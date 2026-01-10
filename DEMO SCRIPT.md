## LocumMap Chennai (MVP) — Demo Script

This script walks through a full **clinic → doctor → negotiation → pay (UPI) → live tracking → OTP check-in/out → payout → invoices** demo.

### 0) Start services (local)

Backend:

```bash
cd apps/api
cp .env.example .env
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:app --reload --port 8000
```

Clinic web:

```bash
cp apps/clinic-web/.env.local.example apps/clinic-web/.env.local
pnpm --filter clinic-web dev
```

Doctor app:

```bash
cp apps/doctor-mobile/.env.example apps/doctor-mobile/.env
pnpm --filter doctor-mobile start
```

### 1) Clinic sign-in + onboarding

1. Open `http://localhost:3000/login`
2. Use demo clinic phone: `9000000001`
3. Click **Get OTP** (OTP is echoed in UI when `ALLOW_DEV_OTP_ECHO=true`)
4. Verify OTP → go to **Shifts**
5. If prompted, fill **Clinic profile** (Chennai-only rule enforced)

### 2) Post a shift

1. In **Shifts**, fill:
   - Specialty: `Dentist (General)`
   - Start/End: any future time (within next 1–2 days)
   - Pay: `₹3500`
   - Address: Chennai address (geocode optional)
2. Click **Post**

### 3) Review candidates + book

1. Click the shift card → **Shift detail**
2. Scroll to **Candidates** (ranked by ETA)
3. Click **Book** on a candidate

You should now see:
- status: `BOOKED`
- a live map with Clinic marker `C`

### 3.5) Broadcast bidding + negotiation (advanced)

1. Doctor can send a **counter offer** in chat (`Offer: ₹xxxx`)
2. Clinic can **Accept** the offer → this updates shift pay and (for posted shifts) can auto-book the offering doctor.

### 4) Doctor sign-in and accept (Doctor app)

1. In Expo app:
   - Use doctor phone from seed: `9100000100`
   - Request OTP → verify
2. If needed, fill profile (specialty must match)
3. In **Available shifts**, tap **Accept** on the newly posted shift

### 5) Live tracking window

Tracking is only allowed **T-30 minutes before start** until **shift end** or **checkout**, whichever first.

In the Doctor app:
- Tap **Set En Route**
- Tap **Ping now**

In clinic web:
- Shift map should update with Doctor marker `D`
- Timeline should append `location_ping` events

### 6) OTP check-in (geofence validated)

1. Clinic web → Shift detail → click **Create check-in OTP**
2. Read OTP to doctor (demo shows OTP card)
3. Doctor app → enter OTP → tap **Check-in**

Rules:
- Check-in is allowed only if doctor is within **150m** of clinic OR clinic created OTP with `allow_remote=true` (override).

### 7) OTP check-out

1. Clinic web → **Create check-out OTP**
2. Doctor enters OTP → **Check-out**
3. Shift becomes `COMPLETED` and backend emits `payout_eligible`

### 8) Payment + payout (MVP)

Payment (UPI via Razorpay Checkout):
- Clinic web → Shift detail → **Create payment order** → Razorpay checkout (UPI/Card/Netbanking)
- In demo mode (no keys), payment confirm is simulated.

Payout:
- For MVP, payout is admin-driven:

```bash
# Example: mark payout paid (admin role)
# You can obtain admin token by OTP login with phone 9999999999 (role=admin).
```

### 9) Invoice

Clinic web → **Invoice (HTML)** button → print/save as PDF.

### 10) Clinic admin screens

- Clinic web → `/admin`
  - **Staff & roles**: invite/remove staff
  - **Billing & invoices**: list payments + open invoices

### 11) Doctor earnings

Doctor app → **Earnings**:
- payouts list
- invoice list (HTML invoices printable to PDF)

