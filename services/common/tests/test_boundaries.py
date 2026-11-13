from meloxo_common.boundaries import find_violations

ALLOWED = {"meloxo_common"}


def _write(tmp_path, relative, text):
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_boundaries_flags_import_of_another_service(tmp_path):
    _write(tmp_path, "social/x.py", "from catalog_streaming.x import y\n")
    assert len(find_violations(tmp_path, "users_playlists", ALLOWED)) == 1


def test_boundaries_allows_meloxo_common(tmp_path):
    _write(tmp_path, "social/x.py", "from meloxo_common.errors import AppError\nimport meloxo_common.db\n")
    assert find_violations(tmp_path, "users_playlists", ALLOWED) == []


def test_boundaries_flags_module_import_without_public(tmp_path):
    _write(tmp_path, "social/x.py", "from users_playlists.users.models import User\n")
    assert len(find_violations(tmp_path, "users_playlists", ALLOWED)) == 1


def test_boundaries_flags_module_imported_from_package(tmp_path):
    _write(tmp_path, "social/x.py", "from users_playlists import users\n")
    assert len(find_violations(tmp_path, "users_playlists", ALLOWED)) == 1


def test_boundaries_allows_public_import(tmp_path):
    _write(tmp_path, "social/x.py", "from users_playlists.users.public import get_auth_state\n")
    assert find_violations(tmp_path, "users_playlists", ALLOWED) == []


def test_boundaries_allows_own_module(tmp_path):
    _write(tmp_path, "social/x.py", "from users_playlists.social.models import Tape\n")
    assert find_violations(tmp_path, "users_playlists", ALLOWED) == []


def test_boundaries_allowed_set_permits_a_service(tmp_path):
    _write(tmp_path, "social/x.py", "import catalog_streaming.contracts\n")
    assert find_violations(tmp_path, "users_playlists", {"catalog_streaming"}) == []
