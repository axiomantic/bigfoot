"""Test get_user_count using bigfoot asyncpg."""

import bigfoot

from .app import get_user_count


async def test_get_user_count():
    (bigfoot.asyncpg
        .new_session()
        .expect("connect",  returns=None)
        .expect("fetchval", returns=42)
        .expect("close",    returns=None))

    with bigfoot:
        result = await get_user_count()

    assert result == 42

    bigfoot.asyncpg.assert_connect(host="localhost", database="app", user="app")
    bigfoot.asyncpg.assert_fetchval(query="SELECT count(*) FROM users", args=[])
    bigfoot.asyncpg.assert_close()
