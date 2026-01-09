## Deployment (LocumMap Chennai MVP)

This repo is designed for **Docker Compose local dev** and simple production deploy (VPS/Render/Fly.io). Secrets are **env vars** only.

### Environment variables

Backend (`apps/api/.env`):

- **DATABASE_URL**: `postgresql+psycopg://postgres:postgres@postgres:5432/locummap`
- **JWT_SECRET**: long random string
- **OTP_TTL_SECONDS**: `300`
- **ALLOW_DEV_OTP_ECHO**: `true` for local demo only
- **GOOGLE_MAPS_API_KEY**: optional; enables real Geocoding/Distance Matrix/Directions
- **RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET**: optional; enables Razorpay order creation
- **RAZORPAY_WEBHOOK_SECRET**: optional; enables webhook signature verification
- **SERVICE_AREA**: `chennai` (MVP only)

Clinic web (`apps/clinic-web/.env.local`):

- **NEXT_PUBLIC_API_BASE_URL**: `http://localhost:8000`
- **NEXT_PUBLIC_GOOGLE_MAPS_API_KEY**: Google Maps JS key

Doctor app (`apps/doctor-mobile/.env`):

- **EXPO_PUBLIC_API_BASE_URL**: `http://localhost:8000`
- **EXPO_PUBLIC_GOOGLE_MAPS_API_KEY**: key for Directions rendering / native maps

### Docker Compose (local dev)

Use `docker compose` to run Postgres, API, and clinic web.

```bash
docker compose up --build
```

Then:
- API: `http://localhost:8000/docs`
- Web: `http://localhost:3000`

### Production (simple VPS)

Recommended: Ubuntu 22.04+ VPS.

1) Install Docker + Docker Compose plugin
2) Create a `.env` file for API (do **not** commit it)
3) Configure a reverse proxy (Caddy/Nginx) with TLS
4) Run:

```bash
docker compose -f docker-compose.yml up -d --build
```

### TLS / security notes

- Terminate TLS at reverse proxy.
- Set `JWT_SECRET` to a strong random value.
- Keep `ALLOW_DEV_OTP_ECHO=false` in production.
- Razorpay webhook verification must be enabled in production (`RAZORPAY_WEBHOOK_SECRET`).

