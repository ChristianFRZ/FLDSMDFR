# Versiones

Los archivos de migración, en orden. No edites uno que ya se aplicó en otra máquina: crea uno nuevo.

| Migración | Qué hace |
| --- | --- |
| `0001_users` | Tablas `users` y `refresh_tokens` |
| `0002_users_audit` | Tablas `audit_log` y `composer_requests` |
| `0003_playlists` | Tablas `playlists` y `playlist_songs` |
| `0004_social` | Tablas `favorites`, `follows` y `notices_seen` |
| `0005_tapes` | Tablas `tapes`, `tape_invites`, `tape_members`, `tape_tracks` e `invite_claims` |

Son las migraciones `0001`, `0002`, `0006`, `0008` y `0009` del monolito, renumeradas desde `0001`.
