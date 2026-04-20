"""Test Redis cache using bigfoot's redis plugin."""

import bigfoot
from dirty_equals import IsInstance

from .app import get_user


def test_get_user_cache_hit():
    bigfoot.redis.mock_command(
        "GET", returns=b'{"id": 1, "name": "Alice"}'
    )

    with bigfoot:
        result = get_user(1)

    assert result == {"id": 1, "name": "Alice"}
    bigfoot.redis.assert_command("GET", args=("user:1",), kwargs=IsInstance(dict))


def test_get_user_cache_miss():
    bigfoot.redis.mock_command("GET", returns=None)

    with bigfoot:
        result = get_user(42)

    assert result is None
    bigfoot.redis.assert_command("GET", args=("user:42",), kwargs=IsInstance(dict))
