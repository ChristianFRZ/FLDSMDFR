"""Detiene una réplica de catálogo mientras se consulta el gateway y la restaura."""
import subprocess
from concurrent.futures import ThreadPoolExecutor

from common import Api, COMPOSE, check, compose, new_user, run


def scenario():
    service = "catalog-streaming-service"
    replicas = compose(COMPOSE, "ps", "-q", service).splitlines()
    check(len(replicas) == 2, "dos réplicas de catálogo en ejecución")
    api, _ = new_user("failover")
    check(Api().call("GET", "/api/genres")[0] == 401, "el catálogo requiere sesión")
    check(api.call("GET", "/api/admin/users")[0] == 403, "un oyente no puede administrar")
    api.ok("GET", "/api/genres")
    try:
        with ThreadPoolExecutor(max_workers=5) as pool:
            stop = pool.submit(subprocess.run, ["docker", "stop", replicas[0]], check=True)
            requests = [pool.submit(api.call, "GET", "/api/genres") for _ in range(40)]
            failures = sum(request.result()[0] != 200 for request in requests)
            stop.result()
        check(failures <= 1, f"{failures} solicitudes fallidas durante la transición")
        api.ok("GET", "/api/genres")
    finally:
        compose(COMPOSE, "up", "-d", "--wait", "--no-build", "--no-deps", service)


if __name__ == "__main__":
    run("Escenario 2 · Failover de catálogo", scenario)
