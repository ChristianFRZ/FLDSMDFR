"""Un Compositor no toca pistas ajenas ni entra a /api/admin."""
from common import admin, check, new_composer, new_user, run, upload_track

TITLE = "Escenario 7"


def scenario() -> None:
    boss = admin()
    owner, _ = new_composer("permisos-a", boss)
    stranger, _ = new_composer("permisos-b", boss)
    listener, _ = new_user("permisos-c")
    track = upload_track(owner, TITLE)
    path = f"/api/composer/tracks/{track['id']}"
    try:
        check(stranger.call("PATCH", path, {"title": "Robada"})[0] == 403, "editar una pista ajena da 403")
        check(stranger.call("DELETE", path)[0] == 403, "borrar una pista ajena da 403")
        check(stranger.call("GET", "/api/admin/users")[0] == 403, "un Compositor en /api/admin/users recibe 403")
        check(stranger.call("GET", "/api/admin/audit")[0] == 403, "un Compositor en /api/admin/audit recibe 403")
        check(listener.call("GET", "/api/composer/tracks")[0] == 403, "un Oyente en /api/composer recibe 403")
        titles = [t["title"] for t in owner.ok("GET", "/api/composer/tracks")]
        check(titles == [TITLE], "la pista sigue intacta")
    finally:
        owner.ok("DELETE", path)


if __name__ == "__main__":
    run("Escenario 7: permisos", scenario)
