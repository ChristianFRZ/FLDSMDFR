# infra

Infraestructura compartida por los tres servicios.

| Carpeta | Contenido |
| --- | --- |
| [`postgres`](postgres/README.md) | `init.sh`: crea una base y un rol por servicio la primera vez que arranca PostgreSQL |
| [`tests`](tests/README.md) | Pruebas de aislamiento entre las bases (necesitan PostgreSQL arriba) |
