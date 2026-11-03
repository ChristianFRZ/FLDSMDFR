"""Límites de users-playlists.

- No importa código de otros servicios (catalog, playback): solo los usa por app/clients.
- Dentro del servicio se conserva la regla del monolito: un módulo usa a otro solo por su
  `service` y sus `schemas`, nunca por `models` ni `repository`.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = ROOT / "app" / "modules"
FORBIDDEN_PREFIXES = ("app.modules.catalog", "app.modules.playback")
PRIVATE_LAYERS = {"models", "repository"}


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
            names.extend(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def test_service_does_not_import_other_services():
    violations = [
        f"{path.relative_to(ROOT)} importa {name}"
        for path in sorted((ROOT / "app").rglob("*.py"))
        for name in _imports(path)
        if name.startswith(FORBIDDEN_PREFIXES)
    ]
    assert not violations, "Imports de otros servicios:\n" + "\n".join(violations)


def test_modules_only_use_public_interfaces():
    violations = []
    for path in sorted(MODULES_DIR.glob("*/*.py")):
        owner = path.parent.name
        for name in _imports(path):
            parts = name.split(".")
            if (
                len(parts) >= 4
                and parts[:2] == ["app", "modules"]
                and parts[2] != owner
                and parts[3] in PRIVATE_LAYERS
            ):
                violations.append(f"{path.relative_to(MODULES_DIR)} importa {name}")
    assert not violations, "Imports prohibidos entre módulos:\n" + "\n".join(violations)
