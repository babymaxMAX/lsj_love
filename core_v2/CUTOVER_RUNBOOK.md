# V2 Cutover Runbook (with rollback)

## Flags used

- `v2_api_public_enabled`
- `v2_bot_enabled`
- `v2_admin_enabled`
- `v2_payments_enabled`
- `v2_referrals_enabled`

Manage them via:
- `GET /api/v2/cutover/flags`
- `POST /api/v2/cutover/flags`

## Pre-cutover checklist

1. Run migrations:
   - `alembic -c core_v2/migrations/alembic.ini upgrade head`
2. Run migration bridge:
   - `python -m core_v2.tools.migrate_mongo_to_v2 --dry-run`
   - `python -m core_v2.tools.migrate_mongo_to_v2`
3. Validate readiness endpoint:
   - `GET /api/v2/cutover/readiness`
4. Verify critical API:
   - `/api/v2/auth/exchange`
   - `/api/v2/dating/search/{user_id}`
   - `/api/v2/payments/create`
   - `/api/v2/payments/webhook`
5. Confirm admin access:
   - `/v2-admin`
   - `/api/v2/admin/users`

## Cutover sequence

1. Freeze legacy critical writes (short window).
2. Run migration bridge delta.
3. Enable `v2_api_public_enabled=true`.
4. Enable `v2_bot_enabled=true`.
5. Enable payments/referrals/admin flags.
6. Watch logs/health for 30+ minutes.

## Rollback plan

1. Set all `v2_*_enabled=false`.
2. Route traffic back to legacy API/bot.
3. Keep v2 DB unchanged for post-mortem.
4. Re-open legacy writes.
5. Create incident note with failed checkpoint.
