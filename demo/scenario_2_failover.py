"""Con una réplica de catalog-streaming detenida, el nginx de entrada sigue sirviendo con la otra."""
import math
import subprocess
import threading
import time

from common import COMPOSE, REPLICAS, SERVICE, Failure, Precondition, check, compose, failed, new_user, probe_status, restore_catalog, run, wait_edge

PATH = "/api/songs?size=1"
RATE = 20  # peticiones por segundo
DURATION = 15
STOP_AT = 3
TAIL = 50


def served(container: str, since: float) -> int:
    """Peticiones de catálogo que atendió la réplica desde `since` (según su registro)."""
    logs = subprocess.run(
        ["docker", "logs", "--since", str(int(since)), container], check=True, capture_output=True, text=True
    )
    return sum("/api/songs" in line for line in (logs.stdout + logs.stderr).splitlines())


def wait_healthy() -> None:
    """Espera a que las REPLICAS réplicas estén sanas, no solo a que el edge responda con la otra."""
    limit = time.monotonic() + 60
    while time.monotonic() < limit:
        ids = compose(COMPOSE, "ps", "-q", SERVICE).split()
        states = [
            subprocess.run(["docker", "inspect", "-f", "{{.State.Health.Status}}", i], capture_output=True, text=True).stdout.strip()
            for i in ids
        ]
        if len(ids) == REPLICAS and all(state == "healthy" for state in states):
            return
        time.sleep(1)
    raise Failure(f"las {REPLICAS} réplicas no quedaron sanas en 60 s")


def scenario() -> None:
    api, _ = new_user("failover")
    ids = compose(COMPOSE, "ps", "-q", SERVICE).split()
    if len(ids) < REPLICAS:
        raise Precondition(f"hacen falta {REPLICAS} réplicas de {SERVICE} y hay {len(ids)}: corre `docker compose up -d`")
    stop = threading.Event()
    thread: threading.Thread | None = None
    try:
        warm = time.time()
        for _ in range(20):
            check_status = probe_status(api, PATH)
            if check_status != 200:
                raise Precondition(f"GET {PATH} responde {check_status} antes de empezar")
        counts = [served(container, warm) for container in ids]
        if min(counts) == 0:
            raise Precondition(f"no ambas réplicas atienden el catálogo (peticiones por réplica: {counts})")
        print(f"  ok: ambas réplicas atienden antes de la falla ({counts})")

        statuses: list[int] = []
        def load() -> None:
            end = time.monotonic() + DURATION
            step = 1 / RATE
            next_at = time.monotonic()
            while time.monotonic() < end and not stop.is_set():
                statuses.append(probe_status(api, PATH))
                next_at += step
                time.sleep(max(0, next_at - time.monotonic()))

        thread = threading.Thread(target=load)
        started = time.time()
        thread.start()
        time.sleep(STOP_AT)
        victim, survivor = ids
        subprocess.run(["docker", "stop", victim], check=True, capture_output=True)
        stopped = math.ceil(time.time())
        thread.join()

        errors = failed(statuses)
        check(len(statuses) >= RATE * DURATION // 2, f"la carga mandó {len(statuses)} peticiones")
        check(errors <= 1, f"{errors} peticiones fallidas de {len(statuses)} al caer una réplica")
        check(all(s == 200 for s in statuses[-TAIL:]), f"las últimas {TAIL} peticiones dan 200")
        check(served(survivor, stopped) > 0, "la réplica que sigue en pie recibió tráfico tras la caída")
    finally:
        stop.set()
        if thread is not None and thread.is_alive():
            thread.join()
        restore_catalog(wait=lambda: (wait_edge(), wait_healthy()))
    print(f"  ok: las {REPLICAS} réplicas volvieron a estar arriba")


if __name__ == "__main__":
    run("Escenario 2: cae una réplica de catálogo", scenario)
