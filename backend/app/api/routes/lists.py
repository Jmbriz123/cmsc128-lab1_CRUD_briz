from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import TaskList, User
from app.schemas.task_list import MemberAdd, MemberResponse, TaskListCreate, TaskListResponse
from app.services import list_service

router = APIRouter(prefix="/lists", tags=["lists"], dependencies=[Depends(get_current_user)])


def accessible_list(list_id: int, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)) -> TaskList:
    # Missing lists and lists the caller is not part of look identical.
    task_list = list_service.get_list(db, list_id, user_id=user.id)
    if task_list is None:
        raise HTTPException(404, "List not found")
    return task_list


def list_response(task_list: TaskList, owner_name: str, user: User) -> TaskListResponse:
    return TaskListResponse(id=task_list.id, name=task_list.name, owner_name=owner_name,
                            is_owner=task_list.owner_id == user.id)


def member_response(member: User, is_owner: bool) -> MemberResponse:
    return MemberResponse(id=member.id, email=member.email, display_name=member.display_name,
                          is_owner=is_owner)


@router.get("", response_model=list[TaskListResponse])
def get_lists(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [list_response(task_list, owner_name, user)
            for task_list, owner_name in list_service.get_lists(db, user_id=user.id)]


@router.post("", response_model=TaskListResponse, status_code=201)
def create_list(payload: TaskListCreate, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return list_response(list_service.create_list(db, payload.name, user_id=user.id),
                         user.display_name, user)


@router.delete("/{list_id}", status_code=204)
def delete_list(task_list: TaskList = Depends(accessible_list),
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        list_service.delete_list(db, task_list, user_id=user.id)
    except list_service.NotListOwner:
        raise HTTPException(403, "Only the list owner can delete this list") from None


@router.get("/{list_id}/members", response_model=list[MemberResponse])
def get_members(task_list: TaskList = Depends(accessible_list), db: Session = Depends(get_db)):
    return [member_response(member, is_owner)
            for member, is_owner in list_service.get_members(db, task_list)]


@router.post("/{list_id}/members", response_model=MemberResponse, status_code=201)
def add_member(payload: MemberAdd, task_list: TaskList = Depends(accessible_list),
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        member = list_service.add_member(db, task_list, str(payload.email), user_id=user.id)
    except list_service.NotListOwner:
        raise HTTPException(403, "Only the list owner can add members") from None
    except list_service.UnknownUser:
        raise HTTPException(404, "No account uses that email address") from None
    except list_service.AlreadyMember:
        raise HTTPException(409, "That user already has access to this list") from None
    return member_response(member, False)


@router.delete("/{list_id}/members/{member_id}", status_code=204)
def remove_member(member_id: int, task_list: TaskList = Depends(accessible_list),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        list_service.remove_member(db, task_list, member_id, user_id=user.id)
    except list_service.NotListOwner:
        raise HTTPException(403, "Only the list owner can remove other members") from None
    except list_service.MemberNotFound:
        raise HTTPException(404, "Member not found") from None
