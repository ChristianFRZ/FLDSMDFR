# DESIGN.md · FLDSMDFR Monolito

## 1. Identidad Visual y Estilo

FLDSMDFR es una plataforma moderna de streaming musical. El diseño visual se inspira en interfaces de streaming contemporáneas (como Spotify o Apple Music), con un tema oscuro refinado que reduce la fatiga visual y realza el contenido multimedia.

### 1.1. Paleta de Colores

- **Fondo Principal (`--bg-primary`):** `#121212` (Gris carbón profundo)
- **Fondo Secundario / Tarjetas (`--bg-surface`):** `#181818` (Gris superficie)
- **Fondo Elevado / Modales (`--bg-elevated`):** `#242424`
- **Color de Acento / Interactivo (`--accent`):** `#1DB954` (Verde Neón FLDSMDFR)
- **Acento Hover (`--accent-hover`):** `#1ed760`
- **Texto Principal (`--text-main`):** `#FFFFFF`
- **Texto Secundario / Metadatos (`--text-muted`):** `#A7A7A7`
- **Bordes y Divisores (`--border-subtle`):** `#282828`
- **Estados de Éxito / Alerta (`--status-warning` / `--status-error`):** `#F59E0B` / `#EF4444`

### 1.2. Tipografía

- Fuente sans-serif nativa de alto rendimiento: `Inter`, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif.
- Tamaños de texto:
  - Títulos principales (H1 / Brand): 24px - 28px, Bold (700)
  - Títulos de sección (H2 / H3): 18px - 20px, Semi-bold (600)
  - Cuerpo / Metadatos de canciones: 14px, Regular (400)
  - Indicadores / Insignias / Timecodes: 12px, Medium (500)

---

## 2. Componentes de la Interfaz

La interfaz monolítica se organiza en un layout de tres columnas / panel responsivo:

### 2.1. Barra Lateral de Navegación y Sesión (Sidebar)
- Identidad de la marca: `FLDSMDFR Streaming`.
- Selector / Perfil de usuario activo (cambio rápido entre oyentes para pruebas).
- Navegación rápida:
  - 🎵 Catálogo de Canciones (`/api/songs`)
  - 📋 Mis Playlists (`/api/playlists`)
  - 🏆 Top Métricas (`/api/metrics/top`)
  - 🔌 API Docs (`/docs` Swagger)

### 2.2. Panel Central de Contenido
- **Vista de Catálogo:**
  - Barra de búsqueda reactiva por título, artista o álbum.
  - Tabla de canciones con carátula simbólica, título, artista, duración y botones de acción (Reproducir, Agregar a Playlist).
- **Vista de Playlists:**
  - Formulario de creación de playlists (`POST /api/playlists`).
  - Listado de playlists y visor de canciones contenidas en cada lista (`GET /api/playlists/{id}`).
- **Vista de Métricas y Popularidad:**
  - Ranking en tiempo real de las canciones más reproducidas (`GET /api/metrics/top`).
  - Contador de escuchas sincronizado.

### 2.3. Reproductor Global Persistente (Footer Audio Player)
- Información de la pista actual (título, artista, cover art).
- Controles de transporte: Reproducir, Pausar, Barra de progreso (Seekable gracias a HTTP Range Requests).
- Indicador de telemetría: Feedback visual cuando se alcanzan los 10 segundos de reproducción continua y se emite el evento idempotente `POST /api/playbacks` con su UUID único.
- Control de volumen y mute.

---

## 3. Experiencia de Usuario y Criterios Técnicos

1. **Streaming fluido con Range Requests:** El reproductor HTML5 realiza solicitudes parciales `Range: bytes=start-end` al backend FastAPI, permitiendo saltar inmediatamente a cualquier segundo de la canción sin esperar descarga completa.
2. **Telemetría no invasiva:** El registro de escuchas ocurre automáticamente a los 10 segundos de reproducción por evento, enviando una clave UUID única para garantizar idempotencia.
3. **Degradación amigable:** Si hay algún error al recuperar metadatos o métricas, la interfaz informa al usuario mediante notificaciones tostadas ("toast notifications") sin congelar el audio.
