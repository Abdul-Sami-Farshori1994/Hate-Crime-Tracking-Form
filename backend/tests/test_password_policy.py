import pytest

from password_policy import validate_password_complexity


def test_accepts_strong_password():
    assert validate_password_complexity("Form#2026x") == "Form#2026x"


@pytest.mark.parametrize(
    "password",
    [
        "short1!",
        "alllowercase1!",
        "ALLUPPERCASE1!",
        "NoDigitsHere!",
        "NoSymbol123",
        "password1!",
        "aaaaAAA1!",
    ],
)
def test_rejects_weak_passwords(password):
    with pytest.raises(ValueError):
        validate_password_complexity(password)
