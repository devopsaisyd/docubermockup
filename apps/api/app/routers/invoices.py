from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.models.clinic import ClinicProfile
from app.models.doctor import DoctorProfile
from app.models.enums import Role
from app.models.shift import Shift
from app.models.user import User


router = APIRouter()


@router.get("/invoices/{shift_id}", response_class=HTMLResponse)
def invoice(
    shift_id: uuid.UUID,
    user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff, Role.doctor, Role.admin)),
    db: Session = Depends(get_db),
):
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    if user.role in (Role.clinic_admin, Role.clinic_staff) and shift.clinic_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your invoice")
    if user.role == Role.doctor and (not shift.assignment or shift.assignment.doctor_user_id != user.id):
        raise HTTPException(status_code=403, detail="Not your invoice")

    clinic = db.get(ClinicProfile, shift.clinic_profile_id)
    doctor_name = "-"
    if shift.assignment:
        doc = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == shift.assignment.doctor_user_id))
        doctor_name = doc.full_name if doc else "-"

    html = f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Invoice - {shift.id}</title>
    <style>
      body {{ font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; padding: 24px; color: #0b1220; }}
      .card {{ max-width: 760px; margin: 0 auto; border: 1px solid #e5e7eb; border-radius: 16px; padding: 20px; }}
      .row {{ display: flex; justify-content: space-between; gap: 16px; }}
      .muted {{ color: #64748b; }}
      .big {{ font-size: 28px; font-weight: 700; }}
      .chip {{ display:inline-block; padding: 6px 10px; border-radius: 999px; background: #0ea5e9; color: white; font-weight: 600; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
      td {{ padding: 10px 0; border-bottom: 1px solid #eef2f7; }}
      .total {{ font-weight: 800; }}
    </style>
  </head>
  <body>
    <div class="card">
      <div class="row">
        <div>
          <div class="muted">LocumMap Chennai</div>
          <div class="big">Invoice</div>
          <div class="muted">Shift ID: {shift.id}</div>
        </div>
        <div style="text-align:right">
          <div class="chip">{shift.status.value.upper()}</div>
          <div class="muted" style="margin-top:8px">Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>
        </div>
      </div>

      <table>
        <tr><td class="muted">Clinic</td><td>{clinic.name if clinic else "-"}</td></tr>
        <tr><td class="muted">Address</td><td>{shift.address}</td></tr>
        <tr><td class="muted">Doctor</td><td>{doctor_name}</td></tr>
        <tr><td class="muted">Specialty</td><td>{shift.specialty.value}</td></tr>
        <tr><td class="muted">Start</td><td>{shift.start_time.isoformat()}</td></tr>
        <tr><td class="muted">End</td><td>{shift.end_time.isoformat()}</td></tr>
        <tr><td class="muted">Amount</td><td class="total">₹ {shift.pay_amount_inr}</td></tr>
      </table>
      <p class="muted">Tip: Use your browser “Print” to save as PDF.</p>
    </div>
  </body>
</html>
"""
    return HTMLResponse(content=html)

