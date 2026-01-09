# LocumMap Chennai (MVP)

Uber-like locum marketplace for Chennai where clinics/hospitals can hire verified dentists & specialists for shifts with **real-time map tracking during the duty window** and **integrated payments (hold + payout placeholder)**.

## Monorepo layout

- `apps/api`: FastAPI + PostgreSQL + Alembic migrations + Socket.IO realtime
- `apps/clinic-web`: Next.js dashboard (map-first)
- `apps/doctor-mobile`: Expo React Native app (Android-first)
- `packages/shared`: shared TypeScript types + validation schemas

## Quick start (local dev)

### Prereqs

- Node 20+
- pnpm 10+
- Python 3.12+
- PostgreSQL 15+
- Google Maps API key (optional for MVP fallbacks)
- Razorpay keys (optional for MVP fallbacks)

### Install

```bash
corepack enable
pnpm -v
pnpm install
```

### Backend

```bash
cd apps/api
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:app --reload --port 8000
```

OpenAPI: `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/openapi.json`.

### Clinic web

```bash
pnpm --filter clinic-web dev
```

Web: `http://localhost:3000`

### Doctor mobile (Expo)

```bash
pnpm --filter doctor-mobile start
```

## Docker (recommended)

See `DEPLOYMENT.md` for `docker compose` local dev and a minimal VPS/Render/Fly.io guide.

## Demo

See `DEMO SCRIPT.md` for an end-to-end demo flow: post shift → candidates → booking → doctor accept → live tracking window → OTP check-in/out → payout eligibility → invoice.
