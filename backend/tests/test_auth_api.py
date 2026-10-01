from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.security import verify_password
from app.db.models import AuthSession, PasswordResetToken, User

PASSWORD = "a sufficiently long password"
NEW_PASSWORD = "a different long password"


def register(client, email="student@example.com"):
    return client.post("/auth/register", json={"email": email, "display_name": " Student ", "password": PASSWORD})


def login(client, email="student@example.com", password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_registration_login_cookie_and_logout(anonymous_client, db_session):
    client = anonymous_client
    assert client.get("/auth/me").status_code == 401
    response = register(client, " Student@Example.com ")
    assert response.status_code == 201
    assert set(response.json()) == {"id", "email", "display_name"}
    assert response.json()["display_name"] == "Student"
    assert client.get("/auth/me").status_code == 401
    user = db_session.scalar(select(User))
    assert verify_password(PASSWORD, user.password_hash)
    assert register(client).status_code == 409
    response = login(client)
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    cookie = client.cookies.get(settings.session_cookie_name)
    assert client.get("/auth/me").json()["email"] == "student@example.com"
    assert client.post("/auth/logout").status_code == 204
    assert client.post("/auth/logout").status_code == 204
    client.cookies.set(settings.session_cookie_name, cookie)
    assert client.get("/auth/me").status_code == 401


def test_invalid_credentials_are_generic_and_throttled(anonymous_client, monkeypatch):
    client = anonymous_client
    monkeypatch.setattr(settings, "login_rate_limit", 2)
    register(client)
    wrong = login(client, password="wrong")
    missing = login(client, email="missing@example.com")
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()
    limited = login(client)
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) > 0


def test_profile_uniqueness_password_and_persistence(anonymous_client, db_session):
    client = anonymous_client
    register(client)
    register(client, "taken@example.com")
    login(client)
    assert client.patch("/users/me", json={"email": "changed@example.com"}).status_code == 400
    assert client.patch("/users/me", json={"email": "taken@example.com", "current_password": PASSWORD}).status_code == 409
    assert client.patch("/users/me", json={}).status_code == 422
    assert client.patch("/users/me", json={"display_name": None}).status_code == 422
    response = client.patch("/users/me", json={"email": " Changed@Example.com ", "display_name": "New Name", "current_password": PASSWORD})
    assert response.status_code == 200
    assert client.get("/auth/me").json()["display_name"] == "New Name"
    db_session.expire_all()
    assert db_session.scalar(select(User).where(User.email == "changed@example.com")).display_name == "New Name"
    assert login(client).status_code == 401
    assert login(client, email="changed@example.com").status_code == 200


def test_password_change_revokes_sessions_and_reset_tokens(anonymous_client, db_session):
    client = anonymous_client
    user_id = register(client).json()["id"]
    login(client)
    db_session.add(PasswordResetToken(user_id=user_id, token_hash="a" * 64,
                                     expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
    db_session.commit()
    assert client.post("/auth/change-password", json={"current_password": "wrong", "new_password": NEW_PASSWORD}).status_code == 400
    assert client.post("/auth/change-password", json={"current_password": PASSWORD, "new_password": NEW_PASSWORD}).status_code == 204
    assert client.get("/auth/me").status_code == 401
    assert db_session.scalar(select(AuthSession)) is None
    assert db_session.scalar(select(PasswordResetToken)) is None
    assert login(client).status_code == 401
    assert login(client, password=NEW_PASSWORD).status_code == 200


def test_login_rotates_and_revokes_previous_cookie(anonymous_client, db_session):
    register(anonymous_client)
    login(anonymous_client)
    first = anonymous_client.cookies.get(settings.session_cookie_name)
    login(anonymous_client)
    assert anonymous_client.cookies.get(settings.session_cookie_name) != first
    assert len(list(db_session.scalars(select(AuthSession)))) == 1
