from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="user", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    referral_code: Mapped[str | None] = mapped_column(String(64), unique=True)
    referred_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    age: Mapped[int] = mapped_column(Integer, index=True)
    gender: Mapped[str] = mapped_column(String(16), index=True)
    target_gender: Mapped[str] = mapped_column(String(16), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    bio: Mapped[str] = mapped_column(Text, default="")
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    moderation_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified", index=True)
    visibility: Mapped[str] = mapped_column(String(16), default="public", index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)


class Swipe(Base, TimestampMixin):
    __tablename__ = "swipes"
    __table_args__ = (UniqueConstraint("from_user_id", "to_user_id", name="uq_swipe_from_to"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    from_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    to_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(16), index=True)  # like/dislike/report


class Match(Base, TimestampMixin):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("user_a_id", "user_b_id", name="uq_match_pair"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_a_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    user_b_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    reporter_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    target_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(String(64), index=True)
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120))
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[str | None] = mapped_column(ForeignKey("plans.id"))
    provider: Mapped[str] = mapped_column(String(32), index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    status: Mapped[str] = mapped_column(String(16), default="created", index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), index=True)


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class PaymentTransaction(Base, TimestampMixin):
    __tablename__ = "payment_transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class ReferralReward(Base, TimestampMixin):
    __tablename__ = "referral_rewards"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    referrer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    invited_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    trigger_type: Mapped[str] = mapped_column(String(32), index=True)
    reward_amount: Mapped[float] = mapped_column(Float, default=0.0)
    reward_status: Mapped[str] = mapped_column(String(16), default="created", index=True)


class AuthToken(Base, TimestampMixin):
    __tablename__ = "auth_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MailingCampaign(Base, TimestampMixin):
    __tablename__ = "mailing_campaigns"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    segment: Mapped[dict] = mapped_column(JSON, default=dict)


class MailingLog(Base, TimestampMixin):
    __tablename__ = "mailing_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    campaign_id: Mapped[str] = mapped_column(ForeignKey("mailing_campaigns.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    delivery_status: Mapped[str] = mapped_column(String(16), default="queued", index=True)


class AIRequest(Base, TimestampMixin):
    __tablename__ = "ai_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    feature: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16), default="created", index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class AdminUser(Base, TimestampMixin):
    __tablename__ = "admin_users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    admin_role: Mapped[str] = mapped_column(String(32), default="moderator", index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class FeatureFlag(Base, TimestampMixin):
    __tablename__ = "feature_flags"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    value: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
