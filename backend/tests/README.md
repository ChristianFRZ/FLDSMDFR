# Pruebas

Corren contra un PostgreSQL real, en la base de datos `meloxo_test`, porque los criterios críticos dependen de bloqueos reales. Esa base se crea sola y se limpia entre pruebas. Jamendo se simula con `respx`.

Necesitas PostgreSQL en marcha y un `.env` con `POSTGRES_PASSWORD`. Los comandos para prepararlo y correr las pruebas están en el [README del backend](../README.md#preparar-el-entorno).

[`modules/`](modules/README.md) repite la estructura de [`app/modules/`](../app/modules/README.md) y [`seed/`](seed/README.md) prueba la semilla. En esta carpeta quedan las pruebas de todo el proyecto y sus utilidades:

| Archivo | Para qué sirve |
| --- | --- |
| [`conftest.py`](conftest.py) | Prepara la base de datos, la app y los usuarios de prueba |
| [`boundaries.py`](boundaries.py) | Detecta las importaciones entre módulos |
| [`media.py`](media.py) | Crea MP3, JPG y PNG mínimos, para no guardar binarios en el repositorio |
| [`test_boundaries.py`](test_boundaries.py) | Comprueba que ningún módulo se salte `public.py` |
| [`test_health.py`](test_health.py) | Salud del sistema y formato de los errores |
| [`test_pool.py`](test_pool.py) | Una petición no retiene su conexión mientras otro módulo abre la suya |
| [`test_readmes.py`](test_readmes.py) | Toda carpeta tiene README |
| [`test_spa.py`](test_spa.py) | La app sirve la interfaz sin pisar la API |
