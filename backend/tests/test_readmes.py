import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IGNORED = {"node_modules", "dist", "__pycache__", "meloxo.egg-info"}
BRAND_DATA = ROOT / "docs" / "brand"


def folders_without_readme(root: Path) -> list[str]:
    missing = []
    for folder, children, files in os.walk(root):
        path = Path(folder)
        children[:] = [c for c in children if not c.startswith(".") and c not in IGNORED]
        if path == BRAND_DATA:
            children[:] = []  # los logos exportados son datos, los explica el README de docs/brand
        if "README.md" not in files:
            missing.append(str(path.relative_to(root)))
    return sorted(missing)


def test_every_folder_has_readme():
    assert folders_without_readme(ROOT) == []


def test_a_folder_without_readme_is_reported(tmp_path):
    (tmp_path / "con").mkdir()
    (tmp_path / "con" / "README.md").write_text("x")
    (tmp_path / "sin").mkdir()
    (tmp_path / "README.md").write_text("x")
    assert folders_without_readme(tmp_path) == ["sin"]
