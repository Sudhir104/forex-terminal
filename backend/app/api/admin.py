from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..schemas import WeightsIn
from ..services.auth import hash_password, require_admin
from ..services.weights import current_weights, set_weights

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/weights")
def get_weights(session: Session = Depends(get_db), _: User = Depends(require_admin)):
    return current_weights(session)


@router.put("/weights")
def put_weights(body: WeightsIn, session: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        return set_weights(session, body.weights)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/users")
def create_user(email: str, password: str, is_admin: bool = False, session: Session = Depends(get_db),
                _: User = Depends(require_admin)):
    email = email.lower().strip()
    if session.execute(select(User).where(User.email == email)).scalar_one_or_none():
        raise HTTPException(409, "User already exists")
    user = User(email=email, password_hash=hash_password(password), is_admin=is_admin)
    session.add(user)
    session.commit()
    return {"id": user.id, "email": user.email, "is_admin": user.is_admin}
