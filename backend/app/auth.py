import hashlib
import secrets
from datetime import timedelta

from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import AuthSession, RateLimit, User, utcnow

password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash("constant-timing-placeholder-never-a-login")
COOKIE_NAME = "clinicflow_session"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def rate_limit(db: Session, scope: str, subject: str, limit: int, seconds: int):
    now = utcnow()
    bucket = int(now.timestamp()) // seconds
    key = f"{scope}:{hashlib.sha256(subject.encode()).hexdigest()[:40]}:{bucket}"
    stmt = insert(RateLimit).values(key=key, count=1, expires_at=now + timedelta(seconds=seconds * 2))
    count = db.scalar(stmt.on_conflict_do_update(index_elements=[RateLimit.key], set_={"count": RateLimit.count + 1}).returning(RateLimit.count))
    db.execute(delete(RateLimit).where(RateLimit.expires_at < now))
    db.commit()  # Attempts count even when downstream requests fail.
    if count > limit:
        raise HTTPException(429, "Too many requests. Please try again later.", headers={"Retry-After": str(seconds)})


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token or len(token) > 128:
        raise HTTPException(401, "Your session has expired. Please sign in.")
    user = db.scalar(select(User).join(AuthSession, AuthSession.user_id == User.id).where(
        AuthSession.token_hash == token_hash(token), AuthSession.expires_at > utcnow()))
    if user is None:
        raise HTTPException(401, "Your session has expired. Please sign in.")
    return user


def doctor(user: User = Depends(current_user)) -> User:
    if user.role != "doctor":
        raise HTTPException(403, "Only doctors can access clinical notes.")
    return user


def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=token_hash(token), user_id=user.id,
                       expires_at=utcnow() + timedelta(hours=get_settings().session_hours)))
    db.execute(delete(AuthSession).where(AuthSession.expires_at < utcnow()))
    return token
