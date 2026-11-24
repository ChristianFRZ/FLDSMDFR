"""Uso: python -m seed all|clear|users|catalog|activity"""
import argparse
import asyncio
import sys

import seed
from seed.catalog import import_catalog
from seed.internal import SeedError
from seed.users import DOMAIN


def _accounts(password: str) -> None:
    print(f"Cuentas: oyente00@{DOMAIN}, compositor00@{DOMAIN}, admin00@{DOMAIN}")
    print(f"Contraseña de las cuentas ficticias: {password}")


def _report(password: str, summary: dict[str, int]) -> None:
    print(f"Simulado: {summary['plays']} reproducciones, {summary['tapes']} casetes, {summary['playlists']} playlists.")
    _accounts(password)


async def main(command: str, sizes: seed.Sizes = seed.Sizes()) -> None:
    if command == "catalog":
        print(await import_catalog(sizes))
    elif command == "clear":
        await seed.clear()
        print("Datos simulados borrados. Las pistas de Jamendo y los usuarios reales siguen ahí.")
    elif command == "users":
        _accounts(await seed.run_users(sizes))
    else:
        _report(*await (seed.run_all(sizes) if command == "all" else seed.run_activity(sizes)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python -m seed", description="Semilla de demo de MELOXO")
    parser.add_argument("command", choices=["all", "clear", "users", "catalog", "activity"])
    try:
        asyncio.run(main(parser.parse_args().command))
    except (SeedError, RuntimeError) as error:
        sys.exit(f"Error: {error}")
