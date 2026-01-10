from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.deps import get_clinic_owner_id, require_role
from app.db.session import get_db
from app.models.chat import ChatMessage
from app.models.doctor import DoctorProfile
from app.models.enums import AssignmentStatus, Role, ShiftStatus, VerificationStatus
from app.models.shift import Shift
from app.models.shift import ShiftAssignment
from app.models.user import User
from app.schemas.chat import ChatMessageOut, ChatSendIn, OfferRespondIn
from app.services.audit import record_event
from app.realtime.socketio import emit_shift_update
from app.services.shift_state import now_utc
from app.services.push_notifications import notify_user


router = APIRouter()


def _can_access_shift_chat(db: Session, *, user: User, shift: Shift) -> bool:
    if user.role in (Role.clinic_admin, Role.clinic_staff):
        owner_id = get_clinic_owner_id(user, db)
        return shift.clinic_user_id == owner_id
    if user.role == Role.doctor:
        if shift.assignment and shift.assignment.doctor_user_id == user.id:
            return True
        # allow pre-book negotiation only if verified + matching specialty
        doc = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == user.id))
        return bool(doc and doc.verification_status == VerificationStatus.approved and doc.specialty == shift.specialty)
    return user.role == Role.admin


@router.get("/shifts/{shift_id}/chat", response_model=list[ChatMessageOut])
def list_chat(
    shift_id: uuid.UUID,
    user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff, Role.doctor, Role.admin)),
    db: Session = Depends(get_db),
):
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    if not _can_access_shift_chat(db, user=user, shift=shift):
        raise HTTPException(status_code=403, detail="Not allowed")
    msgs = db.scalars(select(ChatMessage).where(ChatMessage.shift_id == shift.id).order_by(ChatMessage.created_at.asc())).all()
    return list(msgs)


@router.post("/shifts/{shift_id}/chat", response_model=ChatMessageOut)
async def send_message(
    shift_id: uuid.UUID,
    payload: ChatSendIn,
    user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff, Role.doctor)),
    db: Session = Depends(get_db),
):
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    if not _can_access_shift_chat(db, user=user, shift=shift):
        raise HTTPException(status_code=403, detail="Not allowed")

    kind = payload.kind if payload.kind in ("text", "offer") else "text"
    if kind == "offer" and payload.offer_amount_inr is None:
        raise HTTPException(status_code=400, detail="offer_amount_inr required for offer")

    msg = ChatMessage(
        shift_id=shift.id,
        assignment_id=shift.assignment.id if shift.assignment else None,
        sender_user_id=user.id,
        sender_role=user.role.value,
        kind=kind,
        message=payload.message if kind == "text" else None,
        offer_amount_inr=payload.offer_amount_inr if kind == "offer" else None,
        offer_status="proposed" if kind == "offer" else None,
    )
    db.add(msg)
    record_event(
        db,
        shift_id=shift.id,
        assignment_id=shift.assignment.id if shift.assignment else None,
        actor_user_id=user.id,
        event_type="chat_message",
        payload={"kind": kind},
    )
    db.commit()
    db.refresh(msg)

    await emit_shift_update(
        shift.id,
        {
            "shift_id": str(shift.id),
            "type": "chat_message",
            "message": {
                "id": str(msg.id),
                "kind": msg.kind,
                "sender_role": msg.sender_role,
                "message": msg.message,
                "offer_amount_inr": msg.offer_amount_inr,
                "offer_status": msg.offer_status,
                "created_at": msg.created_at.isoformat(),
            },
        },
    )
    # Notify the counterparty (best-effort)
    try:
        if user.role in (Role.clinic_admin, Role.clinic_staff) and shift.assignment:
            await notify_user(db, shift.assignment.doctor_user_id, title="New message", body="Clinic sent you a message.", data={"shift_id": str(shift.id)})
        if user.role == Role.doctor:
            await notify_user(db, shift.clinic_user_id, title="New message", body="Doctor sent you a message.", data={"shift_id": str(shift.id)})
    except Exception:
        pass
    return msg


@router.post("/chat/{message_id}/offer/respond", response_model=ChatMessageOut)
async def respond_offer(
    message_id: uuid.UUID,
    payload: OfferRespondIn,
    user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff, Role.doctor)),
    db: Session = Depends(get_db),
):
    msg = db.get(ChatMessage, message_id)
    if not msg or msg.kind != "offer":
        raise HTTPException(status_code=404, detail="Offer not found")
    shift = db.get(Shift, msg.shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    if user.role in (Role.clinic_admin, Role.clinic_staff):
        owner_id = get_clinic_owner_id(user, db)
        if shift.clinic_user_id != owner_id:
            raise HTTPException(status_code=403, detail="Not allowed")
    if user.role == Role.doctor:
        # must be eligible to negotiate this specialty (or assigned)
        if not _can_access_shift_chat(db, user=user, shift=shift):
            raise HTTPException(status_code=403, detail="Not allowed")

    action = payload.action.lower()
    if action not in ("accept", "reject"):
        raise HTTPException(status_code=400, detail="action must be accept|reject")

    msg.offer_status = "accepted" if action == "accept" else "rejected"

    # If accepted, update shift pay amount (negotiated price)
    if action == "accept" and msg.offer_amount_inr:
        shift.pay_amount_inr = int(msg.offer_amount_inr)
        record_event(
            db,
            shift_id=shift.id,
            assignment_id=shift.assignment.id if shift.assignment else None,
            actor_user_id=user.id,
            event_type="offer_accepted",
            payload={"amount_inr": shift.pay_amount_inr},
        )

        # If clinic accepts an offer on a posted shift, auto-book the offering doctor.
        if user.role in (Role.clinic_admin, Role.clinic_staff) and shift.status == ShiftStatus.posted and not shift.assignment:
            doc = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == msg.sender_user_id))
            if not doc or doc.verification_status != VerificationStatus.approved:
                raise HTTPException(status_code=400, detail="Doctor not available/verified")
            if doc.specialty != shift.specialty:
                raise HTTPException(status_code=400, detail="Specialty mismatch")
            shift.status = ShiftStatus.booked
            assignment = ShiftAssignment(
                shift_id=shift.id,
                doctor_user_id=msg.sender_user_id,
                doctor_profile_id=doc.id,
                status=AssignmentStatus.booked,
                accepted_at=now_utc(),
            )
            db.add(assignment)
            db.flush()
            record_event(
                db,
                shift_id=shift.id,
                assignment_id=assignment.id,
                actor_user_id=user.id,
                event_type="shift_booked_from_offer",
                payload={"doctor_user_id": str(msg.sender_user_id), "amount_inr": shift.pay_amount_inr},
            )

    db.commit()
    db.refresh(msg)

    await emit_shift_update(
        shift.id,
        {
            "shift_id": str(shift.id),
            "type": "offer_update",
            "message_id": str(msg.id),
            "offer_status": msg.offer_status,
            "offer_amount_inr": msg.offer_amount_inr,
        },
    )
    # Notify doctor if clinic accepted/rejected offer
    try:
        if user.role in (Role.clinic_admin, Role.clinic_staff):
            await notify_user(
                db,
                msg.sender_user_id,
                title="Offer update",
                body=f"Your offer was {msg.offer_status}.",
                data={"shift_id": str(shift.id)},
            )
    except Exception:
        pass
    return msg

