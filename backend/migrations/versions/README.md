# Versiones

Los archivos de migración, en orden. No edites uno que ya se aplicó en otra máquina: crea uno nuevo.

El nombre lleva un número de cuatro dígitos y el tema, como `0009_tapes.py`. Alembic no asigna el número solo: hay que pasarlo con `--rev-id`, como se ve en el [README del backend](../../README.md#comandos).

| Migraciones | Módulo |
| --- | --- |
| `0000` | Punto de partida, sin cambios |
| `0001` y `0002` | [`users`](../../app/modules/users/README.md) |
| `0003` a `0005` y `0011` | [`catalog`](../../app/modules/catalog/README.md) |
| `0006` | [`playlists`](../../app/modules/playlists/README.md) |
| `0007` | [`playback`](../../app/modules/playback/README.md) |
| `0008` y `0009` | [`social`](../../app/modules/social/README.md) |
| `0010` | [`analytics`](../../app/modules/analytics/README.md) |
