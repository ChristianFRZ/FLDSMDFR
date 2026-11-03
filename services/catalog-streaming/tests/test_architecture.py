"""Límites de catalog-streaming: no importa código de otros servicios ni del monolito."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_PREFIXES = (
    "app.modules.users",
    "app.modules.playlists",
    "app.modules.social",
    "app.modules.playback",
)


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
    return names


def test_service_does_not_import_other_services():
    violations = [
        f"{path.relative_to(ROOT)} importa {name}"
        for path in sorted((ROOT / "app").rglob("*.py"))
        for name in _imports(path)
        if name.startswith(FORBIDDEN_PREFIXES)
    ]
    assert not violations, "Imports de otros servicios:\n" + "\n".join(violations)


def test_only_catalog_module_lives_here():
    modules = {p.name for p in (ROOT / "app" / "modules").iterdir() if p.is_dir()}
    assert modules - {"__pycache__"} == {"catalog"}
