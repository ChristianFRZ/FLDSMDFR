import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from core.config import DB_PATH


def create_connection(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    """Crea una conexión a SQLite con PRAGMA foreign_keys y modo WAL activado."""
    conn = sqlite3.connect(
        str(db_path),
        check_same_thread=False,
        timeout=15.0,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


@contextmanager
def get_db_connection(
    db_path: Path | str = DB_PATH,
) -> Generator[sqlite3.Connection, None, None]:
    """Generador con context manager para manejar conexiones y transacciones atómicas."""
    conn = create_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
