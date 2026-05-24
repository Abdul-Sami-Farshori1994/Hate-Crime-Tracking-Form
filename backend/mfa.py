"""TOTP MFA helpers for admin accounts."""

from __future__ import annotations

import base64
import hashlib
import secrets

import pyotp

import config as app_config


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(*, secret: str, username: str, issuer: str | None = None) -> str:
    name = issuer or app_config.mfa_issuer_name()
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=name)


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    normalized = "".join(ch for ch in str(code).strip() if ch.isdigit())
    if len(normalized) != 6:
        return False
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(normalized, valid_window=1))


def encrypt_mfa_secret(secret: str) -> str:
    from cryptography.fernet import Fernet

    digest = hashlib.sha256(app_config.secret_key_bytes()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key).encrypt(secret.encode("utf-8")).decode("ascii")


def decrypt_mfa_secret(encrypted: str) -> str:
    from cryptography.fernet import Fernet, InvalidToken

    digest = hashlib.sha256(app_config.secret_key_bytes()).digest()
    key = base64.urlsafe_b64encode(digest)
    try:
        return Fernet(key).decrypt(encrypted.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return ""


def new_setup_token() -> str:
    return secrets.token_urlsafe(32)
