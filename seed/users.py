"""Cuentas ficticias de los tres roles, con altas repartidas en el periodo simulado."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from random import Random
from uuid import UUID

from seed import internal

DOMAIN = "demo.meloxo.dev"
NAMES = ("Ana", "Bruno", "Carla", "Diego", "Elena", "Fer", "Gabi", "Hugo", "Inés", "Julia", "Kike", "Lucía", "Mateo", "Nora")
SURNAMES = ("Ríos", "Vega", "Soto", "Luna", "Mora", "Paz", "Cruz", "Rey", "Salas", "Campos")
REQUESTS = ("Hago música en casa y quiero compartirla.", "Toco en una banda de barrio.", "Tengo un EP terminado.")


@dataclass(frozen=True)
class Account:
    id: UUID
    email: str
    name: str
    created_at: datetime


@dataclass(frozen=True)
class Accounts:
    listeners: list[Account]
    composers: list[Account]
    admins: list[Account]


@dataclass(frozen=True)
class DemoUser:
    email: str
    display_name: str
    role: str
    created_at: datetime
    request_message: str | None = None


async def create_users(sizes, password: str, rng: Random, now: datetime) -> Accounts:
    def joined() -> datetime:
        # Más altas hacia el final, como un producto que crece.
        return now - timedelta(days=sizes.days * (1 - rng.random() ** 0.6), hours=1)

    def make(prefix: str, role: str, count: int, requests: int = 0) -> list[DemoUser]:
        return [
            DemoUser(
                email=f"{prefix}{index:02}@{DOMAIN}",
                display_name=f"{rng.choice(NAMES)} {rng.choice(SURNAMES)}",
                role=role,
                created_at=joined(),
                request_message=REQUESTS[index % len(REQUESTS)] if index < requests else None,
            )
            for index in range(count)
        ]

    groups = (
        make("oyente", "listener", sizes.listeners, requests=min(3, sizes.listeners)),
        make("compositor", "composer", sizes.composers),
        make("admin", "admin", sizes.admins),
    )
    result = await internal.users().post("/users", {"users": [user for group in groups for user in group], "password": password})
    ids = {email: UUID(value) for email, value in result["ids"].items()}

    def accounts(group: list[DemoUser]) -> list[Account]:
        return [Account(ids[user.email], user.email, user.display_name, user.created_at) for user in group]

    return Accounts(*(accounts(group) for group in groups))
