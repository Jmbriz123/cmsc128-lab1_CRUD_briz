import pytest
from pydantic import ValidationError

from app.core.security import hash_password, verify_password
from app.schemas.user import UserCreate, UserPublic

PASSWORD = "  long Unicode password 🍎  "


def test_argon2_hash_is_salted_and_password_is_not_trimmed():
    hashed = hash_password(PASSWORD)
    assert hashed.startswith("$argon2id$")
    assert PASSWORD not in hashed
    assert hash_password(PASSWORD) != hashed
    assert verify_password(PASSWORD, hashed)
    assert not verify_password(PASSWORD.strip(), hashed)
    assert not verify_password(PASSWORD, None)
    assert not verify_password(PASSWORD, "not-a-hash")
    assert not verify_password("x" * 129, hashed)


@pytest.mark.parametrize("password", ["x" * 14, "x" * 129])
def test_password_bounds(password):
    with pytest.raises(ValueError):
        hash_password(password)
    with pytest.raises(ValidationError):
        UserCreate(email="user@example.com", display_name="User", password=password)


def test_account_validation_and_public_projection():
    user = UserCreate(email="  Student@Example.COM ", display_name=" Student ", password=PASSWORD)
    assert user.email == "student@example.com"
    assert user.display_name == "Student"
    assert user.password.get_secret_value() == PASSWORD
    assert PASSWORD not in repr(user)
    public = UserPublic.model_validate(dict(id=1, email=user.email, display_name=user.display_name,
                                          password_hash="secret", token="secret"))
    assert set(public.model_dump()) == {"id", "email", "display_name"}


@pytest.mark.parametrize("changes", [{"email": "invalid"}, {"display_name": "   "},
                                      {"display_name": "x" * 101}])
def test_invalid_account_fields(changes):
    payload = dict(email="user@example.com", display_name="User", password=PASSWORD)
    payload.update(changes)
    with pytest.raises(ValidationError):
        UserCreate(**payload)


