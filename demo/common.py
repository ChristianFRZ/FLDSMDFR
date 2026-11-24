"""Ayudas de los escenarios. Solo biblioteca estándar: corren con python3 sin instalar nada."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("MELOXO_URL", "http://localhost:8080")
AUDIO = ROOT / "frontend/e2e/fixtures/tone.mp3"
DOMAIN = "escenarios.meloxo.dev"
PASSWORD = "escenario-" + uuid.uuid4().hex
COMPOSE = ["docker", "compose"]
OVERLAY = [*COMPOSE, "-f", "compose.yaml", "-f", "compose.demo.yaml"]
START_SECONDS = 60
SERVICE = "catalog-streaming"
REPLICAS = 2  # réplicas normales de catalog-streaming tras el balanceo del edge


class Failure(Exception):
    """Lo que el escenario esperaba no ocurrió."""


class Precondition(Exception):
    """Falta algo que el escenario no crea por sí mismo (datos sembrados)."""


def check(condition: object, message: str) -> None:
    if not condition:
        raise Failure(message)
    print(f"  ok: {message}")


def run(name: str, scenario: Callable[[], None]) -> None:
    """Imprime PASA o FALLA y sale con error si falla."""
    print(name)
    try:
        scenario()
    except Precondition as exc:
        print(f"PRECONDICIÓN NO CUMPLIDA: {exc}")
        sys.exit(2)
    except Exception as exc:
        print(f"FALLA: {exc}")
        sys.exit(1)
    print("PASA")


def read_env(name: str) -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    raise Failure(f"Falta {name} en .env")


class Api:
    def __init__(self, token: str | None = None, base: str = BASE_URL):
        self.token = token
        self.base = base

    def send(self, method: str, path: str, data: bytes | None, headers: dict) -> tuple[int, bytes]:
        if self.token:
            headers = {**headers, "Authorization": f"Bearer {self.token}"}
        request = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def call(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        data = None if body is None else json.dumps(body).encode()
        status, raw = self.send(method, path, data, {"Content-Type": "application/json"})
        return status, json.loads(raw) if raw else {}

    def ok(self, method: str, path: str, body: dict | None = None) -> dict:
        status, data = self.call(method, path, body)
        if status >= 300:
            raise Failure(f"{method} {path} respondió {status}: {data}")
        return data

    def stream(self, song_id: str) -> tuple[int, bytes]:
        ticket = self.ok("POST", f"/api/songs/{song_id}/stream-ticket")["ticket"]
        return self.send("GET", f"/api/songs/{song_id}/stream?ticket={ticket}", None, {"Range": "bytes=0-1023"})

    def upload(self, fields: dict[str, str]) -> dict:
        boundary = uuid.uuid4().hex
        parts = [
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
            for key, value in fields.items()
        ]
        head = f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="tone.mp3"\r\n'
        parts.append(f"{head}Content-Type: audio/mpeg\r\n\r\n".encode() + AUDIO.read_bytes() + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        status, raw = self.send("POST", "/api/composer/tracks", b"".join(parts), headers)
        if status != 201:
            raise Failure(f"La subida respondió {status}: {raw[:200]!r}")
        return json.loads(raw)


def probe_status(api: Api, path: str) -> int:
    """GET que nunca lanza: un error de conexión cuenta como estado 0 (una petición fallida)."""
    try:
        return api.send("GET", path, None, {})[0]
    except Exception:
        return 0


def failed(statuses: list[int]) -> int:
    return sum(1 for status in statuses if status != 200)


def error_code(data: dict) -> str | None:
    return data.get("error", {}).get("code")


def login(email: str, password: str) -> Api:
    return Api(Api().ok("POST", "/api/auth/login", {"email": email, "password": password})["access_token"])


def admin() -> Api:
    return login(read_env("ADMIN_EMAIL"), read_env("ADMIN_PASSWORD"))


def new_user(label: str) -> tuple[Api, dict]:
    """Cuenta nueva con su propio correo, para no depender de lo que ya haya en la base."""
    email = f"{label}-{uuid.uuid4().hex[:8]}@{DOMAIN}"
    body = {"email": email, "password": PASSWORD, "display_name": f"Escenario {label}"}
    api = Api(Api().ok("POST", "/api/auth/register", body)["access_token"])
    return api, api.ok("GET", "/api/users/me")


def wait_composer_role(
    api: Api,
    seconds: float = 40,
    sleep: Callable[[float], None] | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Espera a que el gateway vea el rol nuevo: guarda el estado de cada usuario hasta 30 s
    (AUTH_CACHE_SECONDS), así que justo tras la promoción /api/composer/* aún puede dar 403.
    Solo un 403 se reintenta; cualquier otro error (401, 5xx...) falla en el acto."""
    sleep = sleep or time.sleep
    deadline = clock() + seconds
    while True:
        status, data = api.call("GET", "/api/composer/tracks")
        if 200 <= status < 300:
            return
        if status != 403:
            raise Failure(f"GET /api/composer/tracks respondió {status} esperando el rol de compositor: {data}")
        if clock() >= deadline:
            raise Failure(f"El rol de compositor no llegó al gateway en {seconds:.0f} s")
        sleep(1)


