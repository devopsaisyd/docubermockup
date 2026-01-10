from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.models.enums import Role
from app.models.push import PushToken
from app.models.user import User
from app.schemas.push import RegisterPushTokenIn, RegisterPushTokenOut


router = APIRouter()


@router.post("/devices/push-token", response_model=RegisterPushTokenOut)
def register_push_token(
    payload: RegisterPushTokenIn,
    user: User = Depends(require_role(Role.doctor, Role.clinic_admin, Role.clinic_staff)),
    db: Session = Depends(get_db),
):
    existing = db.scalar(select(PushToken).where(PushToken.token == payload.token))
    if existing:
        existing.user_id = user.id
        existing.platform = payload.platform
    else:
        db.add(PushToken(user_id=user.id, token=payload.token, platform=payload.platform))
    db.commit()
    return RegisterPushTokenOut()

