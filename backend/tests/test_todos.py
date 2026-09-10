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
    assert todo["priority"] == "medium"
    assert todo["tag"] is None
    assert todo["due_date"] is None
    assert todo["id"] > 0
    datetime.fromisoformat(todo["created_at"])
    datetime.fromisoformat(todo["updated_at"])


def test_list_todos_is_ordered_by_id(client):
    first = create_todo(client, title="First")
    second = create_todo(client, title="Second")

    response = client.get("/todos")

    assert response.status_code == 200
    assert [todo["id"] for todo in response.json()] == [first["id"], second["id"]]


def test_todos_can_be_sorted_by_due_date_priority_and_tag(client):
    create_todo(
        client,
        title="No due date",
        due_date=None,
        priority="low",
        tag="zeta",
    )
    high = create_todo(
        client,
        title="High priority",
        due_date="2026-10-03T09:00:00",
        priority="high",
        tag="beta",
    )
    low = create_todo(
        client,
        title="Low priority",
        due_date="2026-10-01T09:00:00",
        priority="low",
        tag="alpha",
    )

    due_date_response = client.get("/todos?sort_by=due_date")
    priority_response = client.get("/todos?sort_by=priority&sort_order=desc")
    tag_response = client.get("/todos?sort_by=tag")

    assert [todo["id"] for todo in due_date_response.json()] == [
        low["id"],
        high["id"],
        due_date_response.json()[2]["id"],
    ]
    assert [todo["priority"] for todo in priority_response.json()] == [
        "high",
        "low",
        "low",
    ]
    assert [todo["tag"] for todo in tag_response.json()] == [
        "alpha",
        "beta",
        "zeta",
    ]


def test_todos_can_be_filtered_by_tag_and_priority(client):
    create_todo(client, title="Work one", tag="work", priority="high")
    matching = create_todo(client, title="Work two", tag="work", priority="low")
    create_todo(client, title="Home", tag="home", priority="low")

    tag_response = client.get("/todos", params={"tag": "work"})
    priority_response = client.get("/todos", params={"priority": "low"})
    combined_response = client.get(
        "/todos",
        params={"tag": "work", "priority": "low"},
    )

    assert len(tag_response.json()) == 2
    assert all(todo["tag"] == "work" for todo in tag_response.json())
    assert len(priority_response.json()) == 2
    assert all(todo["priority"] == "low" for todo in priority_response.json())
    assert [todo["id"] for todo in combined_response.json()] == [matching["id"]]


def test_todo_filter_and_sort_parameters_are_validated(client):
    invalid_sort = client.get("/todos?sort_by=unknown")
    invalid_order = client.get("/todos?sort_order=sideways")
    invalid_priority = client.get("/todos?priority=urgent")
    blank_tag = client.get("/todos?tag=")

    assert invalid_sort.status_code == 422
    assert invalid_order.status_code == 422
    assert invalid_priority.status_code == 422
    assert blank_tag.status_code == 422


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


def test_update_todo_supports_due_date_priority_and_tag(client):
    todo = create_todo(client)

    response = client.patch(
        f"/todos/{todo['id']}",
        json={
            "due_date": "2026-12-31T23:59:00",
            "priority": "high",
            "tag": "release",
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["due_date"] == "2026-12-31T23:59:00"
    assert updated["priority"] == "high"
    assert updated["tag"] == "release"


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
