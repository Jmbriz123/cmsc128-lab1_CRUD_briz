"""Account transactions. User row locks serialize credential changes and logins."""
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import PasswordResetToken, User
from app.schemas.auth import PasswordChange, ProfileUpdate
from app.schemas.user import UserCreate
from app.services.session_service import create_session, revoke_all_sessions


class DuplicateEmail(Exception):
    pass


class InvalidCredentials(Exception):
    pass


def locked_user(db: Session, user_id: int) -> User:
    return db.scalar(select(User).where(User.id == user_id).with_for_update()
                     .execution_options(populate_existing=True))


def register(db: Session, data: UserCreate) -> User:
    user = User(email=str(data.email), display_name=data.display_name,
                password_hash=hash_password(data.password.get_secret_value()))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if db.scalar(select(User.id).where(User.email == str(data.email))) is not None:
            raise DuplicateEmail from None
        raise
    db.refresh(user)
    return user


def login(db: Session, email: str, password: str) -> tuple[User, str]:
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    if not verify_password(password, user.password_hash if user else None):
        db.rollback()
        raise InvalidCredentials
    return user, create_session(db, user.id)


def update_profile(db: Session, user_id: int, data: ProfileUpdate) -> User:
    user = locked_user(db, user_id)
    if user is None:
        raise InvalidCredentials
    if data.email is not None and str(data.email) != user.email:
        password = data.current_password.get_secret_value() if data.current_password else ""
        if not verify_password(password, user.password_hash):
            db.rollback()
            raise InvalidCredentials
        user.email = str(data.email)
        # Links sent to the former email must no longer authorize a reset.
        db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    if data.display_name is not None:
        user.display_name = data.display_name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if data.email and db.scalar(select(User.id).where(User.email == str(data.email), User.id != user_id)):
            raise DuplicateEmail from None
        raise
    db.refresh(user)
    return user


def change_password(db: Session, user_id: int, data: PasswordChange) -> None:
    user = locked_user(db, user_id)
    if user is None or not verify_password(data.current_password.get_secret_value(), user.password_hash):
        db.rollback()
        raise InvalidCredentials
    user.password_hash = hash_password(data.new_password.get_secret_value())
    revoke_all_sessions(db, user_id)
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id))
    db.commit()
