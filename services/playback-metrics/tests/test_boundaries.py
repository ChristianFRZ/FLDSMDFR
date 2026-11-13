from pathlib import Path

from meloxo_common.boundaries import find_violations

PACKAGE = Path(__file__).resolve().parent.parent / "playback_metrics"


def test_service_only_imports_meloxo_common():
    assert find_violations(PACKAGE, "playback_metrics", {"meloxo_common"}) == []
