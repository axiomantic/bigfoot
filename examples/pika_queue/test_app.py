"""Test RabbitMQ publishing using bigfoot pika."""

import bigfoot

from .app import publish_event


def test_publish_event():
    (bigfoot.pika
        .new_session()
        .expect("connect",  returns=None)
        .expect("channel",  returns=None)
        .expect("publish",  returns=None)
        .expect("close",    returns=None))

    with bigfoot:
        publish_event("mq.internal", "events", "order.created", b'{"order_id": 42}')

    bigfoot.pika.assert_connect(host="mq.internal", port=5672, virtual_host="/")
    bigfoot.pika.assert_channel()
    bigfoot.pika.assert_publish(
        exchange="events",
        routing_key="order.created",
        body=b'{"order_id": 42}',
        properties=None,
    )
    bigfoot.pika.assert_close()
