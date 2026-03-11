"""
Auth: вход на сайт через бота (режим A — одноразовый токен).
POST /auth/token — создаёт одноразовый токен для telegram_id (вызывается ботом).
POST /auth/exchange — обменивает токен на сессию (cookie).
"""
import hashlib
import hmac
import secrets
from base64 import b64encode
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from punq import Container

from app.logic.init import init_container
from app.settings.config import Config


router = APIRouter(prefix="/auth", tags=["Auth"])
TOKEN_TTL_MINUTES = 5
SESSION_COOKIE_NAME = "lsj_session"
SESSION_DAYS = 30


class CreateTokenRequest(BaseModel):
    telegram_id: int


class CreateTokenResponse(BaseModel):
    token: str
    expires_in_seconds: int = TOKEN_TTL_MINUTES * 60


class ExchangeTokenRequest(BaseModel):
    token: str


class ExchangeTokenResponse(BaseModel):
    ok: bool
    telegram_id: Optional[int] = None


def _get_auth_tokens_collection(container: Container):
    config: Config = container.resolve(Config)
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    return client[config.mongodb_dating_database]["auth_tokens"]


def _make_session_value(telegram_id: int, secret: str) -> str:
    payload = f"{telegram_id}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return b64encode(f"{telegram_id}:{sig}".encode()).decode()


def _parse_session_cookie(value: str, secret: str) -> Optional[int]:
    try:
        import base64
        raw = base64.b64decode(value.encode()).decode()
        parts = raw.split(":")
        if len(parts) != 2:
            return None
        tid, sig = int(parts[0]), parts[1]
        expected = hmac.new(secret.encode(), str(tid).encode(), hashlib.sha256).hexdigest()[:16]
        if hmac.compare_digest(sig, expected):
            return tid
    except Exception:
        pass
    return None


async def create_login_token_internal(telegram_id: int, container: Container) -> str:
    """Внутренняя функция: создаёт токен и возвращает его. Вызывается ботом."""
    col = _get_auth_tokens_collection(container)
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_TTL_MINUTES)
    await col.insert_one({
        "token": token,
        "telegram_id": telegram_id,
        "expires_at": expires,
        "used": False,
    })
    return token


@router.post("/token", response_model=CreateTokenResponse)
async def create_login_token(
    body: CreateTokenRequest,
    container: Container = Depends(init_container),
):
    """
    Создаёт одноразовый токен для входа на сайт.
    Вызывается ботом при нажатии "Открыть сайт" или перед формированием deep link.
    """
    token = await create_login_token_internal(body.telegram_id, container)
    return CreateTokenResponse(token=token, expires_in_seconds=TOKEN_TTL_MINUTES * 60)


@router.post("/exchange", response_model=ExchangeTokenResponse)
async def exchange_token_for_session(
    body: ExchangeTokenRequest,
    response: Response,
    container: Container = Depends(init_container),
):
    """
    Обменивает одноразовый токен на сессию (устанавливает httpOnly cookie).
    Вызывается фронтендом при переходе по ?token=...
    """
    config: Config = container.resolve(Config)
    secret = getattr(config, "admin_secret_key", None) or "lsj-auth-fallback-secret"
    col = _get_auth_tokens_collection(container)
    doc = await col.find_one({"token": body.token, "used": False})
    if not doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Токен недействителен или уже использован")
    expires_at = doc.get("expires_at")
    if expires_at and datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Токен истёк")
    telegram_id = doc["telegram_id"]
    await col.update_one({"token": body.token}, {"$set": {"used": True}})
    session_value = _make_session_value(telegram_id, secret)
    import os
    is_prod = os.getenv("ENVIRONMENT", "development") == "production"
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_value,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=SESSION_DAYS * 24 * 3600,
    )
    return ExchangeTokenResponse(ok=True, telegram_id=telegram_id)


@router.get("/me")
async def get_me(
    request: Request,
    container: Container = Depends(init_container),
):
    """Возвращает telegram_id текущего пользователя из сессии."""
    config: Config = container.resolve(Config)
    secret = getattr(config, "admin_secret_key", None) or "lsj-auth-fallback-secret"
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")
    tid = _parse_session_cookie(cookie, secret)
    if tid is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия недействительна")
    return {"telegram_id": tid}


async def get_current_user(
    request: Request,
    container: Container = Depends(init_container),
) -> int:
    """FastAPI dependency: возвращает telegram_id из сессионной cookie."""
    config: Config = container.resolve(Config)
    secret = getattr(config, "admin_secret_key", None) or "lsj-auth-fallback-secret"
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")
    tid = _parse_session_cookie(cookie, secret)
    if tid is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия недействительна")
    return tid
