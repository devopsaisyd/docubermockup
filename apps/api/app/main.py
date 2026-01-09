from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import admin, assignments, auth, clinics, doctors, invoices, otp, payments, payouts, shifts
from app.realtime.socketio import sio

import socketio

socket_app = socketio.ASGIApp(sio, socketio_path="socket.io")

app = FastAPI(
    title="LocumMap Chennai API (MVP)",
    version="0.1.0",
    description="FastAPI backend for LocumMap Chennai (MVP).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(clinics.router, prefix="/clinics", tags=["clinics"])
app.include_router(doctors.router, prefix="/doctors", tags=["doctors"])
app.include_router(shifts.router, prefix="", tags=["shifts"])
app.include_router(assignments.router, prefix="", tags=["assignments"])
app.include_router(otp.router, prefix="", tags=["otp"])
app.include_router(payments.router, prefix="", tags=["payments"])
app.include_router(payouts.router, prefix="", tags=["payouts"])
app.include_router(invoices.router, prefix="", tags=["invoices"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

# Socket.IO endpoint (ASGI)
app.mount("/ws", socket_app)

