"""Uso: python -m seed all|catalog|activity|clear"""
import argparse
import asyncio

import seed
from app.core.db import get_engine
from seed.catalog import import_catalog
from seed.users import DOMAIN


def _report(password: str, summary: dict[str, int]) -> None:
    print(f"Simulado: {summary['plays']} reproducciones, {summary['tapes']} casetes, {summary['playlists']} playlists.")
    print(f"Cuentas: oyente00@{DOMAIN}, compositor00@{DOMAIN}, admin00@{DOMAIN}")
    print(f"Contraseña de las cuentas ficticias: {password}")


async def main(command: str) -> None:
    try:
        if command == "catalog":
            print(await import_catalog(seed.Sizes()))
        elif command == "clear":
            await seed.clear()
            print("Datos simulados borrados. Las pistas de Jamendo y los usuarios reales siguen ahí.")
        else:
            _report(*await (seed.run_all() if command == "all" else seed.run_activity()))
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python -m seed", description="Semilla de demo de MELOXO")
    parser.add_argument("command", choices=["all", "catalog", "activity", "clear"])
    asyncio.run(main(parser.parse_args().command))
