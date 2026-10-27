"""Collaborative lists: only owners and added members may see or use a list."""
import pytest


@pytest.fixture()
def nikko(client_for):
    return client_for("nikko@example.com", "Nikko")


@pytest.fixture()
def victor(client_for):
    return client_for("victor@example.com", "Victor")


@pytest.fixture()
def outsider(client_for):
    return client_for("outsider@example.com", "Outsider")


def create_list(client, name):
    response = client.post("/lists", json={"name": name})
    assert response.status_code == 201
    return response.json()


def list_names(client):
    return [task_list["name"] for task_list in client.get("/lists").json()]


def test_activity_scenario_members_see_only_lists_they_belong_to(nikko, victor):
    nikko_list = create_list(nikko, "Nikko's Group List")
    create_list(victor, "Victor's Group List")
    assert nikko.post(f"/lists/{nikko_list['id']}/members",
                      json={"email": "victor@example.com"}).status_code == 201

    assert list_names(victor) == ["Nikko's Group List", "Victor's Group List"]
    assert list_names(nikko) == ["Nikko's Group List"]
    shared = victor.get("/lists").json()[0]
    assert shared["owner_name"] == "Nikko"
    assert shared["is_owner"] is False


def test_members_are_added_by_case_insensitive_email(nikko, victor):
    task_list = create_list(nikko, "Group")
    response = nikko.post(f"/lists/{task_list['id']}/members", json={"email": "  Victor@Example.COM "})
    assert response.status_code == 201
    assert response.json()["display_name"] == "Victor"

    members = nikko.get(f"/lists/{task_list['id']}/members").json()
    assert [(member["display_name"], member["is_owner"]) for member in members] == [
        ("Nikko", True), ("Victor", False),
    ]


@pytest.mark.parametrize("email,status", [
    ("nobody@example.com", 404),
    ("nikko@example.com", 409),
])
def test_adding_unknown_users_or_the_owner_is_rejected(nikko, email, status):
    task_list = create_list(nikko, "Group")
    assert nikko.post(f"/lists/{task_list['id']}/members", json={"email": email}).status_code == status


def test_adding_an_existing_member_twice_conflicts(nikko, victor):
    task_list = create_list(nikko, "Group")
    path = f"/lists/{task_list['id']}/members"
    assert nikko.post(path, json={"email": "victor@example.com"}).status_code == 201
    assert nikko.post(path, json={"email": "victor@example.com"}).status_code == 409


@pytest.mark.parametrize("method,path,payload", [
    ("get", "/lists/{id}/members", None),
    ("post", "/lists/{id}/members", {"email": "outsider@example.com"}),
    ("delete", "/lists/{id}/members/1", None),
    ("delete", "/lists/{id}", None),
])
def test_outsiders_cannot_tell_a_list_exists(nikko, outsider, method, path, payload):
    task_list = create_list(nikko, "Private group")
    kwargs = {"json": payload} if payload is not None else {}

    response = getattr(outsider, method)(path.format(id=task_list["id"]), **kwargs)

    assert response.status_code == 404
    assert "Private group" not in response.text
    assert list_names(nikko) == ["Private group"]


def test_members_cannot_perform_owner_actions(nikko, victor, outsider):
    task_list = create_list(nikko, "Group")
    nikko.post(f"/lists/{task_list['id']}/members", json={"email": "victor@example.com"})
    nikko.post(f"/lists/{task_list['id']}/members", json={"email": "outsider@example.com"})
    members = {member["display_name"]: member["id"]
               for member in nikko.get(f"/lists/{task_list['id']}/members").json()}

    assert victor.post(f"/lists/{task_list['id']}/members",
                       json={"email": "someone@example.com"}).status_code == 403
    assert victor.delete(f"/lists/{task_list['id']}/members/{members['Outsider']}").status_code == 403
    assert victor.delete(f"/lists/{task_list['id']}").status_code == 403
    assert list_names(outsider) == ["Group"]


def test_members_can_leave_and_owners_can_remove_members(nikko, victor, outsider):
    task_list = create_list(nikko, "Group")
    for email in ("victor@example.com", "outsider@example.com"):
        nikko.post(f"/lists/{task_list['id']}/members", json={"email": email})
    members = {member["display_name"]: member["id"]
               for member in nikko.get(f"/lists/{task_list['id']}/members").json()}

    assert victor.delete(f"/lists/{task_list['id']}/members/{members['Victor']}").status_code == 204
    assert nikko.delete(f"/lists/{task_list['id']}/members/{members['Outsider']}").status_code == 204

    assert list_names(victor) == []
    assert list_names(outsider) == []
    assert victor.get(f"/lists/{task_list['id']}/members").status_code == 404