def new_composer(label: str, by: Api) -> tuple[Api, dict]:
    api, user = new_user(label)
    by.ok("POST", f"/api/admin/users/{user['id']}/role", {"role": "composer"})
    composer = login(user["email"], PASSWORD)
    wait_composer_role(composer)
    return composer, user


def upload_track(composer: Api, title: str, publish_at: str | None = None) -> dict:
    fields = {"title": title, "genre": "demo", "license": "CC BY 4.0"}
    return composer.upload({**fields, "publish_at": publish_at} if publish_at else fields)


def published_songs(api: Api, count: int, source: str | None = None) -> list[dict]:
    query = f"&source={source}" if source else ""
    items = api.ok("GET", f"/api/songs?size=100{query}")["items"]
    if len(items) < count:
        raise Failure(f"Hacen falta {count} canciones y hay {len(items)}: corre la semilla primero")
    return items[:count]


def sql(query: str, database: str = "catalog") -> str:
    """Consulta una de las bases (users_playlists, catalog, playbacks) con el superusuario."""
    command = [*COMPOSE, "exec", "-T", "postgres", "psql", "-U", "meloxo", "-d", database, "-Atc", query]
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def compose(command: list[str], *args: str) -> str:
    return subprocess.run([*command, *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def wait_up(base: str) -> None:
    """Espera a una réplica de catalog-streaming, publicada directo en su puerto (sin pasar por nginx)."""
    limit = time.monotonic() + START_SECONDS
    while time.monotonic() < limit:
        try:
            if Api(base=base).send("GET", "/internal/health", None, {})[0] == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise Failure(f"{base} no arrancó en {START_SECONDS} s")


def replica_urls(replicas: int) -> list[str]:
    urls = []
    for index in range(1, replicas + 1):
        address = compose(OVERLAY, "port", "--index", str(index), SERVICE, "8002")
        urls.append(f"http://localhost:{address.rsplit(':', 1)[1]}")
    return urls


@contextmanager
def demo_stack(replicas: int = REPLICAS) -> Iterator[list[str]]:
    """Levanta catalog-streaming con el overlay y, pase lo que pase, la devuelve a su estado normal en el 8080."""
    try:
        compose(OVERLAY, "up", "-d", "--no-build", "--scale", f"{SERVICE}={replicas}", SERVICE)
        urls = replica_urls(replicas)
        for url in urls:
            wait_up(url)
        yield urls
    finally:
        restore_catalog()


def restore_catalog(run_compose: Callable[..., str] = compose, wait: Callable[[], None] | None = None) -> None:
    """Deja catalog-streaming en REPLICAS réplicas (dos), sin overlay y arriba. Nunca tapa un error anterior:
    si falla durante otro error lo avisa por la salida y sigue; si no había error, lo propaga."""
    in_error = sys.exc_info()[1] is not None
    try:
        run_compose(COMPOSE, "up", "-d", "--no-build", "--scale", f"{SERVICE}={REPLICAS}", SERVICE)
        (wait or wait_edge)()
    except Exception as exc:
        if not in_error:
            raise
        print(f"AVISO: no se pudo restaurar {SERVICE}: {exc}", file=sys.stderr)


def wait_edge(sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic) -> None:
    """Espera a que el nginx de entrada vuelva a repartir tráfico a catalog-streaming por el 8080.

    Sin token, el 401 lo da el gateway sin llegar al catálogo, así que el sondeo usa una sesión de
    administrador y pide cinco 200 seguidos (tras recrear las réplicas, nginx puede tener todavía
    en caché las direcciones viejas hasta 10 s)."""
    limit = clock() + START_SECONDS
    api = None
    streak = 0
    while clock() < limit:
        if api is None:
            try:
                api = admin()
            except Failure as exc:
                raise Failure(f"wait_edge no pudo iniciar sesión como administrador: {exc}") from exc
            except Exception:
                streak = 0  # el edge aún no responde el login: se reintenta
                sleep(0.5)
                continue
        streak = streak + 1 if probe_status(api, "/api/songs?size=1") == 200 else 0
        if streak >= 5:
            return
        sleep(0.5)
    raise Failure(f"{BASE_URL} no respondió en {START_SECONDS} s")
