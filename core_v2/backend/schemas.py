from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "core_v2_api"


class AuthCreateTokenRequest(BaseModel):
    telegram_id: int


class AuthExchangeRequest(BaseModel):
    token: str


class AuthExchangeResponse(BaseModel):
    ok: bool
    telegram_id: int | None = None


class ProfileUpsertRequest(BaseModel):
    display_name: str
    age: int = Field(ge=18, le=99)
    gender: str
    target_gender: str
    city: str
    bio: str = ""
    interests: list[str] = []


class SwipeRequest(BaseModel):
    from_user_id: str
    to_user_id: str
    action: str


class ReportCreateRequest(BaseModel):
    reporter_user_id: str
    target_user_id: str
    reason: str
    details: str | None = None


class PaymentCreateRequest(BaseModel):
    user_id: str
    plan_code: str
    provider: str = "platega"
    idempotency_key: str


class PaymentWebhookRequest(BaseModel):
    payment_id: str
    provider_payment_id: str | None = None
    status: str
    raw_payload: dict = {}


class ReferralRegisterRequest(BaseModel):
    invited_telegram_id: int
    referral_code: str


class BroadcastRequest(BaseModel):
    title: str
    body: str
    segment: dict = {}
    scheduled_at: datetime | None = None

