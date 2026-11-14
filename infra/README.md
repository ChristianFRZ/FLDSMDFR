# infra

Infraestructura compartida por los servicios.

| Carpeta | Contenido |
| --- | --- |
| [`postgres`](postgres/README.md) | `init.sh`: crea una base y un rol por servicio la primera vez que arranca PostgreSQL |
| [`redis`](redis/README.md) | Cómo está configurado Redis (cola de reproducciones y revocación de sesiones) y cómo mirar la cola |
| [`tests`](tests/README.md) | Pruebas de aislamiento entre las bases (necesitan PostgreSQL arriba) |
