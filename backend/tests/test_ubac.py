"""User-based access control: one account must never reach another's tasks."""
import pytest


@pytest.fixture()
def alice(client_for):
    return client_for("alice@example.com", "Alice")


@pytest.fixture()
def bob(client_for):
    return client_for("bob@example.com", "Bob")


def create(client, title, **fields):
    response = client.post("/todos", json={"title": title, **fields})
    assert response.status_code == 201
    return response.json()


def test_each_user_lists_only_their_own_tasks(alice, bob):
    alice_task = create(alice, "Alice's task", tag="shared-tag")
    bob_task = create(bob, "Bob's task", tag="shared-tag")

    assert [todo["id"] for todo in alice.get("/todos").json()] == [alice_task["id"]]
    assert [todo["id"] for todo in bob.get("/todos").json()] == [bob_task["id"]]
    # Filters narrow the caller's own tasks; they never widen the scope.
    assert [todo["id"] for todo in bob.get("/todos?tag=shared-tag").json()] == [bob_task["id"]]


@pytest.mark.parametrize("method,path,payload", [
    ("get", "/todos/{id}", None),
    ("patch", "/todos/{id}", {"title": "Hijacked", "completed": True}),
    ("delete", "/todos/{id}", None),
])
def test_other_users_task_ids_behave_as_missing(alice, bob, method, path, payload):
    task = create(alice, "Private to Alice")
    kwargs = {"json": payload} if payload is not None else {}

    response = getattr(bob, method)(path.format(id=task["id"]), **kwargs)

    # 404, not 403: Bob cannot even confirm that the ID exists.
    assert response.status_code == 404
    assert "Private to Alice" not in response.text
    unchanged = alice.get(f"/todos/{task['id']}")
    assert unchanged.status_code == 200
    assert unchanged.json()["title"] == "Private to Alice"
    assert unchanged.json()["completed"] is False


def test_other_users_cannot_restore_a_deleted_task(alice, bob):
    task = create(alice, "Deleted by Alice")
    assert alice.delete(f"/todos/{task['id']}").status_code == 204

    assert bob.post(f"/todos/{task['id']}/restore").status_code == 404
    assert alice.post(f"/todos/{task['id']}/restore").status_code == 200


def test_task_owner_comes_from_the_session_not_the_request(alice, bob):
    # A forged owner field is rejected by schema validation or ignored; the
    # task always belongs to the signed-in user.
    response = alice.post("/todos", json={"title": "Who owns me?", "user_id": 999})
    assert response.status_code in (201, 422)
    if response.status_code == 201:
        assert bob.get(f"/todos/{response.json()['id']}").status_code == 404
        assert alice.get(f"/todos/{response.json()['id']}").status_code == 200
