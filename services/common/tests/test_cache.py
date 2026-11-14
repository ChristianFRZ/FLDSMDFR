import asyncio
import time

import pytest
from fakeredis import aioredis as fakeredis

from meloxo_common import cache
from meloxo_common.cache import bump, cached, get_json, override_cache, set_json


@pytest.fixture(autouse=True)
def fake():
    client = fakeredis.FakeRedis(decode_responses=True)
    override_cache(client)
    cache._skip_until = 0.0
    yield client
    override_cache(None)
    cache._skip_until = 0.0


class Broken:
    """Cliente que falla o tarda: lo que la caché haría caída o saturada."""

    def __init__(self, delay: float = 0, error: Exception | None = None):
        self.delay, self.error, self.calls = delay, error, 0

    async def _act(self):
        self.calls += 1
        await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return None

    async def get(self, *args, **kwargs):
        return await self._act()

    async def set(self, *args, **kwargs):
        return await self._act()

    async def incr(self, *args, **kwargs):
        return await self._act()


class Counter:
    """Loader que cuenta cuántas veces se ejecutó."""

    def __init__(self, value=None):
        self.calls = 0
        self.value = {"n": 1} if value is None else value

    async def __call__(self):
        self.calls += 1
        return self.value


async def test_cached_guarda_y_reutiliza():
    loader = Counter()
    assert await cached("catalog", {"a": 1}, 60, loader) == {"n": 1}
    assert await cached("catalog", {"a": 1}, 60, loader) == {"n": 1}
    assert loader.calls == 1


async def test_params_en_otro_orden_dan_la_misma_clave():
    loader = Counter()
    await cached("catalog", {"a": 1, "b": 2}, 60, loader)
    await cached("catalog", {"b": 2, "a": 1}, 60, loader)
    assert loader.calls == 1


async def test_params_distintos_no_comparten_entrada():
    loader = Counter()
    await cached("catalog", {"a": 1}, 60, loader)
    await cached("catalog", {"a": 2}, 60, loader)
    assert loader.calls == 2


async def test_bump_invalida_lo_versionado():
    loader = Counter()
    await cached("catalog", {"a": 1}, 60, loader, versioned=True)
    await bump("catalog")
    await cached("catalog", {"a": 1}, 60, loader, versioned=True)
    assert loader.calls == 2


async def test_sin_versionar_ignora_el_bump():
    loader = Counter()
    await cached("metrics", {"a": 1}, 60, loader)
    await bump("metrics")
    await cached("metrics", {"a": 1}, 60, loader)
    assert loader.calls == 1


async def test_lectura_que_empezo_antes_del_bump_no_ensucia_la_version_nueva():
    calls = 0

    async def loader():
        nonlocal calls
        calls += 1
        await bump("catalog")  # una escritura ocurre mientras se carga
        return {"viejo": True}

    await cached("catalog", {"a": 1}, 60, loader, versioned=True)
    await cached("catalog", {"a": 1}, 60, loader, versioned=True)
    assert calls == 2


async def test_si_el_loader_lanza_no_se_guarda():
    async def boom():
        raise ValueError("falla")

    with pytest.raises(ValueError):
        await cached("catalog", {"a": 1}, 60, boom)
    loader = Counter()
    await cached("catalog", {"a": 1}, 60, loader)
    assert loader.calls == 1


async def test_should_store_falso_no_guarda():
    loader = Counter()
    await cached("catalog", {"a": 1}, 60, loader, should_store=lambda _: False)
    await cached("catalog", {"a": 1}, 60, loader, should_store=lambda _: False)
    assert loader.calls == 2


async def test_sin_cache_llama_al_loader_siempre():
    override_cache(None)
    loader = Counter()
    await cached("catalog", {"a": 1}, 60, loader)
    await cached("catalog", {"a": 1}, 60, loader)
    assert loader.calls == 2


async def test_cache_rota_responde_igual_y_salta_5_segundos():
    broken = Broken(error=ConnectionError("caída"))
    override_cache(broken)
    loader = Counter()
    assert await cached("catalog", {"a": 1}, 60, loader) == {"n": 1}
    calls_after_first = broken.calls
    assert await cached("catalog", {"a": 1}, 60, loader) == {"n": 1}
    assert broken.calls == calls_after_first
    assert loader.calls == 2


async def test_cache_lenta_no_retrasa_mas_que_el_timeout():
    override_cache(Broken(delay=2))
    start = time.monotonic()
    assert await cached("catalog", {"a": 1}, 60, Counter()) == {"n": 1}
    assert time.monotonic() - start < 0.6


async def test_bump_no_lanza_con_cache_rota():
    override_cache(Broken(error=ConnectionError("caída")))
    await bump("catalog")


async def test_get_json_y_set_json_van_y_vuelven():
    await set_json("cache:x", {"k": [1, 2]}, 30)
    assert await get_json("cache:x") == {"k": [1, 2]}
    assert await get_json("cache:no-existe") is None


async def test_set_json_aplica_ttl(fake):
    await set_json("cache:x", {"k": 1}, 30)
    assert 0 < await fake.ttl("cache:x") <= 30


async def test_get_json_y_set_json_no_lanzan_con_cache_rota():
    override_cache(Broken(error=ConnectionError("caída")))
    await set_json("cache:x", 1, 30)
    assert await get_json("cache:x") is None
