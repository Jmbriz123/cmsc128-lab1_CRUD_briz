import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_token, hash_password, hash_token, verify_password
from app.db.database import SessionLocal
from app.db.models import PasswordResetToken, User
from app.services import email_service
from app.services.account_service import PasswordUnchanged, locked_user
from app.services.session_service import revoke_all_sessions

logger = logging.getLogger(__name__)


class InvalidResetToken(Exception):
    pass


def deliver_recovery(email: str) -> None:
    """Background work owns its connection; it never reuses a request-scoped session."""
    record_id = None
    try:
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email).with_for_update())
            if user is None:
                return
            token = generate_token()
            record = PasswordResetToken(
                user_id=user.id, token_hash=hash_token(token),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.reset_token_ttl_minutes),
            )
            db.add(record)
            db.commit()
            record_id = record.id
        reset_url = f"{settings.public_frontend_url}/#/reset-password?token={token}"
        email_service.send_reset_email(email, reset_url)
    except Exception:
        # Do not log exception strings: SMTP errors can contain addresses or message content.
        logger.error("Password reset delivery failed; check SMTP connectivity and configuration")
        if record_id is not None:
            try:
                with SessionLocal() as db:
                    db.execute(delete(PasswordResetToken).where(
                        PasswordResetToken.id == record_id, PasswordResetToken.consumed_at.is_(None)))
                    db.commit()
            except Exception:
                logger.error("Could not remove an undelivered reset token; it will expire automatically")


def reset_password(db: Session, token: str, new_password: str) -> None:
    digest = hash_token(token)
    user_id = db.scalar(select(PasswordResetToken.user_id).where(PasswordResetToken.token_hash == digest))
    if user_id is None:
        raise InvalidResetToken
    # All credential-changing operations lock User first, avoiding lock-order deadlocks.
    user = locked_user(db, user_id)
    if user is None:
        raise InvalidResetToken
    now = datetime.now(timezone.utc)
    consumed_id = db.scalar(update(PasswordResetToken).where(
        PasswordResetToken.token_hash == digest,
        PasswordResetToken.consumed_at.is_(None),
        PasswordResetToken.expires_at > now,
    ).values(consumed_at=now).returning(PasswordResetToken.id))
    if consumed_id is None:
        db.rollback()
        raise InvalidResetToken
    if verify_password(new_password, user.password_hash):
        db.rollback()
        raise PasswordUnchanged
    user.password_hash = hash_password(new_password)
    revoke_all_sessions(db, user_id)
    db.execute(delete(PasswordResetToken).where(
        PasswordResetToken.user_id == user_id, PasswordResetToken.id != consumed_id))
    db.commit()
