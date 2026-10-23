import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from db.init_db import init_database


@pytest.fixture(scope="session")
def test_db_path() -> Generator[Path, None, None]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)

    # Establecer variable de entorno para que toda la app use esta DB temporal
    os.environ["FLDSMDFR_DB_PATH"] = str(db_path)

    import core.config

    core.config.DB_PATH = db_path
    import db.connection

    db.connection.DB_PATH = db_path

    # Inicializar schema y seeds
    init_database(db_path=db_path, seed=True)

    yield db_path

    if db_path.exists():
        db_path.unlink()


@pytest.fixture(scope="session")
def client(test_db_path: Path) -> Generator[TestClient, None, None]:
    from main import app

    with TestClient(app) as c:
        yield c
