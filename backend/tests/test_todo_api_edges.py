from datetime import datetime

import pytest


RESPONSE_FIELDS = {
    "id",
    "title",
    "description",
    "due_date",
    "priority",
    "tag",
    "completed",
    "created_at",
    "updated_at",
}


def create_todo(client, **overrides):
    payload = {"title": "Review notes"}
    payload.update(overrides)
    response = client.post("/todos", json=payload)
    assert response.status_code == 201
    return response.json()


def test_create_returns_trimmed_fields_and_complete_response_shape(client):
    todo = create_todo(
        client,
        title="  Review notes  ",
        description="  Chapter two  ",
        due_date="2026-10-03T09:15:00",
        priority="high",
        tag="  reading  ",
    )

    assert set(todo) == RESPONSE_FIELDS
    assert todo["title"] == "Review notes"
    assert todo["description"] == "Chapter two"
    assert todo["due_date"] == "2026-10-03T09:15:00"
    assert todo["priority"] == "high"
    assert todo["tag"] == "reading"
    assert todo["completed"] is False
    datetime.fromisoformat(todo["created_at"])
    datetime.fromisoformat(todo["updated_at"])


def test_title_and_tag_maximum_lengths_are_accepted(client):
    todo = create_todo(client, title="t" * 255, tag="g" * 100)

    assert len(todo["title"]) == 255
    assert len(todo["tag"]) == 100


@pytest.mark.parametrize(
    "payload",
    [
        {"title": None},
        {"title": 123},
        {"title": "Valid title", "priority": "urgent"},
        {"title": "Valid title", "due_date": "not-a-date"},
        {"title": "Valid title", "tag": ""},
        {"title": "Valid title", "tag": "g" * 101},
    ],
)
def test_create_rejects_invalid_field_values(client, payload):
    response = client.post("/todos", json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()


def test_get_todo_returns_full_response_shape(client):
    created = create_todo(client, description="A useful note")

    response = client.get(f"/todos/{created['id']}")

    assert response.status_code == 200
    assert set(response.json()) == RESPONSE_FIELDS
    assert response.json()["description"] == "A useful note"


@pytest.mark.parametrize(
    "sort_by, sort_order, expected_values",
    [
        (
            "due_date",
            "asc",
            [
                "2026-10-01T09:00:00",
                "2026-10-02T09:00:00",
                "2026-10-03T09:00:00",
                None,
            ],
        ),
        (
            "due_date",
            "desc",
            [
                "2026-10-03T09:00:00",
                "2026-10-02T09:00:00",
                "2026-10-01T09:00:00",
                None,
            ],
        ),
        ("priority", "asc", ["low", "medium", "medium", "high"]),
        ("priority", "desc", ["high", "medium", "medium", "low"]),
        ("tag", "asc", ["alpha", "beta", "gamma", None]),
        ("tag", "desc", ["gamma", "beta", "alpha", None]),
    ],
)
def test_sorting_keeps_missing_values_last(
    client,
    sort_by,
    sort_order,
    expected_values,
):
    create_todo(
        client,
        title="No optional value",
        due_date=None,
        priority="medium",
        tag=None,
    )
    create_todo(
        client,
        title="Later or middle value",
        due_date="2026-10-02T09:00:00",
        priority="medium",
        tag="beta",
    )
    create_todo(
        client,
        title="Earlier or low value",
        due_date="2026-10-01T09:00:00",
        priority="low",
        tag="alpha",
    )
    create_todo(
        client,
        title="High value",
        due_date="2026-10-03T09:00:00",
        priority="high",
        tag="gamma",
    )

    response = client.get(
        "/todos",
        params={"sort_by": sort_by, "sort_order": sort_order},
    )

    assert response.status_code == 200
    if sort_by == "due_date":
        assert [todo["due_date"] for todo in response.json()] == expected_values
    elif sort_by == "priority":
        assert [todo["priority"] for todo in response.json()] == expected_values
    else:
        assert [todo["tag"] for todo in response.json()] == expected_values


def test_date_added_sorting_supports_both_directions(client):
    created = [create_todo(client, title=f"Task {index}") for index in range(3)]
    ascending = client.get("/todos", params={"sort_by": "date_added"}).json()
    descending = client.get(
        "/todos",
        params={"sort_by": "date_added", "sort_order": "desc"},
    ).json()

    ascending_dates = [datetime.fromisoformat(todo["created_at"]) for todo in ascending]
    descending_dates = [
        datetime.fromisoformat(todo["created_at"]) for todo in descending
    ]
    assert ascending_dates == sorted(ascending_dates)
    assert descending_dates == sorted(descending_dates, reverse=True)
    assert {todo["id"] for todo in ascending} == {todo["id"] for todo in created}


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "x" * 256},
        {"priority": "urgent"},
        {"priority": None},
        {"tag": ""},
        {"tag": "g" * 101},
        {"due_date": "not-a-date"},
        {"completed": "sometimes"},
    ],
)
def test_update_rejects_invalid_field_values(client, payload):
    todo = create_todo(client)

    response = client.patch(f"/todos/{todo['id']}", json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()


def test_missing_or_invalid_ids_have_expected_status_codes(client):
    assert client.get("/todos/999").status_code == 404
    assert client.patch("/todos/999", json={"completed": True}).status_code == 404
    assert client.delete("/todos/999").status_code == 404
    assert client.post("/todos/999/restore").status_code == 404
    assert client.get("/todos/not-an-id").status_code == 422


def test_deleted_todo_cannot_be_updated_or_deleted_again(client):
    todo = create_todo(client)
    assert client.delete(f"/todos/{todo['id']}").status_code == 204

    update_response = client.patch(
        f"/todos/{todo['id']}",
        json={"completed": True},
    )
    delete_response = client.delete(f"/todos/{todo['id']}")

    assert update_response.status_code == 404
    assert delete_response.status_code == 404