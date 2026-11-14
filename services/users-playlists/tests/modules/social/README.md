# Pruebas de modules/social

Pruebas del módulo [`social`](../../../users_playlists/modules/social/README.md).

| Archivo | Qué cubre |
| --- | --- |
| [`test_follows.py`](test_follows.py) | Favoritas, seguidos y avisos |
| [`test_notices_local.py`](test_notices_local.py) | Avisos de lanzamientos desde `release_events`: sin llamar a catálogo, con catálogo caído, y solo los posteriores a seguir y a lo último visto |
| [`test_release_consumer.py`](test_release_consumer.py) | Consumidor de `track_published`: guarda y acusa, es idempotente, manda a la cola de mensajes muertos lo inválido y lo que agota `MAX_ATTEMPTS`, y reclama lo pendiente |
| [`test_tapes.py`](test_tapes.py) | Casetes: límites, orden, dedicatorias y permisos |
| [`test_invites.py`](test_invites.py) | Enlaces de invitación |
