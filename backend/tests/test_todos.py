from datetime import datetime

from app.services import todo_service


def create_todo(client, **overrides):
    payload = {"title": "Study FastAPI", "description": "Review CRUD patterns"}
    payload.update(overrides)
    response = client.post("/todos", json=payload)
    assert response.status_code == 201
    return response.json()


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_todo_applies_defaults_and_returns_timestamps(client):
    todo = create_todo(client, description=None)

    assert todo["title"] == "Study FastAPI"
    assert todo["description"] is None
    assert todo["completed"] is False
    assert todo["id"] > 0
    datetime.fromisoformat(todo["created_at"])
    datetime.fromisoformat(todo["updated_at"])


def test_list_todos_is_ordered_by_id(client):
    first = create_todo(client, title="First")
    second = create_todo(client, title="Second")

    response = client.get("/todos")

    assert response.status_code == 200
    assert [todo["id"] for todo in response.json()] == [first["id"], second["id"]]


def test_get_missing_todo_returns_404(client):
    response = client.get("/todos/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Todo not found"}


def test_update_todo_supports_partial_updates(client):
    todo = create_todo(client)

    response = client.patch(f"/todos/{todo['id']}", json={"completed": True})

    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == todo["title"]
    assert updated["description"] == todo["description"]
    assert updated["completed"] is True
    assert updated["updated_at"] >= todo["updated_at"]


def test_update_todo_can_clear_description(client):
    todo = create_todo(client)

    response = client.patch(f"/todos/{todo['id']}", json={"description": None})

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_update_missing_todo_returns_404(client):
    response = client.patch("/todos/999", json={"completed": True})

    assert response.status_code == 404
    assert response.json() == {"detail": "Todo not found"}


def test_delete_todo_returns_204_and_removes_todo(client):
    todo = create_todo(client)

    delete_response = client.delete(f"/todos/{todo['id']}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert delete_response.headers["x-undo-window-seconds"] == "10"
    assert client.get(f"/todos/{todo['id']}").status_code == 404


def test_deleted_todo_can_be_restored_during_undo_window(client):
    todo = create_todo(client)

    delete_response = client.delete(f"/todos/{todo['id']}")
    restore_response = client.post(f"/todos/{todo['id']}/restore")

    assert delete_response.status_code == 204
    assert restore_response.status_code == 200
    assert restore_response.json()["title"] == todo["title"]
    assert client.get(f"/todos/{todo['id']}").status_code == 200


def test_deleted_todo_is_hidden_from_list_until_restored(client):
    todo = create_todo(client)

    client.delete(f"/todos/{todo['id']}")

    assert client.get("/todos").json() == []


def test_active_todo_cannot_be_restored(client):
    todo = create_todo(client)

    response = client.post(f"/todos/{todo['id']}/restore")

    assert response.status_code == 404
    assert response.json() == {"detail": "Todo cannot be restored"}


def test_expired_deleted_todo_cannot_be_restored(client, monkeypatch):
    todo = create_todo(client)
    client.delete(f"/todos/{todo['id']}")
    monkeypatch.setattr(todo_service, "UNDO_WINDOW_SECONDS", 0)

    response = client.post(f"/todos/{todo['id']}/restore")

    assert response.status_code == 404
    assert client.get(f"/todos/{todo['id']}").status_code == 404


def test_delete_missing_todo_returns_404(client):
    response = client.delete("/todos/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Todo not found"}


def test_create_rejects_blank_and_oversized_titles(client):
    blank_response = client.post("/todos", json={"title": "   "})
    oversized_response = client.post("/todos", json={"title": "x" * 256})

    assert blank_response.status_code == 422
    assert oversized_response.status_code == 422


def test_create_rejects_missing_title(client):
    response = client.post("/todos", json={"description": "No title"})

    assert response.status_code == 422


def test_update_rejects_empty_and_null_non_nullable_fields(client):
    todo = create_todo(client)

    empty_response = client.patch(f"/todos/{todo['id']}", json={})
    null_title_response = client.patch(
        f"/todos/{todo['id']}",
        json={"title": None},
    )
    null_completed_response = client.patch(
        f"/todos/{todo['id']}",
        json={"completed": None},
    )

    assert empty_response.status_code == 422
    assert null_title_response.status_code == 422
    assert null_completed_response.status_code == 422


def test_update_rejects_blank_title(client):
    todo = create_todo(client)

    response = client.patch(f"/todos/{todo['id']}", json={"title": "   "})

    assert response.status_code == 422
