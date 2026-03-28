from pathlib import Path

from datetime import timedelta

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_v2.backend.db import get_db
from core_v2.backend.models import (
    AdminUser,
    Match,
    MailingCampaign,
    MailingLog,
    Payment,
    Plan,
    Profile,
    ReferralReward,
    Report,
    User,
)
from core_v2.backend.schemas import (
    AuthCreateTokenRequest,
    AuthExchangeRequest,
    AuthExchangeResponse,
    BroadcastRequest,
    HealthResponse,
    PaymentCreateRequest,
    PaymentWebhookRequest,
    ProfileUpsertRequest,
    ReportCreateRequest,
    ReferralRegisterRequest,
    SwipeRequest,
)
from core_v2.backend.services import (
    apply_swipe,
    collect_dashboard_metrics,
    create_report,
    create_auth_token,
    create_campaign,
    create_payment,
    exchange_auth_token,
    get_or_create_user_by_telegram,
    handle_payment_webhook,
    log_ai_request,
    moderation_queue,
    queue_campaign_for_users,
    set_feature_flag,
    referral_overview,
    register_referral,
    revoke_session,
    resolve_session_user,
    search_profiles,
    search_users_for_admin,
    get_feature_flags,
    upsert_profile,
)
from core_v2.backend.settings import V2Settings


settings = V2Settings()
app = FastAPI(title="AI Kupidon v2 API", version="0.1.0")
ADMIN_PANEL_PATH = Path(__file__).resolve().parents[1] / "admin" / "panel.html"


