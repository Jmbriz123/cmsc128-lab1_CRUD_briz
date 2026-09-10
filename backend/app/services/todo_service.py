from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoUpdate


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
    result = db.scalars(
        select(Todo).order_by(Todo.id)
    )

    return list(result)


def get_todo(db: Session, todo_id: int) -> Todo | None:
    return db.get(Todo, todo_id)


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
    db.delete(todo)
    db.commit()