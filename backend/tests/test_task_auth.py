import pytest


@pytest.mark.parametrize("method,path,payload", [
    ("get", "/todos", None), ("get", "/todos/1", None),
    ("post", "/todos", {"title": "Unauthorized"}),
    ("patch", "/todos/1", {"title": "Unauthorized"}),
    ("delete", "/todos/1", None), ("post", "/todos/1/restore", None),
])
def test_every_task_operation_requires_login(anonymous_client, method, path, payload):
    kwargs = {"json": payload} if payload is not None else {}
    response = getattr(anonymous_client, method)(path, **kwargs)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"


def test_logout_revokes_task_access(client):
    assert client.get("/todos").status_code == 200
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/todos").status_code == 401


def test_health_remains_public(anonymous_client):
    assert anonymous_client.get("/health").status_code == 200
