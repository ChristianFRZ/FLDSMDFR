from pathlib import Path

from meloxo_common.boundaries import find_violations

PACKAGE = Path(__file__).resolve().parent.parent / "gateway_auth"


def test_service_only_imports_meloxo_common():
    assert find_violations(PACKAGE, "gateway_auth", {"meloxo_common"}) == []
