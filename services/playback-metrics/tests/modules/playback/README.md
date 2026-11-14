# Pruebas de modules/playback

Pruebas del módulo [`playback`](../../../playback_metrics/modules/playback/README.md).

| Archivo | Qué cubre |
| --- | --- |
| [`test_playbacks.py`](test_playbacks.py) | Idempotencia, progreso, historial, eventos y retención, sembrando con `tests/plays.py`. Los metadatos de las pistas salen de `fake_catalog` |
| [`test_consumer.py`](test_consumer.py) | El consumidor de la cola: aplica y acusa, conserva el orden, reintenta lo transitorio, descarta lo inválido y no cuenta dos veces una entrega repetida |
