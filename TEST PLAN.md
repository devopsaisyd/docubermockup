## Test Plan (MVP)

### Automated tests

Backend tests live in `apps/api/app/tests`:

- **Unit**: shift status machine transition guards
- **Integration**: booking → location ping → OTP check-in verify

Run:

```bash
cd apps/api
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

### Manual test checklist

#### Auth (OTP)
- Clinic OTP request returns `dev_otp` only when `ALLOW_DEV_OTP_ECHO=true`
- OTP verify returns JWT; API rejects invalid/expired OTP
- Role mismatch for same phone is blocked

#### Chennai boundary
- Clinic profile location outside Chennai is rejected
- Shift post outside Chennai is rejected

#### Shift state machine
- Draft/Posted → Booked only once (second booking should fail)
- Booked → En Route via doctor status update
- Booked/En Route → Checked-in only via OTP verify
- Checked-in → Completed only via OTP verify
- Completed → Paid only via admin payout mark-paid

#### Geofence / OTP
- Verify check-in fails if no location ping exists
- Verify check-in fails if >150m and no override
- Verify succeeds if within 150m
- Verify succeeds if clinic created OTP with `allow_remote=true`

#### Real-time tracking privacy
- Location pings rejected outside duty window (T-30 to end/checkout)
- Clinic receives live updates only after joining assignment room

#### Payments (MVP)
- Create order works without Razorpay keys (demo order id)
- Webhook signature verification enforced when `RAZORPAY_WEBHOOK_SECRET` set

#### Doctor app (Android)
- Foreground location permission requested
- Background tracking starts on Live Shift accept and stops on End
- “Ping now” works and updates clinic map within duty window

