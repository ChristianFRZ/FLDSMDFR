from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fakeredis import aioredis as fakeredis
from sqlalchemy import event

from meloxo_common import cache
from meloxo_common.cache import override_cache
from meloxo_common.db import get_engine
from catalog_streaming.modules.catalog.import_jobs import upsert_tracks
from catalog_streaming.modules.catalog.jamendo import to_track
from catalog_streaming.modules.catalog.publishing import publish_due_tracks
from tests.media import JPG, mp3
from tests.modules.catalog.test_composer import upload
from tests.modules.catalog.test_import import track as jamendo_track

VERSION_KEY = "cache:ver:catalog"


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
    """Cuenta las sentencias SQL que se ejecutan dentro del bloque."""
    statements = []
    engine = get_engine().sync_engine

    def listener(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", listener)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", listener)


async def version(fake_cache) -> int:
    return int(await fake_cache.get(VERSION_KEY) or 0)


async def titles(client, user) -> list[str]:
    return [s["title"] for s in (await client.get("/api/songs", headers=user.headers)).json()["items"]]


async def test_lista_se_sirve_de_la_cache(client, listener, make_song):
    await make_song()
    first = await client.get("/api/songs", headers=listener.headers)
    with count_sql() as statements:
        second = await client.get("/api/songs", headers=listener.headers)
    assert second.json() == first.json()
    assert statements == []


async def test_detalle_artista_y_generos_se_sirven_de_la_cache(client, listener, make_song):
    song = await make_song()
    paths = [f"/api/songs/{song.id}", f"/api/artists/{song.artist_id}", "/api/genres"]
    firsts = [(await client.get(p, headers=listener.headers)).json() for p in paths]
    with count_sql() as statements:
        seconds = [(await client.get(p, headers=listener.headers)).json() for p in paths]
    assert seconds == firsts
    assert statements == []


async def test_ocultar_una_pista_la_quita_de_la_siguiente_lectura(client, listener, admin, make_song):
    song = await make_song()
    for path in ("/api/songs", f"/api/songs/{song.id}", f"/api/artists/{song.artist_id}"):
        assert (await client.get(path, headers=listener.headers)).status_code == 200  # llena la caché
    hidden = await client.post(f"/api/admin/songs/{song.id}/hide", json={"reason": "Prueba"}, headers=admin.headers)
    assert hidden.status_code == 200
    assert await titles(client, listener) == []
    assert (await client.get(f"/api/songs/{song.id}", headers=listener.headers)).status_code == 404
    assert (await client.get(f"/api/artists/{song.artist_id}", headers=listener.headers)).json()["songs"] == []


async def test_restaurar_la_vuelve_a_mostrar(client, listener, admin, make_song):
    song = await make_song()
    await client.post(f"/api/admin/songs/{song.id}/hide", json={"reason": "Prueba"}, headers=admin.headers)
    assert await titles(client, listener) == []
    assert (await client.post(f"/api/admin/songs/{song.id}/restore", headers=admin.headers)).status_code == 200
    assert await titles(client, listener) == [song.title]


async def test_ocultar_con_auditoria_caida_no_invalida(client, listener, admin, make_song, users_service, fake_cache):
    song = await make_song()
    await titles(client, listener)
    before = await version(fake_cache)
    users_service.audit_down = True
    assert (await client.post(f"/api/admin/songs/{song.id}/hide", json={"reason": "x"}, headers=admin.headers)).status_code >= 500
    assert await version(fake_cache) == before
    assert await titles(client, listener) == [song.title]


async def test_publicar_programadas_invalida(client, listener, make_song):
    await make_song(title="Ya", status="published")
    assert await titles(client, listener) == ["Ya"]
    await make_song(title="Programada", status="scheduled", publish_at=datetime.now(UTC) - timedelta(minutes=1))
    assert await publish_due_tracks() == 1
    assert sorted(await titles(client, listener)) == ["Programada", "Ya"]


async def test_publicar_programadas_sin_nada_no_invalida(fake_cache):
    assert await publish_due_tracks() == 0
    assert await version(fake_cache) == 0


async def test_editar_una_pista_publicada_se_ve_en_la_lista(client, listener, composer):
    song = (await upload(client, composer)).json()
    await client.post(f"/api/composer/tracks/{song['id']}/publish", headers=composer.headers)
    assert await titles(client, listener) == ["Mi pista"]
    r = await client.patch(f"/api/composer/tracks/{song['id']}", json={"title": "Nuevo título"}, headers=composer.headers)
    assert r.status_code == 200
    assert await titles(client, listener) == ["Nuevo título"]


