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
def make_user(db_session):
    from app.db.models import User

    def make(email="crud@example.com", display_name="CRUD Tester"):
        user = User(email=email, display_name=display_name, password_hash="unused-fixture-hash")
        db_session.add(user)
        db_session.commit()
        return user
    return make


@pytest.fixture()
def client(anonymous_client, db_session, make_user):
    # Existing CRUD tests exercise real cookie authentication, not a bypass.
    from app.services.session_service import create_session
    from app.core.config import settings
    token = create_session(db_session, make_user().id)
    anonymous_client.cookies.set(settings.session_cookie_name, token)
    return anonymous_client


@pytest.fixture()
def client_for(anonymous_client, db_session, make_user):
    # Each call signs in a separate account with its own cookie jar, so tests
    # can act as two users against the same database.
    from app.services.session_service import create_session
    from app.core.config import settings
    clients = []

    def build(email, display_name="UBAC Tester"):
        test_client = TestClient(app, headers=dict(anonymous_client.headers))
        token = create_session(db_session, make_user(email, display_name).id)
        test_client.cookies.set(settings.session_cookie_name, token)
        clients.append(test_client)
        return test_client
    yield build
    for test_client in clients:
        test_client.close()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    from app.core.rate_limit import limiter
    with limiter.lock:
        limiter.attempts.clear()
