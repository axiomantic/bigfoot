"""Test fetch_status using tripwire socket_mock."""

import tripwire

from .app import fetch_status


def test_fetch_status():
    (tripwire.socket
        .new_session()
        .expect("connect",  returns=None)
        .expect("sendall",  returns=None)
        .expect("recv",     returns=b"OK 200\r\n")
        .expect("close",    returns=None))

    with tripwire:
        result = fetch_status("monitoring.internal", 5000)

    assert result == "OK 200\r\n"

    tripwire.socket.assert_connect(host="monitoring.internal", port=5000)
    tripwire.socket.assert_sendall(data=b"STATUS\r\n")
    tripwire.socket.assert_recv(size=4096, data=b"OK 200\r\n")
    tripwire.socket.assert_close()
