"""Collaborative lists. A list is visible only to its owner and its members.

Lookups return None for lists the caller cannot see, so routes answer 404 and
never reveal that another user's list exists. Owner-only actions raise
NotListOwner for members, which routes answer with 403.
"""
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ListMember, TaskList, User


class NotListOwner(Exception):
    pass


class UnknownUser(Exception):
    pass


class AlreadyMember(Exception):
    pass


class MemberNotFound(Exception):
    pass


def accessible_list_ids(user_id: int):
    # Subquery of every list the user owns or was added to; shared with the
    # task service so list and task access use the same membership rule.
    member_of = select(ListMember.list_id).where(ListMember.user_id == user_id)
    return select(TaskList.id).where(or_(TaskList.owner_id == user_id, TaskList.id.in_(member_of)))


def get_list(db: Session, list_id: int, *, user_id: int) -> TaskList | None:
    return db.scalar(select(TaskList).where(
        TaskList.id == list_id, TaskList.id.in_(accessible_list_ids(user_id)),
    ))


def get_lists(db: Session, *, user_id: int) -> list[tuple[TaskList, str]]:
    rows = db.execute(
        select(TaskList, User.display_name).join(User, User.id == TaskList.owner_id)
        .where(TaskList.id.in_(accessible_list_ids(user_id)))
        .order_by(TaskList.created_at, TaskList.id)
    )
    return [(task_list, owner_name) for task_list, owner_name in rows]


def create_list(db: Session, name: str, *, user_id: int) -> TaskList:
    task_list = TaskList(owner_id=user_id, name=name)
    db.add(task_list)
    db.commit()
    db.refresh(task_list)
    return task_list


def _require_owner(task_list: TaskList, user_id: int) -> None:
    if task_list.owner_id != user_id:
        raise NotListOwner


def delete_list(db: Session, task_list: TaskList, *, user_id: int) -> None:
    _require_owner(task_list, user_id)
    db.delete(task_list)
    db.commit()


def get_members(db: Session, task_list: TaskList) -> list[tuple[User, bool]]:
    owner = db.get(User, task_list.owner_id)
    members = db.scalars(
        select(User).join(ListMember, ListMember.user_id == User.id)
        .where(ListMember.list_id == task_list.id).order_by(ListMember.created_at, User.id)
    )
    return [(owner, True), *((member, False) for member in members)]


def add_member(db: Session, task_list: TaskList, email: str, *, user_id: int) -> User:
    _require_owner(task_list, user_id)
    member = db.scalar(select(User).where(User.email == email))
    if member is None:
        raise UnknownUser
    if member.id == task_list.owner_id:
        raise AlreadyMember
    db.add(ListMember(list_id=task_list.id, user_id=member.id))
    try:
        db.commit()
    except IntegrityError:
        # The composite primary key also catches two simultaneous adds.
        db.rollback()
        raise AlreadyMember from None
    return member


def remove_member(db: Session, task_list: TaskList, member_id: int, *, user_id: int) -> None:
    # Owners may remove anyone; a member may only remove themselves (leave).
    if member_id != user_id:
        _require_owner(task_list, user_id)
    result = db.execute(delete(ListMember).where(
        ListMember.list_id == task_list.id, ListMember.user_id == member_id,
    ))
    if result.rowcount == 0:
        db.rollback()
        raise MemberNotFound
    db.commit()
