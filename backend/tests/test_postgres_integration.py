"""Opt-in checks against an isolated PostgreSQL database; never reset the app DB.

POSTGRES_TEST_URL points to a PostgreSQL role allowed to create temporary databases.
Each test owns a uniquely named database, which is removed in a finally block.
"""
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import generate_token, hash_password, hash_token, verify_password
from app.db.models import AuthSession, PasswordResetToken, Todo, User
from app.services.recovery_service import InvalidResetToken, reset_password
from app.services.session_service import create_session

pytestmark = pytest.mark.skipif(not os.getenv("POSTGRES_TEST_URL"), reason="POSTGRES_TEST_URL not configured")
BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture()
def postgres():
    url = make_url(os.environ["POSTGRES_TEST_URL"])
    database = "act2_test_" + uuid4().hex
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{database}"'))
    isolated_url = url.set(database=database)
    engine = create_engine(isolated_url)
    env = dict(os.environ, DATABASE_URL=isolated_url.render_as_string(hide_password=False))
    def migrate(*args):
        subprocess.run([sys.executable, "-m", "alembic", *args], env=env, cwd=BACKEND,
                       check=True, capture_output=True, text=True)
    try:
        migrate("upgrade", "head")
        yield engine, env, migrate
    finally:
        engine.dispose()
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE "{database}" WITH (FORCE)'))
        admin.dispose()


def test_migration_round_trip_and_constraints(postgres):
    engine, _, migrate = postgres
    with Session(engine) as db:
        db.add(Todo(title="Preserve through account migration"))
        user = User(email="migration@example.com", display_name="Migration", password_hash="hash-placeholder")
        db.add(user)
        db.commit()
        user_id = user.id
        assert user.created_at.utcoffset() == timedelta(0)
        for model in (AuthSession, PasswordResetToken):
            db.add(model(user_id=user_id, token_hash="a" * 64,
                         expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        db.commit()
    for model in (AuthSession, PasswordResetToken):
        with Session(engine) as db, pytest.raises(IntegrityError):
            db.add(model(user_id=user_id, token_hash="a" * 64, expires_at=datetime.now(timezone.utc)))
            db.commit()
        with Session(engine) as db, pytest.raises(IntegrityError):
            db.add(model(user_id=99999, token_hash="b" * 64, expires_at=datetime.now(timezone.utc)))
            db.commit()
    with Session(engine) as db, pytest.raises(IntegrityError):
        db.add(User(email="migration@example.com", display_name="Duplicate", password_hash="hash-placeholder"))
        db.commit()
    with Session(engine) as db:
        db.execute(delete(User).where(User.id == user_id))
        db.commit()
        assert db.scalar(select(AuthSession)) is None
        assert db.scalar(select(PasswordResetToken)) is None
    migrate("downgrade", "9a2b3c4d5e6f")
    assert "users" not in inspect(engine).get_table_names()
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT title FROM todos")) == "Preserve through account migration"
    migrate("upgrade", "head")
    migrate("check")


def test_sessions_and_accounts_survive_fresh_backend_processes(postgres):
    engine, env, _ = postgres
    with Session(engine) as db:
        user = User(email="persist@example.com", display_name="Persistent", password_hash=hash_password("a persistent long password"))
        db.add(user)
        db.commit()
        token = create_session(db, user.id)
    script = '''
import os
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
with TestClient(app) as client:
    client.cookies.set(settings.session_cookie_name, os.environ['TEST_SESSION_TOKEN'])
    response = client.get('/auth/me')
    assert response.status_code == 200
    assert response.json()['display_name'] == 'Persistent'
'''
    for _ in range(2):
        subprocess.run([sys.executable, "-c", script], cwd=BACKEND,
                       env=dict(env, TEST_SESSION_TOKEN=token), capture_output=True, check=True)


def test_only_one_concurrent_password_reset_succeeds(postgres):
    engine, _, _ = postgres
    token = generate_token()
    with Session(engine) as db:
        user = User(email="race@example.com", display_name="Race", password_hash=hash_password("the original long password"))
        db.add(user)
        db.commit()
        user_id = user.id
        create_session(db, user_id)
        db.add(PasswordResetToken(user_id=user_id, token_hash=hash_token(token),
                                 expires_at=datetime.now(timezone.utc) + timedelta(minutes=30)))
        db.commit()
    barrier = Barrier(2)
    def attempt(password):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            try:
                reset_password(db, token, password)
                return password
            except InvalidResetToken:
                return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ["first replacement password", "second replacement password"]))
    winners = [outcome for outcome in outcomes if outcome]
    assert len(winners) == 1
    with Session(engine) as db:
        assert verify_password(winners[0], db.get(User, user_id).password_hash)
        assert not verify_password("the original long password", db.get(User, user_id).password_hash)
        assert db.scalar(select(AuthSession)) is None
