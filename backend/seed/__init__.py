"""Semilla de demo. Comando aparte: nunca corre al arrancar la app."""
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from random import Random

from app.modules.analytics.public import catch_up_aggregates, rebuild_aggregates
from app.modules.catalog.public import clear_demo_catalog
from app.modules.playback.public import clear_demo_playbacks
from app.modules.playlists.public import clear_demo_playlists
from app.modules.social.public import clear_demo_social
from app.modules.users.public import clear_demo_users, demo_user_ids
from seed.activity import create_activity, create_catalog
from seed.audio import remove_tones
from seed.catalog import import_catalog
from seed.users import create_users

RANDOM_SEED = 2026


@dataclass(frozen=True)
class Sizes:
    listeners: int = 60
    composers: int = 10
    admins: int = 2
    tracks_per_composer: int = 4
    plays: int = 40_000
    days: int = 90
    tapes: int = 24
    playlists: int = 30
    song_pool: int = 400
    genres: tuple[str, ...] = ("rock", "pop", "electronic", "jazz", "classical", "hiphop", "ambient", "folk", "metal", "reggae")
    per_genre: int = 200


def demo_password() -> str:
    """Sin clave fija en el código: estas cuentas incluyen administradores."""
    return os.environ.get("DEMO_PASSWORD") or secrets.token_urlsafe(16)


async def _clear_rows() -> None:
    users = await demo_user_ids()
    await clear_demo_social(users)
    await clear_demo_playlists()
    await clear_demo_playbacks()
    await clear_demo_catalog()
    await clear_demo_users()
    await rebuild_aggregates()


async def clear() -> None:
    await _clear_rows()
    remove_tones()


async def run_activity(sizes: Sizes = Sizes()) -> tuple[str, dict[str, int]]:
    """Empieza de cero para que repetirla deje los mismos conteos."""
    await _clear_rows()
    password = demo_password()
    rng = Random(RANDOM_SEED)
    now = datetime.now(UTC)
    accounts = await create_users(sizes, password, rng, now)
    await create_catalog(sizes, accounts, rng, now)
    summary = await create_activity(sizes, accounts, rng, now)
    await catch_up_aggregates()
    return password, summary


async def run_all(sizes: Sizes = Sizes()) -> tuple[str, dict[str, int]]:
    print(await import_catalog(sizes))
    return await run_activity(sizes)
