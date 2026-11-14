# modules/users

Cuentas, roles, solicitudes de Compositor y auditoría. Sus pruebas están en [`tests/modules/users/`](../../../tests/modules/users/README.md).

**Tablas:** `users`, `refresh_tokens`, `audit_log` y `composer_requests`.

**Contraseñas y tokens:** el hash argon2 y los tokens opacos están en [`security.py`](../../security.py) del paquete; el JWT, en `meloxo_common.security`.

**Lo que ofrece a otros módulos:** `get_auth_state`, `get_display_names`, `ensure_first_admin`, `record_audit` y `user_growth`, en [`public.py`](public.py).

[`service.py`](service.py) se encarga del registro y la sesión. [`admin.py`](admin.py) lleva la administración de cuentas, las solicitudes de Compositor y la bitácora.

## Autenticación

- **Access token:** JWT HS256 de 15 minutos con `sub`, `role`, `iat` y `exp`.
- **Refresh token:** valor opaco de 30 días, guardado como hash y renovado en cada uso.
- **Rol y estado:** se consultan en la base de datos en cada petición, así que una suspensión aplica de inmediato. En la rama 03, esto pasa a una lista de revocación en Redis.
- **Primer administrador:** se crea al arrancar con `ADMIN_EMAIL` y `ADMIN_PASSWORD`, solo si todavía no hay ninguno. Cambiar esas variables después no modifica la cuenta.
- **Límite de inicio de sesión:** 5 fallos en 60 s por correo e IP, contados en la memoria de cada proceso.

## Último administrador

Cambiar un rol, suspender una cuenta o aprobar una solicitud de Compositor escribe `revoked_after:<user_id>` en Redis después del commit ([`meloxo_common.revocation`](../../../../common/meloxo_common/revocation.py)): los tokens emitidos antes dejan de valer en la siguiente petición, y la persona entra de nuevo (o renueva con su refresh token, que ya trae el rol vigente). Reactivar no escribe nada, pero el token anterior a la suspensión sigue revocado. Si Redis falla, la acción se completa y la caché de 30 s hace de respaldo.

Degradar o suspender a un administrador bloquea, en orden, las filas de los administradores activos con `SELECT ... FOR UPDATE`, y comprueba dentro de la transacción que quede al menos uno. El intento rechazado se audita en una transacción aparte, porque la original se revierte.
