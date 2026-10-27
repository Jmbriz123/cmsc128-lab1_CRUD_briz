from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.todo import TodoCreate, TodoResponse, TodoUpdate
from app.services import todo_service


# The router-level dependency guarantees every route requires a session, even
# one that forgets to ask for the user. Each route still requests `user` so its
# queries can be scoped; FastAPI resolves the dependency once per request.
router = APIRouter(
    prefix="/todos",
    tags=["todos"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_todo(
    todo_data: TodoCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return todo_service.create_todo(db, todo_data, user_id=user.id)


@router.get(
    "",
    response_model=list[TodoResponse],
)
def get_todos(
    sort_by: Literal["date_added", "due_date", "priority", "tag"] = Query(
        default="date_added",
    ),
    sort_order: Literal["asc", "desc"] = Query(default="asc"),
    tag: str | None = Query(default=None, min_length=1, max_length=100),
    priority: Literal["low", "medium", "high"] | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return todo_service.get_todos(
        db,
        user_id=user.id,
        sort_by=sort_by,
        sort_order=sort_order,
        tag=tag,
        priority=priority,
    )


@router.get(
    "/{todo_id}",
    response_model=TodoResponse,
)
def get_todo(
    todo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = todo_service.get_todo(db, todo_id, user_id=user.id)

    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )

    return todo


@router.patch(
    "/{todo_id}",
    response_model=TodoResponse,
)
def update_todo(
    todo_id: int,
    todo_data: TodoUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = todo_service.get_todo(db, todo_id, user_id=user.id)

    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )

    return todo_service.update_todo(
        db,
        todo,
        todo_data,
    )


@router.delete(
    "/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_todo(
    todo_id: int,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = todo_service.get_todo(db, todo_id, user_id=user.id)

    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )

    todo_service.delete_todo(db, todo)
    response.headers["X-Undo-Window-Seconds"] = str(todo_service.UNDO_WINDOW_SECONDS)


@router.post(
    "/{todo_id}/restore",
    response_model=TodoResponse,
)
def restore_todo(
    todo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = todo_service.restore_todo(db, todo_id, user_id=user.id)

    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo cannot be restored",
        )

    return todo