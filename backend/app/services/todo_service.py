from datetime import datetime, timedelta

from sqlalchemy import case, delete, select
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
        due_date=todo_data.due_date,
        priority=todo_data.priority,
        tag=todo_data.tag,
    )

    db.add(todo)
    db.commit()
    db.refresh(todo)

    return todo


def get_todos(
    db: Session,
    sort_by: str = "date_added",
    sort_order: str = "asc",
    tag: str | None = None,
    priority: str | None = None,
) -> list[Todo]:
    _purge_expired_deleted_todos(db)
    query = select(Todo).where(Todo.deleted_at.is_(None))

    if tag is not None:
        query = query.where(Todo.tag == tag)
    if priority is not None:
        query = query.where(Todo.priority == priority)

    priority_order = case(
        (Todo.priority == "low", 1),
        (Todo.priority == "medium", 2),
        (Todo.priority == "high", 3),
        else_=0,
    )
    sort_columns = {
        "date_added": Todo.created_at,
        "due_date": Todo.due_date,
        "priority": priority_order,
        "tag": Todo.tag,
    }
    sort_column = sort_columns[sort_by]
    order_expression = (
        sort_column.desc() if sort_order == "desc" else sort_column.asc()
    ).nulls_last()
    query = query.order_by(order_expression, Todo.id.asc())

    return list(db.scalars(query))


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