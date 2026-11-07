# Aplicación

[`main.py`](main.py) crea la app, registra las rutas y arranca las tareas periódicas. [`core/`](core/README.md) reúne lo que comparten todos los módulos, y cada carpeta de [`modules/`](modules/README.md) es dueña de sus tablas.

**Regla de frontera:** un módulo solo puede importar de otro a través de su `public.py`. Ese archivo trabaja con tipos simples y abre su propia sesión de base de datos. Si alguien rompe la regla, [`test_boundaries.py`](../tests/test_boundaries.py) hace fallar las pruebas. En la rama 02, esas funciones públicas se convierten en llamadas HTTP.

## Qué hay en un módulo

No todos los módulos tienen todos los archivos, pero cuando un archivo existe, siempre cumple la misma función:

| Archivo | Para qué sirve |
| --- | --- |
| `routes.py` | Rutas de la API |
| `schemas.py` | Datos que entran y salen de la API |
| `service.py` | Reglas de negocio |
| `models.py` | Tablas del módulo |
| `public.py` | Lo único que pueden usar los demás módulos |
| `demo.py` | Inserción y limpieza de los datos de la [semilla](../seed/README.md) |

## Tareas periódicas

Corren dentro del mismo proceso, y la variable `DISABLE_SCHEDULER` las apaga. Toda tarea nueva debe funcionar bien con dos procesos a la vez, porque en la rama 03 habrá réplicas.

| Tarea | Frecuencia | Módulo |
| --- | --- | --- |
| Publicar pistas programadas | Cada 30 s | [`catalog`](modules/catalog/README.md) |
| Actualizar agregados | Cada 2 s | [`analytics`](modules/analytics/README.md) |
| Guardar las mediciones de latencia | Cada 30 s | [`analytics`](modules/analytics/README.md) |
| Refrescar metadatos de Jamendo | Cada 24 h; la primera vez, una hora después de arrancar | [`catalog`](modules/catalog/README.md) |

## Rutas generales

- `GET /api/health`: responde si el proceso está vivo.
- `/api/docs`: documentación interactiva de todas las rutas.
- Lo que no empieza con `/api` lo atiende la interfaz, siempre que `STATIC_DIR` esté definida.
