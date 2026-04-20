"""Test memcache user profile caching using bigfoot memcache."""

import bigfoot

from .app import cache_user_profile, get_user_profile


def test_cache_hit():
    bigfoot.memcache.mock_command("GET", returns=b'{"name": "Alice"}')

    with bigfoot:
        from pymemcache.client.base import Client
        client = Client(("localhost", 11211))
        result = get_user_profile(client, "42")

    assert result == '{"name": "Alice"}'

    bigfoot.memcache.assert_get(command="GET", key="profile:42")


def test_cache_write():
    bigfoot.memcache.mock_command("SET", returns=True)

    with bigfoot:
        from pymemcache.client.base import Client
        client = Client(("localhost", 11211))
        cache_user_profile(client, "42", '{"name": "Alice"}', ttl=600)

    bigfoot.memcache.assert_set(
        command="SET",
        key="profile:42",
        value=b'{"name": "Alice"}',
        expire=600,
    )
