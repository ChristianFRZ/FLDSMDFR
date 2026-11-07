# Pantallas del Administrador

Pantallas bajo `/admin`. Solo las ve el rol Administrador, y el permiso real lo revisa el backend en cada ruta.

| Archivo | Ruta | Para qué sirve |
| --- | --- | --- |
| [`AdminLayout.tsx`](AdminLayout.tsx) | `/admin/*` | Título y navegación entre secciones |
| [`Dashboard.tsx`](Dashboard.tsx) | `/admin` | Salud del sistema y gráficas, con exportación a CSV y PNG |
| [`Users.tsx`](Users.tsx) | `/admin/users` | Buscar usuarios, cambiar su rol, suspenderlos y reactivarlos |
| [`Requests.tsx`](Requests.tsx) | `/admin/requests` | Aprobar o rechazar solicitudes de Compositor. Para rechazar hay que dar un motivo |
| [`Catalog.tsx`](Catalog.tsx) | `/admin/catalog` | Importar de Jamendo viendo el avance, y ocultar o restaurar pistas |
| [`Audit.tsx`](Audit.tsx) | `/admin/audit` | Registro de acciones administrativas |
| [`Health.tsx`](Health.tsx) | `/admin/health` | Resumen, estado de cada servicio, tráfico y errores de la última hora, recursos, actividad y datos del sistema |
| [`shared.tsx`](shared.tsx) | No es una ruta | Filtros en la URL, fechas y paginación |

El backend no permite dejar el sistema sin administradores: esa respuesta `409` se muestra como aviso y la fila no cambia.
