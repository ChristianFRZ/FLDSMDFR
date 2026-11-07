# Core

Lo que usan todos los [módulos](../modules/README.md). Aquí no van reglas de negocio.

| Archivo | Para qué sirve |
| --- | --- |
| [`config.py`](config.py) | Variables de entorno |
| [`db.py`](db.py) | Motor, sesiones y clase base de los modelos. `session_scope()` es la sesión que abre cada `public.py` |
| [`errors.py`](errors.py) | `AppError` y el formato común de los errores |
| [`security.py`](security.py) | Contraseñas y JWT |
| [`auth.py`](auth.py) | Usuario actual y comprobación de roles |
| [`pagination.py`](pagination.py) | Paginación de resultados |
| [`scheduler.py`](scheduler.py) | [Tareas periódicas](../README.md#tareas-periódicas) |
