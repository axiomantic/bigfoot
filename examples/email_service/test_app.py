"""Test send_welcome_email using tripwire SMTP state machine assertions."""

from email.message import EmailMessage

from dirty_equals import IsInstance

import tripwire

from .app import send_welcome_email


def test_send_welcome_email_full_smtp_session():
    tripwire.smtp.new_session() \
        .expect("connect", returns=(220, b"OK")) \
        .expect("ehlo", returns=(250, b"OK")) \
        .expect("starttls", returns=(220, b"Ready")) \
        .expect("login", returns=(235, b"Authentication successful")) \
        .expect("send_message", returns={}) \
        .expect("quit", returns=(221, b"Bye"))

    with tripwire:
        send_welcome_email("alice@example.com", "Alice")

    tripwire.smtp.assert_connect(host="smtp.example.com", port=587)
    tripwire.smtp.assert_ehlo(name="example.com")
    tripwire.smtp.assert_starttls()
    tripwire.smtp.assert_login(user="noreply@example.com", password="secret")
    tripwire.smtp.assert_send_message(msg=IsInstance(EmailMessage))
    tripwire.smtp.assert_quit()
