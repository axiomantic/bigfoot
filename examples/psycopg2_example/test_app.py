"""Test save_user using tripwire psycopg2_mock."""

import tripwire

from .app import save_user


def test_save_user():
    (tripwire.psycopg2
        .new_session()
        .expect("connect",  returns=None)
        .expect("execute",  returns=[])
        .expect("commit",   returns=None)
        .expect("close",    returns=None))

    with tripwire:
        save_user("Alice", "alice@example.com")

    tripwire.psycopg2.assert_connect(host="localhost", dbname="app", user="app")
    tripwire.psycopg2.assert_execute(
        sql="INSERT INTO users (name, email) VALUES (%s, %s)",
        parameters=("Alice", "alice@example.com"),
    )
    tripwire.psycopg2.assert_commit()
    tripwire.psycopg2.assert_close()
