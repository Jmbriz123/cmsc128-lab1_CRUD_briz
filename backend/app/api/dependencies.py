from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import User
from app.services.session_service import resolve_user


def get_current_user(request: Request, response: Response, db: Session = Depends(get_db)) -> User:
    response.headers["Cache-Control"] = "no-store"
    user = resolve_user(db, request.cookies.get(settings.session_cookie_name))
    if user is None:
        raise HTTPException(401, "Authentication required", headers={"Cache-Control": "no-store"})
    return user
