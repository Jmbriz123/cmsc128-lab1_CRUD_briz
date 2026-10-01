from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.rate_limit import limit_login
from app.db.database import get_db
from app.db.models import User
from app.schemas.auth import LoginRequest, PasswordChange
from app.schemas.user import UserCreate, UserPublic
from app.services import account_service, session_service

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserPublic, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        return account_service.register(db, payload)
    except account_service.DuplicateEmail:
        raise HTTPException(409, "An account with this email already exists") from None


@router.post("/login", response_model=UserPublic, dependencies=[Depends(limit_login)])
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    try:
        user, token = account_service.login(db, str(payload.email), payload.password.get_secret_value())
    except account_service.InvalidCredentials:
        raise HTTPException(401, "Invalid email or password") from None
    # Replacing the browser's login also revokes its previous session.
    session_service.revoke_session(db, request.cookies.get(settings.session_cookie_name))
    session_service.set_session_cookie(response, token)
    return user


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    session_service.revoke_session(db, request.cookies.get(settings.session_cookie_name))
    session_service.clear_session_cookie(response)


@router.post("/change-password", status_code=204)
def change_password(payload: PasswordChange, response: Response,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        account_service.change_password(db, user.id, payload)
    except account_service.InvalidCredentials:
        raise HTTPException(400, "Current password is incorrect") from None
    except account_service.PasswordUnchanged:
        raise HTTPException(400, "Choose a password different from your current password") from None
    session_service.clear_session_cookie(response)
