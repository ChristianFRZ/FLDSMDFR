import asyncio
import time

from app.core.config import get_settings
from app.modules.catalog import public
from app.modules.catalog.jamendo import JamendoClient, JamendoError


def configured(monkeypatch):
    monkeypatch.setattr(get_settings(), "JAMENDO_CLIENT_ID", "x")


async def test_slow_jamendo_does_not_hold_health(monkeypatch):
    """El panel debe responder en menos de 2 s aunque Jamendo tarde."""
    configured(monkeypatch)

    async def slow(_):
        await asyncio.sleep(5)

    monkeypatch.setattr(JamendoClient, "ping", slow)
    started = time.monotonic()
    assert await public.jamendo_status() == "delayed"
    assert time.monotonic() - started < 2


async def test_status_is_reused_between_polls(monkeypatch):
    """Cada panel abierto consulta cada 15 s: eso no debe gastar la cuota de Jamendo."""
    configured(monkeypatch)
    calls = []

    async def ping(_):
        calls.append(1)

    monkeypatch.setattr(JamendoClient, "ping", ping)
    assert await public.jamendo_status() == "up"
    assert await public.jamendo_status() == "up"
    assert len(calls) == 1


async def test_failed_jamendo_is_down(monkeypatch):
    configured(monkeypatch)

    async def fail(_):
        raise JamendoError("caído")

    monkeypatch.setattr(JamendoClient, "ping", fail)
    assert await public.jamendo_status() == "down"
