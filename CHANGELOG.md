# Cambios

Historial de la rama `01-monolito`, ordenado del más reciente al más antiguo y agrupado por fecha. Cada línea corresponde a un commit. Las decisiones de diseño tomadas durante la construcción están en [`docs/decisions/01-monolito.md`](docs/decisions/01-monolito.md).

## 2026-11-07

### Agregado
- Estante de 12 colores y color libre para los casetes.
- Zona de arrastre para el MP3, la portada y la foto de perfil.
- La pantalla Salud suma resumen, tráfico, módulos, recursos y actividad.
- Documentación de la URL fija con Tailscale Funnel. (`e8c235d`)

### Corregido
- La pantalla completa del reproductor se cerraba al avanzar la canción. (`e8c235d`)
- El crédito de la pista se muestra como artista y origen, sin la licencia. (`e8c235d`)
- Los README tenían datos que no coincidían con el código. (`62effab`)

### Documentación
- Aclaración de los README y corrección de saltos de línea y enlaces. (`a2a103e`)

## 2026-11-06

### Agregado
- Frontend: adaptación a teléfono y accesibilidad. (`da9fdc1`)
- Semilla de demo con Jamendo y actividad simulada. (`dd89059`)
- Escenarios de demo reproducibles y prueba de carga. (`61a8623`)
- Edición de pistas, foto y enlaces del perfil de artista. (`5a5a7b3`)
- Licencia MIT del Equipo FLDSMDFR. (`f0d6b33`)

### Corregido
- **Catálogo**
  - Rechaza campos nulos y enlaces que no son web. (`c741935`)
  - Restaurar devuelve la pista a su estado anterior. (`ad20337`)
  - Maneja un Range enorme, el 416 de Jamendo y las respuestas que no son JSON. (`9741064`)
  - El refresco de Jamendo escribe por lotes. (`14f8789`)
- **Social:** una favorita eliminada se muestra como no disponible. (`a03defc`)
- **Infraestructura:** la clave sale de las pruebas y PostgreSQL queda limitado a localhost. (`162e6eb`)
- **Frontend**
  - Una pista rota salta sola a la siguiente. (`3618ab1`)
  - La sesión sobrevive a dos pestañas y a cortes de red. (`f7ae281`)
  - Unirse a un casete muestra el error en Inicio y Biblioteca. (`061b250`)
  - El panel distingue quién ocultó una pista. (`daa450c`)
  - En teléfono los títulos de Tu música se leen enteros. (`c3bc0a7`)
- La carga de prueba transmite cada pista completa. (`e3ce4ae`)

### Cambiado
- Se saca `egg-info` del repositorio. (`731b814`)
- Se ordena el repositorio y se completan los README. (`3bc443c`)

### Documentación
- Guía del proyecto y verificación final. (`9c64564`)
- Resultados finales tras la revisión de la rama. (`20baa5f`)
- Registro de decisiones y pendientes de la rama. (`3f56aa9`)

### Frontend (construcción)
- Base, marca, sesión e imagen de la app. (`2ce80d5`)
- Reproductor persistente con carretes. (`2ede11c`)
- Inicio, búsqueda, biblioteca y playlists. (`bacb3fa`)
- Casetes, lados, dedicatorias e invitaciones. (`a2669a2`)
- Vistas de compositor y base de gráficas. (`3eef788`)
- Panel de administración y estadísticas. (`daa50a8`)

## 2026-11-05

### Backend (construcción)
- **Base:** esqueleto del backend, base de datos y prueba de fronteras entre módulos. (`07afe35`)
- **Usuarios**
  - Registro, login, refresh y estado en cada petición. (`0173f7d`)
  - Roles, auditoría y solicitudes de compositor. (`0a1713d`)
- **Catálogo**
  - Modelo de catálogo y búsqueda. (`2f607b0`)
  - Streaming con Range, proxy de Jamendo y ticket. (`22ad724`)
  - Importación idempotente y reanudable de Jamendo. (`0d1757d`)
  - Subida validada y gestión de pistas de compositor. (`d80d7f3`)
  - Publicación programada y moderación. (`610d3d9`)
- **Playlists:** playlists con degradación elegante. (`d8bc392`)
- **Reproducción:** eventos idempotentes, progreso e historial. (`3271a88`)
- **Social**
  - Favoritas, artistas seguidos y avisos. (`f807107`)
  - Casetes, invitaciones y dedicatorias. (`04764fb`)
- **Analítica:** agregados, gráficas, salud y CSV. (`548596b`)

### Corregido
- Se suelta la conexión antes de llamar a otro módulo, para que el pool no se bloquee. (`442e2dc`)

### Documentación
- PRD, marca, maqueta, diseño y plan de 01-Monolito. (`074eeb8`)

### Inicio
- Commit inicial. (`f1017c6`)
