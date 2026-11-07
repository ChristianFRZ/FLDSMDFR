# Módulos

Los seis módulos de negocio. Cada uno es dueño de sus tablas y solo se comunica con los demás a través de su `public.py`.

| Módulo | Responsabilidad |
| --- | --- |
| [`users/`](users/README.md) | Cuentas, roles, solicitudes de Compositor y auditoría |
| [`playlists/`](playlists/README.md) | Playlists y sus pistas |
| [`catalog/`](catalog/README.md) | Canciones, artistas, álbumes, importación, subidas y streaming |
| [`playback/`](playback/README.md) | Eventos de reproducción, contadores e historial |
| [`social/`](social/README.md) | Favoritas, seguidos, casetes, invitaciones y avisos |
| [`analytics/`](analytics/README.md) | Agregados para gráficas, latencia y salud |

La función de cada archivo de un módulo se explica en el [README de la aplicación](../README.md#qué-hay-en-un-módulo). Las pruebas de cada módulo están en [`backend/tests/modules/`](../../tests/modules/README.md).
