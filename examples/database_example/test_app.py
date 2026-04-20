"""Test save_user using bigfoot db."""

import bigfoot

from .app import save_user


def test_save_user():
    (bigfoot.db
        .new_session()
        .expect("connect",  returns=None)
        .expect("execute",  returns=[])
        .expect("commit",   returns=None)
        .expect("close",    returns=None))

    with bigfoot:
        save_user("Alice", "alice@example.com")

    bigfoot.db.assert_connect(database="app.db")
    bigfoot.db.assert_execute(
        sql="INSERT INTO users (name, email) VALUES (?, ?)",
        parameters=("Alice", "alice@example.com"),
    )
    bigfoot.db.assert_commit()
    bigfoot.db.assert_close()
