import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_v2.backend.models import (
    AIRequest,
    AuditLog,
    FeatureFlag,
    AuthToken,
    Match,
    MailingCampaign,
    MailingLog,
    Payment,
    PaymentTransaction,
    Plan,
    Profile,
    ReferralReward,
    Report,
    Session,
    Subscription,
    Swipe,
    User,
)
from core_v2.backend.schemas import (
    BroadcastRequest,
    PaymentCreateRequest,
    PaymentWebhookRequest,
    ProfileUpsertRequest,
    ReportCreateRequest,
    ReferralRegisterRequest,
    SwipeRequest,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def get_or_create_user_by_telegram(session: AsyncSession, telegram_id: int) -> User:
    existing = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if existing:
        return existing
    user = User(telegram_id=telegram_id, referral_code=f"ref_{telegram_id}")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_auth_token(session: AsyncSession, telegram_id: int) -> str:
    user = await get_or_create_user_by_telegram(session, telegram_id)
    token = secrets.token_urlsafe(32)
    row = AuthToken(
        token=token,
        user_id=user.id,
        expires_at=now_utc() + timedelta(minutes=10),
        used=False,
    )
    session.add(row)
    await session.commit()
    return token


async def exchange_auth_token(session: AsyncSession, token: str) -> tuple[User, str]:
    row = await session.scalar(select(AuthToken).where(and_(AuthToken.token == token, AuthToken.used.is_(False))))
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token not found or already used")

    expires_at = _ensure_utc(row.expires_at)
    if expires_at and now_utc() > expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")

    user = await session.scalar(select(User).where(User.id == row.user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")

    row.used = True
    session_key = secrets.token_urlsafe(48)
    session_row = Session(
        session_key=session_key,
        user_id=user.id,
        expires_at=now_utc() + timedelta(days=30),
    )
    session.add(session_row)
    session.add(AuditLog(actor_user_id=user.id, action="auth.exchange", entity_type="session", entity_id=session_row.id))
    await session.commit()
    return user, session_key


async def resolve_session_user(session: AsyncSession, session_key: str | None) -> User | None:
    if not session_key:
        return None
    row = await session.scalar(
        select(Session).where(
            and_(
                Session.session_key == session_key,
                Session.revoked_at.is_(None),
                Session.expires_at > now_utc(),
            )
        )
    )
    if not row:
        return None
    return await session.scalar(select(User).where(User.id == row.user_id))


async def revoke_session(session: AsyncSession, session_key: str | None) -> bool:
    if not session_key:
        return False
    row = await session.scalar(select(Session).where(Session.session_key == session_key))
    if not row:
        return False
    row.revoked_at = now_utc()
    await session.commit()
    return True


async def upsert_profile(session: AsyncSession, user_id: str, payload: ProfileUpsertRequest) -> Profile:
    profile = await session.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is None:
        profile = Profile(user_id=user_id, **payload.model_dump())
        session.add(profile)
    else:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
        profile.moderation_status = "pending"
    session.add(AuditLog(actor_user_id=user_id, action="profile.upsert", entity_type="profile", entity_id=profile.id))
    await session.commit()
    await session.refresh(profile)
    return profile


async def search_profiles(session: AsyncSession, current_user_id: str, limit: int = 20) -> list[Profile]:
    viewed_subquery = select(Swipe.to_user_id).where(Swipe.from_user_id == current_user_id)
    query = (
        select(Profile)
        .where(
            and_(
                Profile.user_id != current_user_id,
                Profile.visibility == "public",
                Profile.moderation_status == "approved",
                Profile.user_id.not_in(viewed_subquery),
            )
        )
        .limit(limit)
    )
    rows = await session.scalars(query)
    return list(rows)


def _normalize_pair(user_a_id: str, user_b_id: str) -> tuple[str, str]:
    return (user_a_id, user_b_id) if user_a_id < user_b_id else (user_b_id, user_a_id)


async def apply_swipe(session: AsyncSession, payload: SwipeRequest) -> dict:
    swipe = await session.scalar(
        select(Swipe).where(and_(Swipe.from_user_id == payload.from_user_id, Swipe.to_user_id == payload.to_user_id))
    )
    if swipe is None:
        swipe = Swipe(from_user_id=payload.from_user_id, to_user_id=payload.to_user_id, action=payload.action)
        session.add(swipe)
    else:
        swipe.action = payload.action

    match_created = False
    if payload.action == "like":
        reverse_like = await session.scalar(
            select(Swipe).where(
                and_(
                    Swipe.from_user_id == payload.to_user_id,
                    Swipe.to_user_id == payload.from_user_id,
                    Swipe.action == "like",
                )
            )
        )
        if reverse_like:
            user_a_id, user_b_id = _normalize_pair(payload.from_user_id, payload.to_user_id)
            existing_match = await session.scalar(
                select(Match).where(and_(Match.user_a_id == user_a_id, Match.user_b_id == user_b_id))
            )
            if existing_match is None:
                session.add(Match(user_a_id=user_a_id, user_b_id=user_b_id, status="active"))
                match_created = True

    if payload.action == "report":
        session.add(
            Report(
                reporter_user_id=payload.from_user_id,
                target_user_id=payload.to_user_id,
                reason="swipe_report",
                details="Created from swipe flow",
            )
        )

    await session.commit()
    return {"ok": True, "match_created": match_created}


async def create_report(session: AsyncSession, payload: ReportCreateRequest) -> Report:
    report = Report(
        reporter_user_id=payload.reporter_user_id,
        target_user_id=payload.target_user_id,
        reason=payload.reason,
        details=payload.details,
        status="open",
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


async def create_payment(session: AsyncSession, payload: PaymentCreateRequest) -> Payment:
    existing = await session.scalar(select(Payment).where(Payment.idempotency_key == payload.idempotency_key))
    if existing:
        return existing

    plan = await session.scalar(select(Plan).where(and_(Plan.code == payload.plan_code, Plan.is_active.is_(True))))
    if not plan:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan not found")

    payment = Payment(
        user_id=payload.user_id,
        plan_id=plan.id,
        provider=payload.provider,
        amount=plan.price,
        currency=plan.currency,
        status="created",
        idempotency_key=payload.idempotency_key,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def handle_payment_webhook(session: AsyncSession, payload: PaymentWebhookRequest) -> Payment:
    payment = await session.scalar(select(Payment).where(Payment.id == payload.payment_id))
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    payment.status = payload.status
    payment.provider_payment_id = payload.provider_payment_id
    session.add(
        PaymentTransaction(payment_id=payment.id, event_type=f"provider.{payload.status}", payload=payload.raw_payload)
    )

    if payload.status == "paid":
        user = await session.scalar(select(User).where(User.id == payment.user_id))
        if user:
            user.is_premium = True
            base = _ensure_utc(user.premium_until) or now_utc()
            if base < now_utc():
                base = now_utc()
            user.premium_until = base + timedelta(days=30)
            if payment.plan_id:
                session.add(
                    Subscription(
                        user_id=user.id,
                        plan_id=payment.plan_id,
                        status="active",
                        started_at=now_utc(),
                        ends_at=user.premium_until,
                    )
                )

            if user.referred_by_user_id and payment.amount > 0:
                session.add(
                    ReferralReward(
                        referrer_user_id=user.referred_by_user_id,
                        invited_user_id=user.id,
                        trigger_type="first_paid",
                        reward_amount=round(payment.amount * 0.2, 2),
                        reward_status="granted",
                    )
                )

    await session.commit()
    await session.refresh(payment)
    return payment


async def register_referral(session: AsyncSession, payload: ReferralRegisterRequest) -> dict:
    invited_user = await get_or_create_user_by_telegram(session, payload.invited_telegram_id)
    referrer = await session.scalar(select(User).where(User.referral_code == payload.referral_code))
    if not referrer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral code not found")
    if referrer.telegram_id == invited_user.telegram_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Self referral is not allowed")
    if invited_user.referred_by_user_id:
        return {"ok": True, "already_linked": True}

    invited_user.referred_by_user_id = referrer.id
    session.add(
        ReferralReward(
            referrer_user_id=referrer.id,
            invited_user_id=invited_user.id,
            trigger_type="signup",
            reward_amount=0.0,
            reward_status="tracked",
        )
    )
    await session.commit()
    return {"ok": True, "referrer_user_id": referrer.id}


async def referral_overview(session: AsyncSession, user_id: str) -> dict:
    user = await session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    invited_count = await session.scalar(select(func.count()).select_from(User).where(User.referred_by_user_id == user_id))
    rewards = list(
        await session.scalars(select(ReferralReward).where(ReferralReward.referrer_user_id == user_id).limit(100))
    )
    earned_total = sum(r.reward_amount for r in rewards if r.reward_status == "granted")
    return {
        "referral_code": user.referral_code,
        "invited_count": invited_count or 0,
        "earned_total": earned_total,
        "rewards": [
            {
                "id": r.id,
                "invited_user_id": r.invited_user_id,
                "trigger_type": r.trigger_type,
                "reward_amount": r.reward_amount,
                "reward_status": r.reward_status,
            }
            for r in rewards
        ],
    }


async def create_campaign(session: AsyncSession, payload: BroadcastRequest) -> MailingCampaign:
    campaign = MailingCampaign(title=payload.title, body=payload.body, status="queued", segment=payload.segment)
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return campaign


async def queue_campaign_for_users(session: AsyncSession, campaign_id: str, limit: int = 1000) -> int:
    campaign = await session.scalar(select(MailingCampaign).where(MailingCampaign.id == campaign_id))
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    segment = campaign.segment or {}
    query = select(User).where(User.is_active.is_(True))
    if segment.get("premium") == "only":
        query = query.where(User.is_premium.is_(True))
    if segment.get("premium") == "exclude":
        query = query.where(User.is_premium.is_(False))
    if segment.get("active_days"):
        try:
            days = int(segment["active_days"])
            since = now_utc() - timedelta(days=days)
            query = query.where(User.updated_at >= since)
        except (TypeError, ValueError):
            pass
    if segment.get("city"):
        city = str(segment["city"]).strip()
        if city:
            query = query.join(Profile, Profile.user_id == User.id).where(Profile.city == city)
    query = query.limit(limit)
    users = list(await session.scalars(query))
    for user in users:
        session.add(MailingLog(campaign_id=campaign.id, user_id=user.id, delivery_status="queued"))
    await session.commit()
    return len(users)


async def collect_dashboard_metrics(session: AsyncSession) -> dict:
    users_total = await session.scalar(select(func.count()).select_from(User))
    profiles_total = await session.scalar(select(func.count()).select_from(Profile))
    matches_total = await session.scalar(select(func.count()).select_from(Match))
    reports_open = await session.scalar(select(func.count()).select_from(Report).where(Report.status == "open"))
    payments_paid = await session.scalar(select(func.count()).select_from(Payment).where(Payment.status == "paid"))
    subscriptions_active = await session.scalar(
        select(func.count()).select_from(Subscription).where(Subscription.status == "active")
    )
    return {
        "users_total": users_total or 0,
        "profiles_total": profiles_total or 0,
        "matches_total": matches_total or 0,
        "reports_open": reports_open or 0,
        "payments_paid": payments_paid or 0,
        "subscriptions_active": subscriptions_active or 0,
    }


async def log_ai_request(session: AsyncSession, user_id: str | None, feature: str, payload: dict) -> AIRequest:
    request = AIRequest(user_id=user_id, feature=feature, status="queued", payload=payload)
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return request


async def get_feature_flags(session: AsyncSession) -> list[FeatureFlag]:
    return list(await session.scalars(select(FeatureFlag)))


async def set_feature_flag(session: AsyncSession, key: str, value: bool, description: str | None = None) -> FeatureFlag:
    flag = await session.scalar(select(FeatureFlag).where(FeatureFlag.key == key))
    if flag is None:
        flag = FeatureFlag(key=key, value=value, description=description)
        session.add(flag)
    else:
        flag.value = value
        if description is not None:
            flag.description = description
    await session.commit()
    await session.refresh(flag)
    return flag


async def moderation_queue(session: AsyncSession, limit: int = 50) -> dict:
    profiles = list(await session.scalars(select(Profile).where(Profile.moderation_status == "pending").limit(limit)))
    reports = list(await session.scalars(select(Report).where(Report.status == "open").limit(limit)))
    return {
        "profiles_pending": [p.id for p in profiles],
        "reports_open": [r.id for r in reports],
    }


async def search_users_for_admin(session: AsyncSession, q: str | None = None, limit: int = 100) -> list[User]:
    query = select(User)
    if q:
        clauses = [User.username.ilike(f"%{q}%")]
        if q.isdigit():
            clauses.append(User.telegram_id == int(q))
        query = query.where(or_(*clauses))
    query = query.limit(limit)
    return list(await session.scalars(query))
