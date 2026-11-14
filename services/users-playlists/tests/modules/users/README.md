# Pruebas de modules/users

Pruebas del módulo [`users`](../../../users_playlists/modules/users/README.md).

| Archivo | Qué cubre |
| --- | --- |
| [`test_auth.py`](test_auth.py) | Registro y sesión |
| [`test_admin.py`](test_admin.py) | Roles, último administrador y auditoría |
| [`test_revocation.py`](test_revocation.py) | La revocación en Redis al cambiar rol, suspender o aprobar; la acción sigue si Redis falla; el refresh devuelve un token válido |
| [`test_composer_requests.py`](test_composer_requests.py) | Solicitudes de Compositor |
