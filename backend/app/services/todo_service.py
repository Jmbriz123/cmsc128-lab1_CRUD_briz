from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoUpdate


UNDO_WINDOW_SECONDS = 10


def _purge_expired_deleted_todos(db: Session) -> None:
    expiration_time = datetime.utcnow() - timedelta(seconds=UNDO_WINDOW_SECONDS)
    db.execute(
        delete(Todo).where(
            Todo.deleted_at.is_not(None),
            Todo.deleted_at < expiration_time,
        )
    )
    db.commit()


def create_todo(db: Session, todo_data: TodoCreate) -> Todo:
    # instandiate todo model
    todo = Todo(
        title=todo_data.title,
        description=todo_data.description,
    )

    db.add(todo)
    db.commit()
    db.refresh(todo)

    return todo


def get_todos(db: Session) -> list[Todo]:
    _purge_expired_deleted_todos(db)
    result = db.scalars(
        select(Todo)
        .where(Todo.deleted_at.is_(None))
        .order_by(Todo.id)
    )

    return list(result)


def get_todo(db: Session, todo_id: int) -> Todo | None:
    _purge_expired_deleted_todos(db)
    return db.scalar(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.deleted_at.is_(None),
        )
    )


def update_todo(
    db: Session,
    todo: Todo,
    todo_data: TodoUpdate,
) -> Todo:

    update_data = todo_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(todo, field, value)

    db.commit()
    db.refresh(todo)

    return todo


def delete_todo(db: Session, todo: Todo) -> None:
    todo.deleted_at = datetime.utcnow()
    db.commit()


def restore_todo(db: Session, todo_id: int) -> Todo | None:
    _purge_expired_deleted_todos(db)
    todo = db.scalar(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.deleted_at.is_not(None),
        )
    )

    if todo is None:
        return None

    todo.deleted_at = None
    db.commit()
    db.refresh(todo)

    return todo