"""
Unit tests for app.core.security: password hashing, JWT tokens, credential encryption.

These tests do NOT require a database or Redis — they test pure logic.
"""
import time

import jwt
import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    encrypt_value,
    decrypt_value,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Password hash and verify."""

    def test_hash_password_returns_bcrypt_hash(self):
        hashed = hash_password("secret123")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_hash_password_is_different_each_time(self):
        h1 = hash_password("secret123")
        h2 = hash_password("secret123")
        assert h1 != h2  # bcrypt uses random salt

    def test_verify_correct_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_empty_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("", hashed) is False


class TestJWTokens:
    """JWT access and refresh token creation/decoding."""

    def test_create_access_token_has_correct_type(self):
        token = create_access_token("user-123")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_create_refresh_token_has_correct_type(self):
        token = create_refresh_token("user-456")
        payload = decode_token(token)
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"

    def test_access_token_includes_extra_claims(self):
        token = create_access_token("user-789", extra={"username": "admin"})
        payload = decode_token(token)
        assert payload["username"] == "admin"

    def test_decode_invalid_token_raises(self):
        with pytest.raises(jwt.PyJWTError):
            decode_token("invalid.token.here")

    def test_decode_tampered_token_raises(self):
        token = create_access_token("user-123")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(jwt.PyJWTError):
            decode_token(tampered)

    def test_access_token_has_future_expiry(self):
        token = create_access_token("user-123")
        payload = decode_token(token)
        assert payload["exp"] > int(time.time())


class TestCredentialEncryption:
    """Fernet encrypt/decrypt for stored credentials."""

    def test_encrypt_then_decrypt_roundtrip(self):
        original = "my-secret-password"
        encrypted = encrypt_value(original)
        assert encrypted != original
        decrypted = decrypt_value(encrypted)
        assert decrypted == original

    def test_encrypt_different_inputs_produce_different_outputs(self):
        e1 = encrypt_value("password1")
        e2 = encrypt_value("password2")
        assert e1 != e2

    def test_encrypt_same_input_produces_different_outputs(self):
        """Fernet uses random IV, so same input encrypts differently."""
        e1 = encrypt_value("same-password")
        e2 = encrypt_value("same-password")
        assert e1 != e2
        # But both decrypt to the same value
        assert decrypt_value(e1) == decrypt_value(e2) == "same-password"

    def test_decrypt_invalid_ciphertext_raises(self):
        with pytest.raises(Exception):
            decrypt_value("not-a-valid-fernet-token")
