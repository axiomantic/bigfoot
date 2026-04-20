"""Test send_welcome_email using bigfoot SMTP state machine assertions."""

from email.message import EmailMessage

from dirty_equals import IsInstance

import bigfoot

from .app import send_welcome_email


def test_send_welcome_email_full_smtp_session():
    bigfoot.smtp.new_session() \
        .expect("connect", returns=(220, b"OK")) \
        .expect("ehlo", returns=(250, b"OK")) \
        .expect("starttls", returns=(220, b"Ready")) \
        .expect("login", returns=(235, b"Authentication successful")) \
        .expect("send_message", returns={}) \
        .expect("quit", returns=(221, b"Bye"))

    with bigfoot:
        send_welcome_email("alice@example.com", "Alice")

    bigfoot.smtp.assert_connect(host="smtp.example.com", port=587)
    bigfoot.smtp.assert_ehlo(name="example.com")
    bigfoot.smtp.assert_starttls()
    bigfoot.smtp.assert_login(user="noreply@example.com", password="secret")
    bigfoot.smtp.assert_send_message(msg=IsInstance(EmailMessage))
    bigfoot.smtp.assert_quit()
