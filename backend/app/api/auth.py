from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.assets import get_db
from backend.app.core.security import decode_token, issue_token, verify_password
from backend.app.db.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    return token if scheme.lower() == "bearer" and token else None


def get_optional_user(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> User | None:
    token = _bearer_token(authorization)
    payload = decode_token(token) if token else None
    if payload is None:
        return None
    user = db.get(User, payload.user_id)
    if user is None or user.status != "ENABLED":
        return None
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == body.username)).scalar_one_or_none()
    if user is None or user.status != "ENABLED" or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = issue_token(user.id, user.username, user.role)
    return {
        "code": "OK",
        "data": {
            "accessToken": token,
            "tokenType": "bearer",
            "user": {"id": user.id, "username": user.username, "displayName": user.display_name, "role": user.role},
        },
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"code": "OK", "data": {"id": user.id, "username": user.username, "displayName": user.display_name, "role": user.role}}
