from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.auth import ProfileUpdate
from app.schemas.user import UserPublic
from app.services import account_service

router = APIRouter(prefix="/users", tags=["accounts"])


@router.patch("/me", response_model=UserPublic)
def update_profile(payload: ProfileUpdate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    try:
        return account_service.update_profile(db, user.id, payload)
    except account_service.DuplicateEmail:
        raise HTTPException(409, "An account with this email already exists") from None
    except account_service.InvalidCredentials:
        raise HTTPException(400, "Current password is required and must be correct to change email") from None
