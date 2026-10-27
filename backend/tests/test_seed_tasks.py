import pytest
from sqlalchemy import select

from app.db.models import Todo, User
from app.seed_tasks import SAMPLE_TASKS, UnknownAccount, seed_tasks


def test_seeds_personal_tasks_once_for_an_existing_account(db_session, make_user):
    owner = make_user("seeded@example.com")
    other = make_user("other@example.com")

    assert seed_tasks(db_session, "  Seeded@Example.com ") == len(SAMPLE_TASKS)
    assert seed_tasks(db_session, "seeded@example.com") == 0

    tasks = db_session.scalars(select(Todo)).all()
    assert len(tasks) == len(SAMPLE_TASKS)
    assert {task.user_id for task in tasks} == {owner.id}
    assert all(task.list_id is None for task in tasks)
    assert other.id not in {task.user_id for task in tasks}


def test_refuses_to_create_accounts(db_session):
    with pytest.raises(UnknownAccount):
        seed_tasks(db_session, "missing@example.com")
    assert db_session.scalar(select(User)) is None
    assert db_session.scalar(select(Todo)) is None
