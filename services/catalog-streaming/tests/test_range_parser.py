import pytest

from app.modules.catalog.streaming import parse_range
from app.shared.errors import RangeNotSatisfiable

SIZE = 1000


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, None),
        ("bytes=0-99", (0, 99)),
        ("bytes=900-", (900, 999)),
        ("bytes=-100", (900, 999)),
        ("bytes=900-5000", (900, 999)),
        ("bytes=-5000", (0, 999)),
        ("bytes=0-1,4-5", None),
        ("items=0-1", None),
        ("bytes=abc", None),
    ],
)
def test_parse_range_valid_or_ignored(header, expected):
    assert parse_range(header, SIZE) == expected


@pytest.mark.parametrize("header", ["bytes=1000-", "bytes=50-10", "bytes=-0"])
def test_parse_range_unsatisfiable(header):
    with pytest.raises(RangeNotSatisfiable) as info:
        parse_range(header, SIZE)
    assert info.value.size == SIZE
