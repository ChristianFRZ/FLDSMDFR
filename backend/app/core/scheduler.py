"""Tareas periódicas dentro del proceso. Deben ser seguras con dos procesos a la vez."""
import asyncio
import logging
from collections.abc import Awaitable, Callable

log = logging.getLogger(__name__)


async def _loop(name: str, seconds: float, fn: Callable[[], Awaitable[object]], first_delay: float) -> None:
    await asyncio.sleep(first_delay)
    while True:
        try:
            await fn()
        except Exception:
            log.exception("Falló la tarea periódica %s", name)
        await asyncio.sleep(seconds)


def periodic(name: str, seconds: float, fn: Callable[[], Awaitable[object]], first_delay: float = 0) -> asyncio.Task:
    return asyncio.create_task(_loop(name, seconds, fn, first_delay), name=f"periodic:{name}")
