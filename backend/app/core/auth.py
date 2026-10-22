"""Local password authentication with revocable, expiring bearer sessions."""

import hashlib
import hmac
import secrets
from datetime import UTC, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.entities import AuthSession, User, utcnow

ROLES = {"operator", "reviewer", "admin"}
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: bytes | None = None) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


def create_user(db: Session, email: str, password: str, role: str) -> User:
    email = email.strip().lower()
    if role not in ROLES or "@" not in email or len(email) > 255:
        raise ValueError("A valid email and role are required")
    user = User(email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def issue_session(db: Session, user: User) -> tuple[str, AuthSession]:
    token = secrets.token_urlsafe(32)
    session = AuthSession(
        user_id=user.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=utcnow() + timedelta(hours=12),
    )
    db.add(session)
    db.commit()
    return token, session


def session_for_token(db: Session, token: str) -> AuthSession | None:
    if len(token) > 128:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
    if not session:
        return None
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    return session if expires > utcnow() else None


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    session = session_for_token(db, credentials.credentials) if credentials else None
    user = db.get(User, session.user_id) if session else None
    if not user or not user.active:
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    return user


def require_role(*roles: str):
    def check(user: User = Depends(current_user)) -> User:
        if user.role not in roles and user.role != "admin":
            raise HTTPException(403, "Insufficient role")
        return user

    return check
