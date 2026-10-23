"""Shared, sliding-window login limits stored in the application database."""

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.auth import hash_password, verify_password
from app.models.entities import AuditLog, AuthSession, LoginThrottle, User, utcnow

WINDOW = timedelta(minutes=15)
ACCOUNT_FAILURE_LIMIT = 5
IP_FAILURE_LIMIT = 30
_DUMMY_HASH = hash_password("not-a-real-account", salt=b"\x00" * 16)


def account_key(email: str) -> str:
    return "a:" + hashlib.sha256(email.strip().lower().encode()).hexdigest()


def _ip_key(client_ip: str) -> str:
    return "i:" + hashlib.sha256(client_ip.encode()).hexdigest()


def _ensure_bucket(db: Session, key: str, now: datetime) -> None:
    table = LoginThrottle.__table__
    if db.bind.dialect.name == "postgresql":
        statement = postgres_insert(table)
    elif db.bind.dialect.name == "sqlite":
        statement = sqlite_insert(table)
    else:
        raise RuntimeError("Login throttling requires PostgreSQL or SQLite")
    db.execute(
        statement.values(key=key, failures=[], blocked_until=None, updated_at=now)
        .on_conflict_do_nothing(index_elements=["key"])
    )


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def authenticate(
    db: Session,
    email: str,
    password: str,
    client_ip: str,
    *,
    now: datetime | None = None,
) -> tuple[User | None, bool]:
    """Return (user, throttled); update both buckets before returning a failure."""
    now = now or utcnow()
    email = email.strip().lower()
    keys = sorted((account_key(email), _ip_key(client_ip)))
    for key in keys:
        _ensure_bucket(db, key, now)
    buckets = {
        bucket.key: bucket
        for bucket in db.scalars(
            select(LoginThrottle)
            .where(LoginThrottle.key.in_(keys))
            .order_by(LoginThrottle.key)
            .with_for_update()
        )
    }
    if any(
        bucket.blocked_until and _utc(bucket.blocked_until) > now for bucket in buckets.values()
    ):
        db.commit()
        return None, True

    user = db.scalar(select(User).where(User.email == email))
    valid = verify_password(password, user.password_hash if user and user.active else _DUMMY_HASH)
    if user and user.active and valid:
        account = buckets[account_key(email)]
        account.failures = []
        account.blocked_until = None
        account.updated_at = now
        db.commit()
        return user, False

    throttled = False
    for key, limit in ((account_key(email), ACCOUNT_FAILURE_LIMIT), (_ip_key(client_ip), IP_FAILURE_LIMIT)):
        bucket = buckets[key]
        recent = [value for value in bucket.failures if _utc(datetime.fromisoformat(value)) > now - WINDOW]
        recent.append(now.isoformat())
        bucket.failures = recent
        bucket.updated_at = now
        if len(recent) >= limit:
            bucket.blocked_until = now + WINDOW
            throttled = True
    db.commit()
    return None, throttled


def unlock_user(db: Session, email: str) -> User:
    """Local administrator recovery; IP limits remain in force."""
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not user:
        raise ValueError("Account not found")
    db.execute(delete(LoginThrottle).where(LoginThrottle.key == account_key(user.email)))
    db.add(AuditLog(action="auth.unlocked", detail={"user_id": user.id}))
    db.commit()
    return user


def reset_password(db: Session, email: str, password: str) -> User:
    """Set a new password, clear the account lock, and revoke all sessions."""
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not user:
        raise ValueError("Account not found")
    user.password_hash = hash_password(password)
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.execute(delete(LoginThrottle).where(LoginThrottle.key == account_key(user.email)))
    db.add(AuditLog(action="auth.password_reset", detail={"user_id": user.id}))
    db.commit()
    return user
