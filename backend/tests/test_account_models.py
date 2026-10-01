from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.db.models import AuthSession, PasswordResetToken, User


def make_user(email="student@example.com"):
    return User(email=email, display_name="Student", password_hash="hash-placeholder")


def test_email_normalization_and_unique_identifier(db_session):
    user = make_user("  Student@Example.COM ")
    db_session.add(user)
    db_session.commit()
    assert user.email == "student@example.com"
    assert user.created_at is not None
    assert user.updated_at is not None
    db_session.add(make_user())
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


@pytest.mark.parametrize("model", [AuthSession, PasswordResetToken])
def test_token_uniqueness_and_persistence(db_session, model):
    user = make_user()
    db_session.add(user)
    db_session.flush()
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    token = model(user_id=user.id, token_hash="a" * 64, expires_at=expires)
    db_session.add(token)
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(model, token.id).token_hash == "a" * 64
    if model is PasswordResetToken:
        assert token.consumed_at is None
    db_session.add(model(user_id=user.id, token_hash="a" * 64, expires_at=expires))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


@pytest.mark.parametrize("model", [AuthSession, PasswordResetToken])
def test_foreign_key_and_database_delete_cascade(test_engine, db_session, model):
    # SQLite disables FK enforcement by default; enable it for this connection.
    with test_engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db_session.add(model(user_id=999, token_hash="a" * 64, expires_at=expires))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
    user = make_user()
    db_session.add(user)
    db_session.flush()
    db_session.add(model(user_id=user.id, token_hash="b" * 64, expires_at=expires))
    db_session.commit()
    db_session.execute(delete(User).where(User.id == user.id))
    db_session.commit()
    assert db_session.scalar(select(model)) is None
