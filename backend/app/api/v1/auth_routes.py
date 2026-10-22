from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import bearer, current_user, issue_session, session_for_token, verify_password
from app.core.config import get_settings
from app.core.db import get_db
from app.models.entities import User

router = APIRouter(prefix="/api/v1")


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": get_settings().app_mode}


@router.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
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
