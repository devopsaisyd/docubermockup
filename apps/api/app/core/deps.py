from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import Role
from app.models.clinic_staff import ClinicStaffMember
from app.models.user import User


bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = decode_access_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.get(User, uuid.UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found/inactive")
    return user


def require_role(*roles: Role):
    def _inner(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _inner


def get_clinic_owner_id(user: User, db: Session) -> "uuid.UUID":
    """
    Clinic staff accounts are linked to a clinic admin via ClinicStaffMember.
    This returns the clinic owner (admin) user_id for permission checks and data access.
    """
    import uuid as _uuid
    from sqlalchemy import select as _select

    if user.role != Role.clinic_staff:
        return user.id
    row = db.scalar(_select(ClinicStaffMember).where(ClinicStaffMember.staff_user_id == user.id))
    if not row:
        # orphan staff account
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinic staff not linked to a clinic")
    return _uuid.UUID(str(row.clinic_user_id))

