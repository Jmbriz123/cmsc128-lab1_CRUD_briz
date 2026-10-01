from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import limit_recovery
from app.db.database import get_db
from app.schemas.auth import ForgotPasswordRequest, Message, ResetPasswordRequest
from app.services.account_service import PasswordUnchanged
from app.services.recovery_service import InvalidResetToken, deliver_recovery, reset_password
from app.services.session_service import clear_session_cookie

router = APIRouter(prefix="/auth", tags=["password recovery"])


@router.post("/forgot-password", status_code=202, response_model=Message,
             dependencies=[Depends(limit_recovery)])
def forgot_password(payload: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    if not settings.smtp_configured:
        raise HTTPException(503, "Password recovery email is not configured. Please contact the administrator.")
    background_tasks.add_task(deliver_recovery, str(payload.email))
    return {"detail": "If an account exists for that email, a reset link will arrive shortly. Check spam, or request another link if needed."}


@router.post("/reset-password", status_code=204, dependencies=[Depends(limit_recovery)])
def complete_reset(payload: ResetPasswordRequest, response: Response, db: Session = Depends(get_db)):
    try:
        reset_password(db, payload.token.get_secret_value(), payload.new_password.get_secret_value())
    except InvalidResetToken:
        raise HTTPException(400, "This reset link is invalid or expired. Request a new one.") from None
    except PasswordUnchanged:
        raise HTTPException(400, "Choose a password different from your current password") from None
    clear_session_cookie(response)
