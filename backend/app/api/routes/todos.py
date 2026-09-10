from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.todo import TodoCreate, TodoResponse, TodoUpdate
from app.services import todo_service


router = APIRouter(
    prefix="/todos",
    tags=["todos"],
)


@router.post(
    "",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_todo(
    todo_data: TodoCreate,
    db: Session = Depends(get_db),
):
    return todo_service.create_todo(db, todo_data)


@router.get(
    "",
    response_model=list[TodoResponse],
)
def get_todos(
    db: Session = Depends(get_db),
):
    return todo_service.get_todos(db)


@router.get(
    "/{todo_id}",
    response_model=TodoResponse,
)
def get_todo(
    todo_id: int,
    db: Session = Depends(get_db),
):
    todo = todo_service.get_todo(db, todo_id)

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
    db: Session = Depends(get_db),
):
    todo = todo_service.get_todo(db, todo_id)

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
    db: Session = Depends(get_db),
):
    todo = todo_service.get_todo(db, todo_id)

    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )

    todo_service.delete_todo(db, todo)