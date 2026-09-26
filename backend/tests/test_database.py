import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models.todo import Todo
from app.schemas.todo import TodoUpdate
from app.services import todo_service


def test_todo_creation_persists_database_defaults(db_session):
    todo = Todo(title="Persist this task")
    db_session.add(todo)
    db_session.commit()
    todo_id = todo.id

    db_session.expire_all()
    persisted = db_session.scalar(select(Todo).where(Todo.id == todo_id))

    assert persisted is not None
    assert persisted.title == "Persist this task"
    assert persisted.completed is False
    assert persisted.priority == "medium"
    assert persisted.created_at is not None
    assert persisted.updated_at is not None
    assert persisted.deleted_at is None


def test_todo_update_is_persisted(db_session):
    todo = Todo(title="Original title")
    db_session.add(todo)
    db_session.commit()
    todo_id = todo.id

    todo_service.update_todo(
        db_session,
        todo,
        TodoUpdate(title="Updated title", completed=True, priority="high"),
    )
    db_session.expire_all()
    persisted = db_session.scalar(select(Todo).where(Todo.id == todo_id))

    assert persisted.title == "Updated title"
    assert persisted.completed is True
    assert persisted.priority == "high"


def test_soft_delete_and_restore_are_persisted(db_session):
    todo = Todo(title="Restorable task")
    db_session.add(todo)
    db_session.commit()
    todo_id = todo.id

    todo_service.delete_todo(db_session, todo)
    db_session.expire_all()
    deleted = db_session.get(Todo, todo_id)
    assert deleted.deleted_at is not None

    restored = todo_service.restore_todo(db_session, todo_id)

    assert restored is not None
    assert restored.deleted_at is None
    assert db_session.get(Todo, todo_id).deleted_at is None


def test_database_rejects_a_missing_required_title(db_session):
    db_session.add(Todo(title=None))

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()