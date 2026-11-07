from pathlib import Path

from tests.boundaries import find_violations

APP = Path(__file__).resolve().parent.parent / "app"


def test_module_boundaries():
    assert find_violations(APP) == []


def test_detector_catches_private_import(tmp_path):
    folder = tmp_path / "modules" / "social"
    folder.mkdir(parents=True)
    (folder / "x.py").write_text("from app.modules.users.models import User\n")
    assert len(find_violations(tmp_path)) == 1


def test_detector_allows_public_import(tmp_path):
    folder = tmp_path / "modules" / "social"
    folder.mkdir(parents=True)
    (folder / "x.py").write_text("from app.modules.users.public import get_auth_state\n")
    assert find_violations(tmp_path) == []


def test_detector_catches_plain_import(tmp_path):
    folder = tmp_path / "modules" / "social"
    folder.mkdir(parents=True)
    (folder / "x.py").write_text("import app.modules.users.service\n")
    assert len(find_violations(tmp_path)) == 1


def test_detector_catches_module_import_from_package(tmp_path):
    folder = tmp_path / "modules" / "social"
    folder.mkdir(parents=True)
    (folder / "x.py").write_text("from app.modules import users\n")
    assert len(find_violations(tmp_path)) == 1


def test_detector_allows_own_module(tmp_path):
    folder = tmp_path / "modules" / "social"
    folder.mkdir(parents=True)
    (folder / "x.py").write_text("from app.modules.social.models import Tape\n")
    assert find_violations(tmp_path) == []
