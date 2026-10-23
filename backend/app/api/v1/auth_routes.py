from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import bearer, current_user, issue_session, session_for_token
from app.core.config import get_settings
from app.core.db import get_db
from app.core.login_throttle import authenticate
from app.models.entities import User

router = APIRouter(prefix="/api/v1")


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": get_settings().app_mode}


@router.post("/auth/login")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    user, throttled = authenticate(db, payload.email, payload.password, client_ip)
    if throttled:
        raise HTTPException(429, "Too many login attempts. Try again later")
    if not user:
        raise HTTPException(401, "Invalid credentials")
    token, session = issue_session(db, user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": session.expires_at,
        "user": {"email": user.email, "role": user.role},
    }


@router.get("/auth/me")
def me(user: User = Depends(current_user)):
    return {"email": user.email, "role": user.role}


@router.post("/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    session = session_for_token(db, credentials.credentials) if credentials else None
    if session and session.user_id == user.id:
        db.delete(session)
        db.commit()
    return {"status": "signed_out"}