async def test_ocultar_y_borrar_como_compositor_se_ven_en_la_lista(client, listener, composer):
    song = (await upload(client, composer)).json()
    await client.post(f"/api/composer/tracks/{song['id']}/publish", headers=composer.headers)
    assert await titles(client, listener) == ["Mi pista"]
    await client.post(f"/api/composer/tracks/{song['id']}/hide", headers=composer.headers)
    assert await titles(client, listener) == []
    await client.post(f"/api/composer/tracks/{song['id']}/publish", headers=composer.headers)
    assert await titles(client, listener) == ["Mi pista"]
    assert (await client.delete(f"/api/composer/tracks/{song['id']}", headers=composer.headers)).status_code == 204
    assert await titles(client, listener) == []


async def test_perfil_editado_se_ve_en_la_pagina_del_artista(client, listener, composer):
    song = (await upload(client, composer)).json()
    await client.post(f"/api/composer/tracks/{song['id']}/publish", headers=composer.headers)
    path = f"/api/artists/{song['artist_id']}"
    assert (await client.get(path, headers=listener.headers)).json()["bio"] == ""
    await client.put("/api/composer/profile", json={"name": "Luz Norte", "bio": "Canciones", "links": {}}, headers=composer.headers)
    body = (await client.get(path, headers=listener.headers)).json()
    assert (body["name"], body["bio"]) == ("Luz Norte", "Canciones")


@pytest.mark.parametrize("operation", ["foto", "album"])
async def test_foto_y_album_suben_la_version(client, composer, fake_cache, operation):
    if operation == "foto":
        r = await client.post("/api/composer/profile/photo", files={"photo": ("f.jpg", JPG, "image/jpeg")}, headers=composer.headers)
    else:
        r = await client.post("/api/composer/albums", data={"title": "EP", "kind": "ep"}, headers=composer.headers)
    assert r.status_code in (200, 201)
    assert await version(fake_cache) == 1


async def test_importar_pistas_de_jamendo_invalida(client, listener, fake_cache):
    assert await titles(client, listener) == []
    await upsert_tracks([to_track(jamendo_track(1))])
    assert await titles(client, listener) == ["Pista 1"]


async def test_importar_nada_no_invalida(fake_cache):
    await upsert_tracks([])
    assert await version(fake_cache) == 0


async def test_404_no_se_guarda(client, listener, composer):
    missing = uuid4()
    assert (await client.get(f"/api/songs/{missing}", headers=listener.headers)).status_code == 404
    with count_sql() as statements:
        assert (await client.get(f"/api/songs/{missing}", headers=listener.headers)).status_code == 404
    assert statements, "el 404 debió volver a consultar la base"
    song = (await upload(client, composer)).json()
    await client.post(f"/api/composer/tracks/{song['id']}/publish", headers=composer.headers)
    assert (await client.get(f"/api/songs/{song['id']}", headers=listener.headers)).status_code == 200
    assert (await client.get(f"/api/artists/{uuid4()}", headers=listener.headers)).status_code == 404


async def test_sin_cache_las_rutas_responden_igual(client, listener, make_song):
    song = await make_song()
    paths = ["/api/songs", f"/api/songs/{song.id}", f"/api/artists/{song.artist_id}", "/api/genres"]
    cached_bodies = [(await client.get(p, headers=listener.headers)).json() for p in paths]
    override_cache(None)
    plain = [(await client.get(p, headers=listener.headers)).json() for p in paths]
    assert plain == cached_bodies


async def test_cache_rota_no_cambia_la_respuesta(client, listener, make_song):
    song = await make_song()
    paths = ["/api/songs", f"/api/songs/{song.id}", f"/api/artists/{song.artist_id}", "/api/genres"]
    expected = [(await client.get(p, headers=listener.headers)).json() for p in paths]
    override_cache(Broken())
    cache._skip_until = 0.0
    for path, body in zip(paths, expected):
        r = await client.get(path, headers=listener.headers)
        assert (r.status_code, r.json()) == (200, body)


async def test_parametros_distintos_no_comparten_clave(client, listener, make_song):
    await make_song(title="Rock A", genres=("rock",))
    await make_song(title="Jazz B", genres=("jazz",), artist="Otra Banda")
    for _ in range(2):
        rock = (await client.get("/api/songs?genre=rock", headers=listener.headers)).json()
        jazz = (await client.get("/api/songs?genre=jazz", headers=listener.headers)).json()
        assert [s["title"] for s in rock["items"]] == ["Rock A"]
        assert [s["title"] for s in jazz["items"]] == ["Jazz B"]
    page_1 = (await client.get("/api/songs?size=1&page=1", headers=listener.headers)).json()
    page_2 = (await client.get("/api/songs?size=1&page=2", headers=listener.headers)).json()
    assert page_1["items"] != page_2["items"]