async def require_admin(
    x_admin_key: str | None = Header(default=None),
) -> None:
    if not settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin key is not configured")
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _must_be_valid_role(role: str) -> None:
    if role not in {"moderator", "admin"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.get("/v2-admin", response_class=HTMLResponse)
async def admin_panel() -> str:
    if not ADMIN_PANEL_PATH.exists():
        return "<h1>Admin panel template not found</h1>"
    return ADMIN_PANEL_PATH.read_text(encoding="utf-8")


@app.post("/api/v2/auth/token")
async def auth_token_create(payload: AuthCreateTokenRequest, db: AsyncSession = Depends(get_db)) -> dict:
    token = await create_auth_token(db, payload.telegram_id)
    return {"token": token, "expires_in_seconds": int(timedelta(minutes=10).total_seconds())}


@app.post("/api/v2/auth/exchange", response_model=AuthExchangeResponse)
async def auth_exchange(payload: AuthExchangeRequest, response: Response, db: AsyncSession = Depends(get_db)) -> AuthExchangeResponse:
    user, session_key = await exchange_auth_token(db, payload.token)
    response.set_cookie(
        key="ak_v2_session",
        value=session_key,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(timedelta(days=30).total_seconds()),
    )
    return AuthExchangeResponse(ok=True, telegram_id=user.telegram_id)


@app.get("/api/v2/auth/me")
async def auth_me(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    session_key = request.cookies.get("ak_v2_session")
    user = await resolve_session_user(db, session_key)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return {"user_id": user.id, "telegram_id": user.telegram_id, "is_premium": user.is_premium}


@app.post("/api/v2/auth/logout")
async def auth_logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    session_key = request.cookies.get("ak_v2_session")
    revoked = await revoke_session(db, session_key)
    response.delete_cookie("ak_v2_session")
    return {"ok": True, "revoked": revoked}


@app.post("/api/v2/dating/onboarding")
async def onboarding(
    payload: AuthCreateTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await get_or_create_user_by_telegram(db, payload.telegram_id)
    return {"ok": True, "user_id": user.id, "telegram_id": user.telegram_id}


@app.put("/api/v2/dating/profiles/{user_id}")
async def profile_upsert(user_id: str, payload: ProfileUpsertRequest, db: AsyncSession = Depends(get_db)) -> dict:
    profile = await upsert_profile(db, user_id, payload)
    return {"ok": True, "profile_id": profile.id, "moderation_status": profile.moderation_status}


@app.get("/api/v2/dating/search/{user_id}")
async def dating_search(user_id: str, limit: int = Query(default=20, ge=1, le=100), db: AsyncSession = Depends(get_db)) -> dict:
    items = await search_profiles(db, current_user_id=user_id, limit=limit)
    return {"items": [{"user_id": p.user_id, "display_name": p.display_name, "age": p.age, "city": p.city} for p in items]}


@app.post("/api/v2/dating/swipes")
async def dating_swipe(payload: SwipeRequest, db: AsyncSession = Depends(get_db)) -> dict:
    if payload.action not in {"like", "dislike", "report"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")
    return await apply_swipe(db, payload)


@app.get("/api/v2/dating/matches/{user_id}")
async def dating_matches(user_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    rows = list(await db.scalars(select(Match).where((Match.user_a_id == user_id) | (Match.user_b_id == user_id))))
    return {"items": [{"match_id": m.id, "user_a_id": m.user_a_id, "user_b_id": m.user_b_id} for m in rows]}


@app.post("/api/v2/dating/reports")
async def dating_report(payload: ReportCreateRequest, db: AsyncSession = Depends(get_db)) -> dict:
    report = await create_report(db, payload)
    return {"ok": True, "report_id": report.id, "status": report.status}


@app.post("/api/v2/payments/create")
async def payment_create(payload: PaymentCreateRequest, db: AsyncSession = Depends(get_db)) -> dict:
    payment = await create_payment(db, payload)
    return {
        "payment_id": payment.id,
        "status": payment.status,
        "provider": payment.provider,
        "amount": payment.amount,
        "currency": payment.currency,
    }


@app.post("/api/v2/payments/webhook")
async def payment_webhook(payload: PaymentWebhookRequest, db: AsyncSession = Depends(get_db)) -> dict:
    payment = await handle_payment_webhook(db, payload)
    return {"ok": True, "payment_id": payment.id, "status": payment.status}


@app.get("/api/v2/payments/plans")
async def payment_plans(db: AsyncSession = Depends(get_db)) -> dict:
    rows = list(await db.scalars(select(Plan).where(Plan.is_active.is_(True))))
    return {
        "items": [
            {
                "id": p.id,
                "code": p.code,
                "title": p.title,
                "price": p.price,
                "currency": p.currency,
                "duration_days": p.duration_days,
            }
            for p in rows
        ]
    }


@app.get("/api/v2/payments/{payment_id}")
async def payment_get(payment_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    payment = await db.scalar(select(Payment).where(Payment.id == payment_id))
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return {
        "id": payment.id,
        "user_id": payment.user_id,
        "provider": payment.provider,
        "status": payment.status,
        "amount": payment.amount,
        "currency": payment.currency,
    }


@app.post("/api/v2/referrals/register")
async def referral_register(payload: ReferralRegisterRequest, db: AsyncSession = Depends(get_db)) -> dict:
    return await register_referral(db, payload)


@app.get("/api/v2/referrals/{user_id}")
async def referral_get(user_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    return await referral_overview(db, user_id)


@app.post("/api/v2/admin/broadcast", dependencies=[Depends(require_admin)])
async def admin_broadcast(payload: BroadcastRequest, db: AsyncSession = Depends(get_db)) -> dict:
    campaign = await create_campaign(db, payload)
    queued = await queue_campaign_for_users(db, campaign.id)
    return {"ok": True, "campaign_id": campaign.id, "queued": queued}


@app.get("/api/v2/admin/moderation/queue", dependencies=[Depends(require_admin)])
async def admin_moderation_queue(db: AsyncSession = Depends(get_db)) -> dict:
    return await moderation_queue(db)


@app.get("/api/v2/admin/users", dependencies=[Depends(require_admin)])
async def admin_users(q: str | None = None, db: AsyncSession = Depends(get_db)) -> dict:
    users = await search_users_for_admin(db, q=q)
    return {"items": [{"id": u.id, "telegram_id": u.telegram_id, "username": u.username, "role": u.role} for u in users]}


@app.post("/api/v2/admin/rbac/grant", dependencies=[Depends(require_admin)])
async def admin_rbac_grant(user_id: str, role: str, db: AsyncSession = Depends(get_db)) -> dict:
    _must_be_valid_role(role)
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    mapping = await db.scalar(select(AdminUser).where(AdminUser.user_id == user_id))
    if mapping is None:
        mapping = AdminUser(user_id=user_id, admin_role=role, is_enabled=True)
        db.add(mapping)
    else:
        mapping.admin_role = role
        mapping.is_enabled = True
    user.role = role
    await db.commit()
    return {"ok": True, "user_id": user_id, "role": role}


@app.get("/api/v2/admin/rbac/list", dependencies=[Depends(require_admin)])
async def admin_rbac_list(db: AsyncSession = Depends(get_db)) -> dict:
    rows = list(await db.scalars(select(AdminUser)))
    return {
        "items": [
            {"id": r.id, "user_id": r.user_id, "admin_role": r.admin_role, "is_enabled": r.is_enabled} for r in rows
        ]
    }


@app.post("/api/v2/admin/users/{user_id}/ban", dependencies=[Depends(require_admin)])
async def admin_ban_user(user_id: str, ban: bool = True, db: AsyncSession = Depends(get_db)) -> dict:
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = not ban
    await db.commit()
    return {"ok": True, "user_id": user_id, "is_active": user.is_active}


@app.post("/api/v2/admin/profiles/{profile_id}/moderate", dependencies=[Depends(require_admin)])
async def admin_moderate_profile(profile_id: str, status_value: str, db: AsyncSession = Depends(get_db)) -> dict:
    if status_value not in {"approved", "rejected", "pending"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid moderation status")
    profile = await db.scalar(select(Profile).where(Profile.id == profile_id))
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    profile.moderation_status = status_value
    await db.commit()
    return {"ok": True, "profile_id": profile_id, "moderation_status": profile.moderation_status}


@app.get("/api/v2/admin/payments", dependencies=[Depends(require_admin)])
async def admin_payments(limit: int = Query(default=100, ge=1, le=1000), db: AsyncSession = Depends(get_db)) -> dict:
    rows = list(await db.scalars(select(Payment).limit(limit)))
    return {
        "items": [
            {
                "id": p.id,
                "user_id": p.user_id,
                "provider": p.provider,
                "status": p.status,
                "amount": p.amount,
                "currency": p.currency,
            }
            for p in rows
        ]
    }


@app.get("/api/v2/admin/referrals", dependencies=[Depends(require_admin)])
async def admin_referrals(limit: int = Query(default=100, ge=1, le=1000), db: AsyncSession = Depends(get_db)) -> dict:
    rows = list(await db.scalars(select(ReferralReward).limit(limit)))
    return {
        "items": [
            {
                "id": r.id,
                "referrer_user_id": r.referrer_user_id,
                "invited_user_id": r.invited_user_id,
                "trigger_type": r.trigger_type,
                "reward_amount": r.reward_amount,
                "reward_status": r.reward_status,
            }
            for r in rows
        ]
    }


@app.post("/api/v2/admin/plans/seed", dependencies=[Depends(require_admin)])
async def admin_seed_plans(db: AsyncSession = Depends(get_db)) -> dict:
    existing = list(await db.scalars(select(Plan)))
    if existing:
        return {"ok": True, "created": 0, "message": "Plans already exist"}
    rows = [
        Plan(code="premium_month", title="Premium 30d", price=299.0, currency="RUB", duration_days=30, is_active=True),
        Plan(code="vip_month", title="VIP 30d", price=799.0, currency="RUB", duration_days=30, is_active=True),
    ]
    db.add_all(rows)
    await db.commit()
    return {"ok": True, "created": len(rows)}


@app.post("/api/v2/admin/reports/{report_id}/resolve", dependencies=[Depends(require_admin)])
async def admin_resolve_report(report_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    report = await db.scalar(select(Report).where(Report.id == report_id))
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    report.status = "resolved"
    await db.commit()
    return {"ok": True}


@app.get("/api/v2/analytics/dashboard", dependencies=[Depends(require_admin)])
async def analytics_dashboard(db: AsyncSession = Depends(get_db)) -> dict:
    return await collect_dashboard_metrics(db)


@app.get("/api/v2/analytics/mailings", dependencies=[Depends(require_admin)])
async def analytics_mailings(db: AsyncSession = Depends(get_db)) -> dict:
    campaigns = list(await db.scalars(select(MailingCampaign)))
    logs = list(await db.scalars(select(MailingLog)))
    delivered = len([log for log in logs if log.delivery_status == "sent"])
    queued = len([log for log in logs if log.delivery_status == "queued"])
    failed = len([log for log in logs if log.delivery_status == "failed"])
    return {
        "campaigns_total": len(campaigns),
        "messages_total": len(logs),
        "messages_queued": queued,
        "messages_sent": delivered,
        "messages_failed": failed,
    }


@app.post("/api/v2/analytics/ai/request")
async def analytics_ai_request(user_id: str | None, feature: str, payload: dict, db: AsyncSession = Depends(get_db)) -> dict:
    row = await log_ai_request(db, user_id=user_id, feature=feature, payload=payload)
    return {"ok": True, "request_id": row.id, "status": row.status}


@app.get("/api/v2/cutover/readiness", dependencies=[Depends(require_admin)])
async def cutover_readiness(db: AsyncSession = Depends(get_db)) -> dict:
    users_count = await db.scalar(select(func.count()).select_from(User))
    profiles_count = await db.scalar(select(func.count()).select_from(Profile))
    reports_open = await db.scalar(select(func.count()).select_from(Report))
    return {
        "allow_legacy_fallback": settings.allow_legacy_fallback,
        "users_count": users_count or 0,
        "profiles_count": profiles_count or 0,
        "reports_count": reports_open or 0,
    }


@app.get("/api/v2/cutover/flags", dependencies=[Depends(require_admin)])
async def cutover_flags_get(db: AsyncSession = Depends(get_db)) -> dict:
    rows = await get_feature_flags(db)
    return {"items": [{"key": x.key, "value": x.value, "description": x.description} for x in rows]}


@app.post("/api/v2/cutover/flags", dependencies=[Depends(require_admin)])
async def cutover_flags_set(
    key: str,
    value: bool,
    description: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await set_feature_flag(db, key=key, value=value, description=description)
    return {"ok": True, "key": row.key, "value": row.value}
