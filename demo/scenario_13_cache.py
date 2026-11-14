"""La caché de lectura vive aparte y nunca es necesaria: `redis-cache` puede llenarse, vaciarse o caer.

(a) Una lectura llena la caché y ocultar una pista la quita de la siguiente lectura, sin esperar al TTL.
(b) Con `redis-cache` detenido, las lecturas responden lo mismo y sin pagar un timeout por petición; al volver, se vuelve a llenar.
(c) El Redis durable no se mezcla con la caché: su stream y su política de memoria quedan intactos.
"""
import subprocess
import time

from common import COMPOSE, Api, Failure, admin, check, compose, published_songs, run, wait_until

CACHE = "redis-cache"
LIMIT_SECONDS = 0.5
REFILL_WAIT = 30


def cache_cli(*args: str) -> str:
    return compose(COMPOSE, "exec", "-T", CACHE, "redis-cli", *args)


def durable_cli(*args: str) -> str:
    return compose(COMPOSE, "exec", "-T", "redis", "redis-cli", *args)


def keys(pattern: str) -> list[str]:
    return [line for line in cache_cli("--scan", "--pattern", pattern).splitlines() if line]


def titles(page: dict) -> list[str]:
    return [item["id"] for item in page["items"]]


def wait_cache_up() -> None:
    def ping() -> bool:
        try:
            return cache_cli("ping") == "PONG"
        except subprocess.CalledProcessError:
            return False

    wait_until(ping, 30, "redis-cache no volvió a responder en 30 s")


def scenario() -> None:
    boss = admin()
    songs = published_songs(boss, 6)
    target = songs[0]["id"]
    cache_cli("FLUSHALL")  # es solo caché: vaciarla no pierde nada

    page = boss.ok("GET", "/api/songs?size=5")
    check(len(keys("cache:catalog:*")) >= 1, "(a) una lectura de /api/songs deja claves cache:catalog:* en redis-cache")
    check(target in titles(page), "(a) la pista elegida está en la primera página")
    boss.ok("GET", f"/api/songs/{target}")
    try:
        boss.ok("POST", f"/api/admin/songs/{target}/hide", {"reason": "Escenario 13"})
        check(
            target not in titles(boss.ok("GET", "/api/songs?size=5")),
            "(a) ocultar la pista la quita de la siguiente lectura, sin esperar al TTL",
        )
        status, _ = boss.call("GET", f"/api/songs/{target}")
        check(status == 404, f"(a) el detalle de la pista oculta da {status}")
    finally:
        boss.ok("POST", f"/api/admin/songs/{target}/restore")
    check(target in titles(boss.ok("GET", "/api/songs?size=5")), "(a) al restaurarla vuelve a aparecer")

    baseline = {
        "lista": boss.ok("GET", "/api/songs?size=5"),
        "detalle": boss.ok("GET", f"/api/songs/{target}"),
    }
    stream_before = durable_cli("XLEN", "track_published")
    try:
        compose(COMPOSE, "stop", CACHE)
        check(boss.ok("GET", "/api/songs?size=5") == baseline["lista"], "(b) con la caché caída, la lista es la misma")
        check(boss.ok("GET", f"/api/songs/{target}") == baseline["detalle"], "(b) y el detalle también")
        check("items" in boss.ok("GET", "/api/metrics/top"), "(b) /api/metrics/top responde")
        start = time.monotonic()
        for _ in range(5):
            boss.ok("GET", "/api/songs?size=5")
        seconds = (time.monotonic() - start) / 5
        check(seconds < LIMIT_SECONDS, f"(b) con la caché caída, cada lectura tarda {seconds:.2f} s en promedio")
    finally:
        compose(COMPOSE, "start", CACHE)
        wait_cache_up()

    def refilled() -> bool:
        try:
            boss.ok("GET", "/api/songs?size=5")
        except Failure:
            return False
        return len(keys("cache:catalog:*")) >= 1

    wait_until(refilled, REFILL_WAIT, "(b) la caché no se volvió a llenar en 30 s")
    print("  ok: (b) al volver redis-cache, las lecturas se vuelven a guardar")

    check(durable_cli("XLEN", "track_published") == stream_before, "(c) el stream track_published del Redis durable no cambió")
    check(not keys("track_published*") and not keys("playbacks*") and not keys("revoked_after:*"), "(c) redis-cache no guarda streams ni revocaciones")
    durable_cache_keys = durable_cli("--scan", "--pattern", "cache:*").strip()
    check(not durable_cache_keys, "(c) el Redis durable no guarda claves de caché")
    check(cache_cli("config", "get", "maxmemory-policy").split()[-1] == "allkeys-lru", "(c) redis-cache desaloja con allkeys-lru")
    check(durable_cli("config", "get", "maxmemory").split()[-1] == "0", "(c) el Redis durable no tiene límite de memoria")


if __name__ == "__main__":
    run("Escenario 13: caché de lectura", scenario)
