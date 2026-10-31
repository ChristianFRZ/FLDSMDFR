"""Registro de modelos para Alembic y los tests.

Es el unico lugar (junto con alembic/env.py) que importa los `models` de varios modulos,
para poblar `Base.metadata`. Cada tarea que agrega un modulo anade aqui su import.
"""

import app.modules.users.models  # noqa: E402, F401
