import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.core.request_security import protect_requests, safe_validation_error
from app.schemas.user import UserCreate

@pytest.fixture()
def security_client():
    app = FastAPI()
    app.middleware("http")(protect_requests)
    app.add_exception_handler(RequestValidationError, safe_validation_error)

    @app.post("/auth/probe")
    def probe(payload: UserCreate):
        return {"email": payload.email}

    @app.post("/auth/logout")
    def bodyless():
        return {"ok": True}

    @app.get("/auth/me")
    def account():
        return {"ok": True}

    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("origin", ["https://evil.example", "null", "http://localhost:5173.evil.example"])
def test_rejects_untrusted_origins(security_client, origin):
    response = security_client.post("/auth/logout", headers={"Origin": origin, "X-Requested-With": "Daymark"})
    assert response.status_code == 403


def test_custom_header_and_json_are_required(security_client):
    assert security_client.post("/auth/logout").status_code == 403
    headers = {"Origin": "http://localhost:5173", "X-Requested-With": "Daymark"}
    assert security_client.post("/auth/logout", headers=headers).status_code == 200
    assert security_client.post("/auth/logout", headers=headers, data={"a": "b"}).status_code == 415
    # Non-browser clients may omit Origin, but never the custom header.
    assert security_client.post("/auth/logout", headers={"X-Requested-With": "Daymark"}).status_code == 200


def test_sensitive_validation_input_is_not_returned(security_client):
    response = security_client.post("/auth/probe", headers={"X-Requested-With": "Daymark"},
                                    json={"email": "user@example.com", "display_name": "User", "password": "secret"})
    assert response.status_code == 422
    assert "secret" not in response.text
    assert all(set(error) == {"loc", "msg", "type"} for error in response.json()["detail"])
    assert response.headers["cache-control"] == "no-store"
    assert security_client.get("/auth/me").headers["cache-control"] == "no-store"


