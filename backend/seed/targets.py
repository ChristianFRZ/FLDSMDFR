"""El comando de mantenimiento escribe cada lote usando la cuenta de su dominio."""
import os
from functools import wraps

from app.core.db import maintenance_database


def in_database(variable, operation):
    @wraps(operation)
    async def run(*args, **kwargs):
        token = maintenance_database.set(os.environ.get(variable))
        try:
            return await operation(*args, **kwargs)
        finally:
            maintenance_database.reset(token)
    return run
