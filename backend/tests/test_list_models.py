import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.db.models import ListMember, TaskList, Todo, User


@pytest.fixture()
def enforce_foreign_keys(test_engine):
    # SQLite disables FK enforcement by default; enable it for this connection.
    with test_engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def test_a_user_can_be_added_to_a_list_only_once(db_session, make_user):
    owner, member = make_user("owner@example.com"), make_user("member@example.com")
    task_list = TaskList(owner_id=owner.id, name="Group")
    db_session.add(task_list)
    db_session.commit()
    db_session.add(ListMember(list_id=task_list.id, user_id=member.id))
    db_session.commit()

    db_session.add(ListMember(list_id=task_list.id, user_id=member.id))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_deleting_a_list_removes_its_memberships_and_tasks(enforce_foreign_keys, db_session, make_user):
    owner, member = make_user("owner@example.com"), make_user("member@example.com")
    task_list = TaskList(owner_id=owner.id, name="Group")
    db_session.add(task_list)
    db_session.commit()
    db_session.add_all([
        ListMember(list_id=task_list.id, user_id=member.id),
        Todo(title="Group task", user_id=member.id, list_id=task_list.id),
        Todo(title="Personal task", user_id=member.id),
    ])
    db_session.commit()

    db_session.execute(delete(TaskList).where(TaskList.id == task_list.id))
    db_session.commit()

    assert db_session.scalar(select(ListMember)) is None
    assert db_session.scalars(select(Todo.title)).all() == ["Personal task"]


def test_deleting_an_owner_removes_their_lists(enforce_foreign_keys, db_session, make_user):
    owner = make_user("owner@example.com")
    db_session.add(TaskList(owner_id=owner.id, name="Group"))
    db_session.commit()

    db_session.execute(delete(User).where(User.id == owner.id))
    db_session.commit()

    assert db_session.scalar(select(TaskList)) is None


def test_tasks_and_memberships_reject_unknown_lists(enforce_foreign_keys, db_session, make_user):
    user = make_user()
    for row in (Todo(title="Orphan", user_id=user.id, list_id=999), ListMember(list_id=999, user_id=user.id)):
        db_session.add(row)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()
