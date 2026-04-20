"""Test native library calls using bigfoot native."""

import bigfoot

from .app import compute_distance


def test_compute_distance():
    bigfoot.native.mock_call("libm", "sqrt", returns=5.0)

    with bigfoot:
        result = compute_distance(0.0, 0.0, 3.0, 4.0)

    assert result == 5.0

    bigfoot.native.assert_call(
        library="libm", function="sqrt", args=(25.0,),
    )
