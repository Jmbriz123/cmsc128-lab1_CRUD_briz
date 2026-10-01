import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import app


@pytest.fixture()
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(test_engine):
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )
    with TestingSessionLocal() as db:
        yield db


@pytest.fixture()
def anonymous_client(test_engine):
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app, headers={"X-Requested-With": "Daymark", "Origin": "http://localhost:5173"}) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def client(anonymous_client, db_session):
    # Existing CRUD tests exercise real cookie authentication, not a bypass.
    from app.db.models import User
    from app.services.session_service import create_session
    from app.core.config import settings
    user = User(email="crud@example.com", display_name="CRUD Tester", password_hash="unused-fixture-hash")
    db_session.add(user)
    db_session.commit()
    token = create_session(db_session, user.id)
    anonymous_client.cookies.set(settings.session_cookie_name, token)
    return anonymous_client


@pytest.fixture(autouse=True)
def reset_rate_limits():
    from app.core.rate_limit import limiter
    with limiter.lock:
        limiter.attempts.clear()
