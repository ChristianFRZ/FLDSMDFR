"""Degradar al único administrador activo da 409, no cambia nada y queda auditado."""
from common import admin, check, error_code, run


def scenario() -> None:
    boss = admin()
    me = boss.ok("GET", "/api/users/me")
    active = boss.ok("GET", "/api/admin/users?role=admin&status=active&size=100")["items"]
    others = [user for user in active if user["id"] != me["id"]]
    suspended = []
    try:
        # La semilla crea más administradores: se suspenden para que este sea el único.
        for user in others:
            boss.ok("POST", f"/api/admin/users/{user['id']}/suspend", {"reason": "Escenario 6"})
            suspended.append(user)
        before = boss.ok("GET", f"/api/admin/audit?target_id={me['id']}")["total"]

        status, data = boss.call("POST", f"/api/admin/users/{me['id']}/role", {"role": "listener"})

        check(status == 409, f"degradarlo responde {status}")
        check(error_code(data) == "last_admin", "el error dice last_admin")
        check(boss.ok("GET", "/api/users/me")["role"] == "admin", "sigue siendo administrador")
        audit = boss.ok("GET", f"/api/admin/audit?target_id={me['id']}")
        check(audit["total"] == before + 1, "el intento dejó una línea de auditoría")
        check(audit["items"][0]["outcome"] == "rejected", "la auditoría lo marca como rechazado")
    finally:
        for user in suspended:
            boss.ok("POST", f"/api/admin/users/{user['id']}/reactivate")


if __name__ == "__main__":
    run("Escenario 6: último administrador", scenario)
