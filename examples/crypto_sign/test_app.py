"""Test PII encryption and decryption using bigfoot crypto."""

from cryptography.fernet import Fernet

import bigfoot

from .app import decrypt_pii_field, encrypt_pii_field

# Generate a valid Fernet key for the example
TEST_KEY = Fernet.generate_key()


def test_encrypt_pii():
    bigfoot.crypto.mock_encrypt(returns=b"gAAAAABencrypted_ssn")

    with bigfoot:
        ciphertext = encrypt_pii_field(TEST_KEY, "123-45-6789")

    assert ciphertext == b"gAAAAABencrypted_ssn"

    bigfoot.crypto.assert_encrypt(plaintext_length=11)


def test_decrypt_pii():
    bigfoot.crypto.mock_decrypt(returns=b"123-45-6789")

    with bigfoot:
        plaintext = decrypt_pii_field(TEST_KEY, b"gAAAAABencrypted_ssn")

    assert plaintext == "123-45-6789"

    bigfoot.crypto.assert_decrypt(token=b"gAAAAABencrypted_ssn", ttl=None)
