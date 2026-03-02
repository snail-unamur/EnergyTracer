import math

import pytest

from src.plot.utilities.padding import pad


@pytest.mark.unit
@pytest.mark.parametrize(
    "lst,length,expected_len,expected_prefix",
    [
        pytest.param([1, 2, 3], 5, 5, [1, 2, 3], id="shorter_list"),
        pytest.param([1, 2, 3], 3, 3, [1, 2, 3], id="equal_length"),
        pytest.param([1, 2, 3, 4, 5], 3, 5, [1, 2, 3, 4, 5], id="longer_list"),
    ],
)
def test_pad(lst, length, expected_len, expected_prefix):
    result = pad(lst, length)
    assert len(result) == expected_len
    assert result[: len(expected_prefix)] == expected_prefix
    # Check any padded values are NaN
    for x in result[len(lst) :]:
        assert math.isnan(x)
