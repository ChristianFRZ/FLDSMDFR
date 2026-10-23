# FLDSMDFR · Sistema Distribuido de Streaming Musical

Repositorio del proyecto semestral para la materia de **Sistemas Distribuidos** (Semestre 2027-1, FI-UNAM).

---

## 👥 Equipo
- **Nombre del equipo:** `FLDSMDFR`
- **Integrantes:**
  - Franco Ramírez Christian ([@ChristianFRZ](https://github.com/ChristianFRZ))
  - López Hernández Miriam Amisadai ([@AmisadaiLopez](https://github.com/AmisadaiLopez))
  - Nava Santiago Erick ([@Saiko-E](https://github.com/Saiko-E))
  - Pérez Paitán Brent Armando ([@zmd-brnt](https://github.com/zmd-brnt))

---

## 📌 Estado Actual: Rama `01-monolito`

En esta fase se encuentra implementado el **Monolito Modular** inicial correspondiente al paso 1 del plan progresivo del [PRD.md](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/docs/PRD.md).

> Para consultar el desglose detallado de archivos creados, justificación técnica y pruebas ejecutadas, revisa el archivo dedicado: [README_MONOLITO.md](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/README_MONOLITO.md).

---

## 🏗️ Arquitectura del Monolito

El monolito reside en una sola aplicación con un único proceso, implementada en **Python 3.11+ con FastAPI y SQLite** (modo WAL), organizada según las directrices de `AGENTS.md` y `PRD.md`:

```text
FLDSMDFR/
├── AGENTS.md                  # Reglas del agente y arquitectura
├── SKILLS.md                  # Prompts reutilizables y rol de asesor técnico crítico
├── DESIGN.md                  # Especificación de interfaz y diseño visual
├── README.md                  # Este documento
├── README_MONOLITO.md         # Documentación detallada de cambios e instrucciones
├── requirements.txt           # Dependencias de Python
├── Dockerfile                 # Contenedor del monolito
├── docker-compose.yml         # Orquestación con un solo comando (docker compose up --build)
│
├── core/                      # Lógica de negocio modular
│   ├── config.py              # Parámetros del sistema y rutas
│   ├── module_users/          # Gestión de usuarios y sesiones
│   ├── module_catalog/        # Catálogo y streaming binario con HTTP Range Requests (RFC 7233)
│   ├── module_playlists/      # Creación de playlists y asociación de canciones (< 200 ms)
│   └── module_playback/       # Telemetría de escucha (>10s), idempotencia UUID y top de popularidad
│
├── db/                        # Acceso y gestión de datos
│   ├── schema.sql             # Esquema relacional e índices
│   ├── connection.py          # Conexión SQLite thread-safe con modo WAL
│   └── init_db.py             # Sembrado inicial con usuarios, canciones y listas
│
├── media/
│   └── audio/                 # Canciones reales en formato WAV para streaming
│
├── ui/                        # Interfaz de usuario SPA moderna (Dark mode)
│   ├── index.html             # Vistas de Catálogo, Playlists, Top Métricas y Reproductor
│   ├── css/style.css          # Estilos inspirados en plataformas de streaming
│   └── js/app.js              # Controlador cliente con Range Streaming y telemetría automática
│
├── tests/                     # Batería de 19 pruebas automatizadas (pytest)
└── main.py                    # Punto de entrada de la aplicación FastAPI
```

---

## 🚀 Cómo Levantar el Monolito

### Opción 1: Con Docker Compose (Recomendada)

```bash
# Levantar el monolito
docker compose up --build

# Apagar el monolito
docker compose down -v
```

### Opción 2: En Entorno Local de Python

```bash
# 1. Crear y activar el entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Generar pistas de audio de demostración (si es necesario)
python scripts/generate_samples.py

# 4. Iniciar el servidor
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🌐 Enlaces y Puntos de Acceso

Una vez levantado el servidor:
- **Interfaz Web del Monolito:** [http://localhost:8000](http://localhost:8000)
- **Documentación Interactiva Swagger / OpenAPI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Documentación Redoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Comprobación de Salud:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 🧪 Pruebas Automatizadas

Para validar que se cumplen todos los criterios de aceptación del PRD:

```bash
.venv/bin/pytest -v
```

Todas las 19 pruebas unitarias y de integración cubren:
1. Autenticación y creación de usuarios.
2. Latencia JSON de playlists menor a 200 ms.
3. Streaming de audio admitiendo peticiones con cabeceras `Range: bytes=...` (`206 Partial Content`).
4. Rechazo de reproducciones menores a 10 segundos.
5. Idempotencia estricta en el registro de reproducciones mediante UUID.
6. Consulta ordenada del Top de popularidad.

---

## 🗺️ Plan Progresivo de Ramas (Siguientes Fases)

- `01-monolito` *(Fase actual)*: Aplicación única en Python (FastAPI) con módulos acoplados y base de datos local.
- `02-separacion`: División del código en servicios independientes en contenedores Docker comunicándose por red interna.
- `03-gateway-balanceo`: Integración de API Gateway centralizado y balanceador de carga.
- `04-resiliencia-concurrencia`: Implementación de timeouts, reintentos con backoff y degradación elegante.
