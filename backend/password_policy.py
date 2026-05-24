"""Shared password complexity rules for credential updates."""

from __future__ import annotations

import re

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

_COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "password123",
        "12345678",
        "123456789",
        "qwerty123",
        "admin123",
        "letmein1",
        "welcome1",
        "changeme",
        "iloveyou",
    }
)

_COMPLEXITY_MESSAGE = (
    "Password must be at least 8 characters and include uppercase, lowercase, "
    "a number, and a symbol (e.g. ! @ # $)."
)


def validate_password_complexity(password: str) -> str:
    """Return password if valid; raise ValueError with a clear message if not."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(_COMPLEXITY_MESSAGE)
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"Password must be at most {PASSWORD_MAX_LENGTH} characters.")

    if not re.search(r"[A-Z]", password):
        raise ValueError(_COMPLEXITY_MESSAGE)
    if not re.search(r"[a-z]", password):
        raise ValueError(_COMPLEXITY_MESSAGE)
    if not re.search(r"\d", password):
        raise ValueError(_COMPLEXITY_MESSAGE)
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError(_COMPLEXITY_MESSAGE)

    normalized = password.strip().lower()
    if normalized in _COMMON_PASSWORDS:
        raise ValueError("Password is too common. Choose a stronger, unique password.")

    if len(set(password)) < 5:
        raise ValueError("Password is too simple. Use a mix of varied characters.")

    return password
