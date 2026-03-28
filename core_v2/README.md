# AI Kupidon v2 (parallel-run)

This module contains the new unified core for bot/backend/admin/payments/referrals.

## Local startup

1. Copy env:
   - `.env.v2.example` -> `.env.v2`
2. Start services:
   - `docker compose up -d postgres redis core_v2_api core_v2_worker core_v2_bot`
3. Run migrations:
   - `alembic -c core_v2/migrations/alembic.ini upgrade head`

## API checks

- `GET /health`
- `POST /api/v2/auth/token`
- `POST /api/v2/auth/exchange`
- `GET /api/v2/auth/me`
- `GET /api/v2/analytics/dashboard` (requires `X-Admin-Key`)
