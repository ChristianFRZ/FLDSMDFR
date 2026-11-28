from contextlib import contextmanager

import pytest
from fakeredis import aioredis as fakeredis
from sqlalchemy import event

from meloxo_common import cache
from meloxo_common.cache import override_cache
from meloxo_common.db import get_engine
from playback_metrics.modules.analytics.aggregates import refresh_aggregates
from tests.plays import record_play


@pytest.fixture(autouse=True)
def fake_cache():
    client = fakeredis.FakeRedis(decode_responses=True)
    override_cache(client)
    cache._skip_until = 0.0
    yield client
    override_cache(None)
    cache._skip_until = 0.0


class Broken:
    """Cliente de caché que falla siempre."""

    async def get(self, *args, **kwargs):
        raise ConnectionError("caída")

    set = incr = get


@contextmanager
def count_sql():
    statements = []
    engine = get_engine().sync_engine

    def listener(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", listener)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", listener)


async def seed(user, song, plays=1):
    for _ in range(plays):
        assert await record_play(user, song) == "created"
    await refresh_aggregates(settle_seconds=0)


async def get(client, user, name, **params):
    return await client.get(f"/api/metrics/{name}", params=params, headers=user.headers)


async def test_top_global_se_sirve_de_la_cache(client, admin, listener, make_song):
    await seed(listener, await make_song())
    first = await get(client, admin, "top")
    with count_sql() as statements:
        second = await get(client, admin, "top")
    assert second.json() == first.json()
    assert statements == []


@pytest.mark.parametrize("name,params", [("genres", {}), ("heatmap", {}), ("plays", {"group": "hour"})])
async def test_genres_heatmap_y_plays_se_sirven_de_la_cache(client, admin, listener, make_song, name, params):
    await seed(listener, await make_song())
    first = await get(client, admin, name, **params)
    assert first.status_code == 200
    with count_sql() as statements:
        second = await get(client, admin, name, **params)
    assert second.json() == first.json()
    assert statements == []


async def test_top_me_no_mezcla_usuarios(client, make_user, make_song):
    ana, beto = await make_user(), await make_user()
    song_a, song_b = await make_song(title="De Ana"), await make_song(title="De Beto")
    await seed(ana, song_a)
    await seed(beto, song_b, plays=2)
    for _ in range(2):  # la segunda vuelta sale de la caché
        mine_a = (await get(client, ana, "top", scope="me")).json()["items"]
        mine_b = (await get(client, beto, "top", scope="me")).json()["items"]
        assert [i["label"] for i in mine_a] == ["De Ana"]
        assert [i["label"] for i in mine_b] == ["De Beto"]


async def test_plays_composer_no_mezcla_compositores(client, make_user, make_song, listener):
    uno, dos = await make_user(role="composer"), await make_user(role="composer")
    mine = await make_song(title="Uno", artist="Artista Uno", owner=uno.id)
    other = await make_song(title="Dos", artist="Artista Dos", owner=dos.id)
    await seed(listener, mine, plays=1)
    await seed(listener, other, plays=3)
    for _ in range(2):
        a = (await get(client, uno, "plays", scope="composer")).json()["items"]
        b = (await get(client, dos, "plays", scope="composer")).json()["items"]
        assert [i["plays"] for i in a] == [1]
        assert [i["plays"] for i in b] == [3]


async def test_zonas_horarias_no_comparten_entrada(client, admin, listener, make_song):
    await seed(listener, await make_song())
    utc = (await get(client, admin, "plays", group="hour", tz="UTC")).json()["items"]
    lima = (await get(client, admin, "plays", group="hour", tz="America/Lima")).json()["items"]
    assert utc[0]["bucket"] != lima[0]["bucket"]
    assert (await get(client, admin, "plays", group="hour", tz="UTC")).json()["items"] == utc


async def test_top_con_pista_desconocida_para_catalogo_no_se_guarda(client, admin, listener, make_song, fake_catalog):
    song = await make_song(title="Se fue")
    await seed(listener, song)
    del fake_catalog.songs[song.id]
    assert (await get(client, admin, "top")).json()["items"][0]["label"] == "No disponible"
    fake_catalog.songs[song.id] = song
    assert (await get(client, admin, "top")).json()["items"][0]["label"] == "Se fue"


async def test_top_con_catalogo_caido_no_guarda_el_error(client, admin, listener, make_song, fake_catalog):
    await seed(listener, await make_song())
    fake_catalog.down = True
    assert (await get(client, admin, "top")).status_code == 503
    fake_catalog.down = False
    assert (await get(client, admin, "top")).status_code == 200


async def test_permisos_siguen_antes_que_la_cache(client, admin, listener, make_song):
    await seed(listener, await make_song())
    assert (await get(client, admin, "top")).status_code == 200  # guarda la entrada global
    assert (await get(client, listener, "top", scope="global")).status_code == 403
    assert (await get(client, listener, "plays")).status_code == 403
    assert (await get(client, listener, "heatmap")).status_code == 403


async def test_cache_rota_responde_igual(client, admin, listener, make_song):
    await seed(listener, await make_song())
    expected = {n: (await get(client, admin, n)).json() for n in ("top", "genres", "plays", "heatmap")}
    override_cache(Broken())
    cache._skip_until = 0.0
    for name, body in expected.items():
        r = await get(client, admin, name)
        assert (r.status_code, r.json()) == (200, body)


async def test_expira_a_los_15_segundos(client, admin, listener, make_song, fake_cache):
    await seed(listener, await make_song())
    await get(client, admin, "top")
    keys = [k async for k in fake_cache.scan_iter("cache:metrics:*")]
    assert keys
    assert 0 < await fake_cache.ttl(keys[0]) <= 15