def test_owner_deletes_a_list_for_everyone(nikko, victor):
    task_list = create_list(nikko, "Group")
    nikko.post(f"/lists/{task_list['id']}/members", json={"email": "victor@example.com"})

    assert nikko.delete(f"/lists/{task_list['id']}").status_code == 204
    assert list_names(nikko) == []
    assert list_names(victor) == []


@pytest.mark.parametrize("payload", [{"name": ""}, {"name": "   "}, {"name": "x" * 101}])
def test_list_names_are_validated(nikko, payload):
    assert nikko.post("/lists", json=payload).status_code == 422


@pytest.mark.parametrize("method,path,payload", [
    ("get", "/lists", None), ("post", "/lists", {"name": "Group"}),
    ("get", "/lists/1/members", None), ("post", "/lists/1/members", {"email": "a@example.com"}),
    ("delete", "/lists/1/members/1", None), ("delete", "/lists/1", None),
])
def test_every_list_operation_requires_login(anonymous_client, method, path, payload):
    kwargs = {"json": payload} if payload is not None else {}
    assert getattr(anonymous_client, method)(path, **kwargs).status_code == 401


@pytest.fixture()
def shared_list(nikko):
    task_list = create_list(nikko, "Nikko's Group List")
    nikko.post(f"/lists/{task_list['id']}/members", json={"email": "victor@example.com"})
    return task_list


def create_task(client, title, list_id=None):
    response = client.post("/todos", json={"title": title, "list_id": list_id})
    assert response.status_code == 201
    return response.json()


def titles(client, list_id=None):
    path = "/todos" if list_id is None else f"/todos?list_id={list_id}"
    response = client.get(path)
    assert response.status_code == 200
    return [todo["title"] for todo in response.json()]


def test_members_share_list_tasks_but_keep_personal_tasks_private(nikko, victor, shared_list):
    create_task(nikko, "Nikko personal")
    create_task(victor, "Victor personal")
    create_task(nikko, "Group task by Nikko", shared_list["id"])
    create_task(victor, "Group task by Victor", shared_list["id"])

    assert titles(nikko) == ["Nikko personal"]
    assert titles(victor) == ["Victor personal"]
    expected = ["Group task by Nikko", "Group task by Victor"]
    assert titles(nikko, shared_list["id"]) == expected
    assert titles(victor, shared_list["id"]) == expected


def test_members_can_update_delete_and_restore_list_tasks(nikko, victor, shared_list):
    task = create_task(nikko, "Group task", shared_list["id"])
    path = f"/todos/{task['id']}"

    assert victor.patch(path, json={"completed": True}).json()["completed"] is True
    assert victor.delete(path).status_code == 204
    assert nikko.post(f"{path}/restore").status_code == 200


def test_outsiders_cannot_use_a_list_or_its_tasks(nikko, outsider, shared_list):
    task = create_task(nikko, "Group task", shared_list["id"])
    path = f"/todos/{task['id']}"

    assert outsider.get(f"/todos?list_id={shared_list['id']}").status_code == 404
    assert outsider.post("/todos", json={"title": "Sneak in", "list_id": shared_list["id"]}).status_code == 404
    assert outsider.get(path).status_code == 404
    assert outsider.patch(path, json={"title": "Hijacked"}).status_code == 404
    assert outsider.delete(path).status_code == 404
    assert titles(nikko, shared_list["id"]) == ["Group task"]


def test_removed_members_lose_access_to_tasks_they_created(nikko, victor, shared_list):
    task = create_task(victor, "Victor's contribution", shared_list["id"])
    victor_id = next(member["id"] for member in nikko.get(f"/lists/{shared_list['id']}/members").json()
                     if member["display_name"] == "Victor")

    assert nikko.delete(f"/lists/{shared_list['id']}/members/{victor_id}").status_code == 204

    # Access follows list membership, not authorship; the task stays with the list.
    assert victor.get(f"/todos/{task['id']}").status_code == 404
    assert titles(victor) == []
    assert titles(nikko, shared_list["id"]) == ["Victor's contribution"]


def test_tasks_cannot_be_moved_between_lists_by_update(nikko, victor, shared_list):
    task = create_task(nikko, "Stay personal")

    response = nikko.patch(f"/todos/{task['id']}", json={"title": "Still personal", "list_id": shared_list["id"]})

    assert response.status_code == 200
    assert response.json()["list_id"] is None
    assert victor.get(f"/todos/{task['id']}").status_code == 404
