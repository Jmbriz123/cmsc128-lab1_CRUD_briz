from datetime import datetime, timedelta, timezone

from fastapi import Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_token, hash_token
from app.db.models import AuthSession, User


def create_session(db: Session, user_id: int) -> str:
    token = generate_token()
    db.add(AuthSession(
        user_id=user_id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days),
    ))
    db.commit()
    return token


def resolve_user(db: Session, token: str | None) -> User | None:
    if not token or len(token) != 43:
        return None
    return db.scalar(
        select(User).join(AuthSession, AuthSession.user_id == User.id).where(
            AuthSession.token_hash == hash_token(token),
            AuthSession.expires_at > datetime.now(timezone.utc),
        )
    )


def revoke_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == hash_token(token)))
        db.commit()


def revoke_all_sessions(db: Session, user_id: int) -> None:
    # Caller commits together with the password update in one transaction.
    db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name, token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True, secure=settings.session_cookie_secure, samesite="lax", path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        httponly=True, secure=settings.session_cookie_secure, samesite="lax", path="/",
    )
    response.headers["Cache-Control"] = "no-store"
