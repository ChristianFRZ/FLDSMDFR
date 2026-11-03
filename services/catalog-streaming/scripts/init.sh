#!/usr/bin/env bash
# Una sola vez antes de las réplicas (servicio catalog-init): migrar y sembrar.
# Si las tres réplicas lo hicieran al arrancar, competirían por la misma base.
set -euo pipefail

alembic upgrade head
python -m scripts.seed
