"""Detector de importaciones que cruzan fronteras entre servicios o entre módulos."""
import ast
from pathlib import Path

SERVICE_PACKAGES = {"users_playlists", "catalog_streaming", "playback_metrics"}


def _imported(node: ast.AST) -> list[str]:
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        return [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    return []


def _owner(path: Path) -> str | None:
    """`social/x.py` pertenece al módulo `social`. Lo que está suelto en la raíz no tiene dueño."""
    return path.parts[0] if len(path.parts) > 1 else None


def find_violations(root: Path, package: str, allowed: set[str]) -> list[str]:
    """Revisa el código de `root` (la carpeta del paquete `package`).

    Marca los imports hacia el paquete de otro servicio que no estén en `allowed`
    y los imports de un módulo hacia otro que no pasan por su `public`.
    """
    root = Path(root)
    violations = []
    for path in sorted(root.rglob("*.py")):
        owner = _owner(path.relative_to(root))
        for node in ast.walk(ast.parse(path.read_text())):
            names = _imported(node)
            if not names:
                continue
            tops = {n.split(".")[0] for n in names}
            for top in sorted((tops & SERVICE_PACKAGES) - {package} - allowed):
                violations.append(f"{path}: importa el servicio {top}")
            if owner is None:
                continue
            prefix = f"{package}."
            foreign = {n.split(".")[1] for n in names if n.startswith(prefix)} - {owner}
            for module in sorted(foreign):
                if not any(n.startswith(f"{prefix}{module}.public") for n in names):
                    violations.append(f"{path}: {owner} importa {module} sin pasar por public")
    return violations
