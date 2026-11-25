"""Un cambio de rol o una suspensión se ve en la siguiente petición, no 30 s después."""
import time

from common import PASSWORD, Api, admin, check, login, new_user, run

LIMIT_SECONDS = 2.0


def scenario() -> None:
    boss = admin()
    me, user = new_user("revocacion")
    check(me.call("GET", "/api/songs?size=1")[0] == 200, "con la sesión nueva, las rutas responden 200")

    start = time.monotonic()
    boss.ok("POST", f"/api/admin/users/{user['id']}/role", {"role": "composer"})
    status, _ = me.call("GET", "/api/songs?size=1")
    seconds = time.monotonic() - start
    check(status == 401, f"el token anterior al cambio de rol da {status} en la siguiente petición")
    check(seconds < LIMIT_SECONDS, f"tardó {seconds:.2f} s (antes: hasta 30 s)")

    fresh = login(user["email"], PASSWORD)
    check(fresh.call("GET", "/api/composer/tracks")[0] == 200, "con un token nuevo, /api/composer/ responde 200 de inmediato")

    start = time.monotonic()
    boss.ok("POST", f"/api/admin/users/{user['id']}/suspend", {"reason": "Escenario 11"})
    status, _ = fresh.call("GET", "/api/songs?size=1")
    seconds = time.monotonic() - start
    check(status == 401, f"la sesión de una cuenta suspendida da {status} en la siguiente petición")
    check(seconds < LIMIT_SECONDS, f"tardó {seconds:.2f} s")
    status, _ = Api().call("POST", "/api/auth/login", {"email": user["email"], "password": PASSWORD})
    check(status == 403, "la cuenta suspendida no puede volver a entrar")


if __name__ == "__main__":
    run("Escenario 11: revocación de sesiones", scenario)
