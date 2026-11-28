# Pruebas de modules/analytics

Pruebas del módulo [`analytics`](../../../playback_metrics/modules/analytics/README.md).

| Archivo | Qué cubre |
| --- | --- |
| [`test_metrics.py`](test_metrics.py) | Agregados, gráficas, reportes y salud. Catálogo y usuarios son `fake_catalog` y `fake_users`. Las pruebas de medición de latencia (volcado a `request_metrics`) pasan a la tarea de recolección |
