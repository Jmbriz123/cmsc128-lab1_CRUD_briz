from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Response
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.security import hash_token
from app.db.database import get_db
from app.db.models import AuthSession, User
from app.schemas.user import UserPublic
from app.services.session_service import (clear_session_cookie, create_session, resolve_user,
                                          revoke_all_sessions, revoke_session, set_session_cookie)


def add_user(db):
    user = User(email="user@example.com", display_name="User", password_hash="hash-placeholder")
    db.add(user)
    db.commit()
    return user


def test_session_survives_new_database_connection(test_engine, db_session):
    user = add_user(db_session)
    token = create_session(db_session, user.id)
    record = db_session.scalar(select(AuthSession))
    assert len(token) == 43
    assert record.token_hash == hash_token(token)
    assert record.token_hash != token
    assert 29 <= (record.expires_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days <= 30
    with Session(test_engine) as fresh_db:
        assert resolve_user(fresh_db, token).id == user.id
        assert resolve_user(fresh_db, "x" * 43) is None
        assert resolve_user(fresh_db, None) is None


def test_expired_session_and_logout_revocation(db_session):
    user = add_user(db_session)
    expired = create_session(db_session, user.id)
    record = db_session.scalar(select(AuthSession))
    record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    assert resolve_user(db_session, expired) is None
    first, second = create_session(db_session, user.id), create_session(db_session, user.id)
    revoke_session(db_session, first)
    revoke_session(db_session, first)
    assert resolve_user(db_session, first) is None
    assert resolve_user(db_session, second).id == user.id
    revoke_all_sessions(db_session, user.id)
    db_session.commit()
    assert resolve_user(db_session, second) is None


def test_cookie_attributes(monkeypatch):
    response = Response()
    set_session_cookie(response, "token")
    cookie = response.headers["set-cookie"]
    for expected in ("HttpOnly", "Max-Age=2592000", "Path=/", "SameSite=lax"):
        assert expected in cookie
    assert "Domain=" not in cookie
    monkeypatch.setattr(settings, "session_cookie_secure", True)
    secure = Response()
    set_session_cookie(secure, "token")
    assert "Secure" in secure.headers["set-cookie"]
    clear = Response()
    clear_session_cookie(clear)
    assert "Max-Age=0" in clear.headers["set-cookie"]
    assert "Secure" in clear.headers["set-cookie"]
    assert clear.headers["cache-control"] == "no-store"


def test_auth_dependency_with_cookie(db_session):
    user = add_user(db_session)
    token = create_session(db_session, user.id)
    app = FastAPI()
    app.dependency_overrides[get_db] = lambda: db_session

    @app.get("/protected", response_model=UserPublic)
    def protected(user=Depends(get_current_user)):
        return user

    with TestClient(app) as client:
        assert client.get("/protected").status_code == 401
        client.cookies.set(settings.session_cookie_name, token)
        response = client.get("/protected")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert set(response.json()) == {"id", "email", "display_name"}
        revoke_session(db_session, token)
        assert client.get("/protected").status_code == 401
