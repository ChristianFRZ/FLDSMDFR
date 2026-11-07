"""Detector de importaciones que cruzan la frontera entre módulos."""
import ast
from pathlib import Path


PACKAGE = "app.modules."


def _owner(path: Path) -> str | None:
    """`modules/social/x.py` pertenece a `social`. Lo que está fuera de un módulo no tiene dueño."""
    parts = path.parts
    return parts[1] if len(parts) > 2 and parts[0] == "modules" else None


def _imported(node: ast.AST) -> list[str]:
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        return [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    return []


def find_violations(root: str | Path) -> list[str]:
    """Lista los imports de un módulo hacia otro que no pasan por su public.py."""
    violations = []
    for path in Path(root).rglob("*.py"):
        owner = _owner(path.relative_to(root))
        if owner is None:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            names = _imported(node)
            if not names:
                continue
            targets = [n for n in names if n.startswith(PACKAGE)]
            foreign = {n.split(".")[2] for n in targets} - {owner}
            for module in foreign:
                allowed = any(n.startswith(f"{PACKAGE}{module}.public") for n in names)
                if not allowed:
                    violations.append(f"{path}: {owner} importa {module} sin pasar por public")
    return violations
