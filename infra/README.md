# infra

Infraestructura compartida por los servicios.

| Carpeta | Contenido |
| --- | --- |
| [`postgres`](postgres/README.md) | `init.sh`: crea una base y un rol por servicio la primera vez que arranca PostgreSQL |
| [`redis`](redis/README.md) | Cómo están configurados los dos Redis (el durable, con la cola de reproducciones, `track_published` y la revocación; y `redis-cache`, la caché de lectura con LRU) y cómo mirarlos |
| [`tests`](tests/README.md) | Pruebas de aislamiento entre las bases (necesitan PostgreSQL arriba) |
