"""Test chat_client using bigfoot sync_websocket."""

import bigfoot

from .app import chat_client


def test_chat_client():
    (bigfoot.sync_websocket
        .new_session()
        .expect("connect", returns=None)
        .expect("send",    returns=None)
        .expect("recv",    returns="echo: hello")
        .expect("send",    returns=None)
        .expect("recv",    returns="echo: world")
        .expect("close",   returns=None))

    with bigfoot:
        responses = chat_client("ws://chat.example.com/ws", ["hello", "world"])

    assert responses == ["echo: hello", "echo: world"]

    bigfoot.sync_websocket.assert_connect(uri="ws://chat.example.com/ws")
    bigfoot.sync_websocket.assert_send(message="hello")
    bigfoot.sync_websocket.assert_recv(message="echo: hello")
    bigfoot.sync_websocket.assert_send(message="world")
    bigfoot.sync_websocket.assert_recv(message="echo: world")
    bigfoot.sync_websocket.assert_close()
