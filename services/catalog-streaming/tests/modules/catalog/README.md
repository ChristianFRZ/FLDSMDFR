# Pruebas de modules/catalog

Pruebas del módulo [`catalog`](../../../catalog_streaming/modules/catalog/README.md).

| Archivo | Qué cubre |
| --- | --- |
| [`test_songs.py`](test_songs.py) | Búsqueda y filtros |
| [`test_streaming.py`](test_streaming.py) | `Range`, tickets y proxy hacia Jamendo |
| [`test_import.py`](test_import.py) | Importación por lotes y reanudación |
| [`test_jamendo_status.py`](test_jamendo_status.py) | Estado de Jamendo para el panel de salud |
| [`test_composer.py`](test_composer.py) | Subidas, estados de pista y permisos del Compositor |
| [`test_publishing.py`](test_publishing.py) | Publicación programada, ocultar y restaurar |

Los usuarios y sus roles salen del fixture `users_service` de [`conftest.py`](../../conftest.py), que simula con `respx` las rutas internas de `users-playlists`.
