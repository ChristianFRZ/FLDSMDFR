import ast
from pathlib import Path

MODULES_DIR = Path(__file__).resolve().parent.parent / "app" / "modules"
PRIVATE_LAYERS = {"models", "repository"}


def _imported_modules(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
            # `from app.modules.x import models` tambien cruza el limite.
            names.extend(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def test_modules_only_use_public_interfaces():
    violations = []
    for path in sorted(MODULES_DIR.glob("*/*.py")):
        owner = path.parent.name
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name in _imported_modules(tree):
            parts = name.split(".")
            if (
                len(parts) >= 4
                and parts[:2] == ["app", "modules"]
                and parts[2] != owner
                and parts[3] in PRIVATE_LAYERS
            ):
                violations.append(f"{path.relative_to(MODULES_DIR)} importa {name}")
    assert not violations, "Imports prohibidos entre modulos:\n" + "\n".join(violations)
