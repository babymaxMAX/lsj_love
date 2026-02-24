"""
Platega Payment Integration
Docs: https://docs.platega.io/
Base URL: https://app.platega.io/api/

Response fields (CreateTransactionResponse):
  - transactionId  : UUID транзакции
  - redirect       : ссылка для оплаты
  - paymentDetails : строка (QR-данные СБП / адрес кошелька крипто)
  - usdtRate       : курс USDT (для крипто)
  - status         : PENDING / CONFIRMED / CANCELED
  - expiresIn      : HH:MM:SS до истечения

Callback payload (только CONFIRMED / CANCELED):
  - id, amount, currency, status, paymentMethod
  НЕТ поля payload → используем коллекцию transactions для связки
"""
import logging
from datetime import datetime, timedelta
from typing import Literal, Optional

import aiohttp
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from punq import Container

from app.logic.init import init_container
from app.logic.services.base import BaseUsersService
from app.settings.config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])

PLATEGA_BASE_URL = "https://app.platega.io"

PAYMENT_METHODS = {
    "sbp":    2,    # СБП QR
    "crypto": 13,   # Криптовалюта (USDT)
}

PRODUCTS = {
    "premium":   {"name": "Premium (1 месяц)", "days": 30, "premium_type": "premium"},
    "vip":       {"name": "VIP (1 месяц)",     "days": 30, "premium_type": "vip"},
    "superlike": {"name": "Суперлайк",         "days": 0,  "premium_type": None},
}


# ─── Schemas ─────────────────────────────────────────────────────────────────

class CreatePaymentRequest(BaseModel):
    telegram_id: int
    product: Literal["premium", "vip", "superlike"]
    method: Literal["sbp", "crypto"] = "sbp"


class CreatePaymentResponse(BaseModel):
    transaction_id: str
    method: str
    product: str
    amount: float
    currency: str = "RUB"
    redirect_url: Optional[str] = None
    expires_in: Optional[str] = None
    usdt_rate: Optional[float] = None
    usdt_amount: Optional[float] = None


class PaymentStatusResponse(BaseModel):
    transaction_id: str
    status: str
    premium_activated: bool = False


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_transactions_collection(container: Container):
    """Возвращает коллекцию MongoDB для хранения транзакций."""
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)
    return client[config.mongodb_dating_database]["transactions"]


async def _fetch_usdt_rate(merchant_id: str) -> Optional[float]:
    """
    Получает текущий курс RUB→USDT от Platega.
    Endpoint: GET /rates/payment_method_rate
    Возвращает rate: сколько USDT за 1 RUB (например, 0.0106).
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PLATEGA_BASE_URL}/rates/payment_method_rate",
                params={
                    "merchantId": merchant_id,
                    "paymentMethod": 13,   # Crypto (USDT)
                    "currencyFrom": "RUB",
                    "currencyTo": "USDT",
                },
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"USDT rate endpoint returned {resp.status}")
                    return None
                data = await resp.json()
                logger.info(f"USDT rate response: {data}")
                rate = data.get("rate")
                return float(rate) if rate else None
    except Exception as e:
        logger.warning(f"Failed to fetch USDT rate: {e}")
        return None


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/platega/usdt-rate")
async def get_usdt_rate(container: Container = Depends(init_container)):
    """
    Возвращает текущий курс USDT для отображения цен в UI.
    Ответ: { usdt_per_rub: float, rub_per_usdt: float }
    Пример: usdt_per_rub=0.0106 → 1 RUB = 0.0106 USDT → 1 USDT = 94 RUB
    """
    config: Config = container.resolve(Config)
    if not config.platega_merchant_id:
        return {"usdt_per_rub": None, "rub_per_usdt": None, "error": "not configured"}
    usdt_per_rub = await _fetch_usdt_rate(config.platega_merchant_id)
    if not usdt_per_rub or usdt_per_rub <= 0:
        return {"usdt_per_rub": None, "rub_per_usdt": None}
    return {
        "usdt_per_rub": usdt_per_rub,
        "rub_per_usdt": round(1.0 / usdt_per_rub, 1),
    }

@router.post("/platega/create", response_model=CreatePaymentResponse)
async def create_platega_payment(
    body: CreatePaymentRequest,
    container: Container = Depends(init_container),
):
    """Создаёт платёж в Platega. Возвращает данные для отображения QR / крипто адреса."""
    config: Config = container.resolve(Config)

    if not config.platega_merchant_id or not config.platega_secret:
        raise HTTPException(status_code=503, detail="Platega не настроен")

    prices = {
        "premium":   config.platega_premium_price,
        "vip":       config.platega_vip_price,
        "superlike": config.platega_superlike_price,
    }
    amount = prices[body.product]
    product_info = PRODUCTS[body.product]

    request_body = {
        "paymentMethod": PAYMENT_METHODS[body.method],
        "paymentDetails": {"amount": amount, "currency": "RUB"},
        "description": product_info["name"],
        "return": f"https://lsjlove.duckdns.org/users/{body.telegram_id}/premium?status=success",
        "failedUrl": f"https://lsjlove.duckdns.org/users/{body.telegram_id}/premium?status=failed",
        "payload": f"{body.telegram_id}:{body.product}",
    }

    headers = {
        "X-MerchantId": config.platega_merchant_id,
        "X-Secret": config.platega_secret,
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{PLATEGA_BASE_URL}/transaction/process",
                json=request_body,
                headers=headers,
            ) as resp:
                data = await resp.json()
                logger.info(f"Platega create response ({resp.status}): {data}")

                if resp.status not in (200, 201):
                    logger.error(f"Platega error {resp.status}: {data}")
                    raise HTTPException(status_code=502, detail=f"Platega error: {data}")

                transaction_id = str(data.get("transactionId", ""))
                redirect_url = data.get("redirect")
                payment_details = data.get("paymentDetails")  # str | dict | None
                usdt_rate = data.get("usdtRate")
                expires_in = data.get("expiresIn")

    except aiohttp.ClientError as e:
        logger.error(f"Platega network error: {e}")
        raise HTTPException(status_code=503, detail="Ошибка соединения с Platega")

    # Сохраняем транзакцию в MongoDB для webhook lookup
    col = _get_transactions_collection(container)
    await col.insert_one({
        "transaction_id": transaction_id,
        "telegram_id": body.telegram_id,
        "product": body.product,
        "method": body.method,
        "amount": amount,
        "status": "PENDING",
        "created_at": datetime.utcnow(),
    })

    # ── USDT расчёт ───────────────────────────────────────────────────────────
    # Platega возвращает usdtRate в формате USDT-за-1-RUB (например 0.0106 или 0.013).
    # НО в примере из документации написано 93.45 — непонятный формат.
    # Защита: если значение < 1 → это USDT/RUB → usdt = amount * rate
    #          если значение ≥ 1 → это RUB/USDT → usdt = amount / rate
    usdt_per_rub: Optional[float] = None   # всегда USDT за 1 RUB для расчётов
    usdt_amount: Optional[float] = None
    rub_per_usdt_display: Optional[float] = None  # для показа курса в UI

    if body.method == "crypto":
        raw_rate = data.get("usdtRate")
        if raw_rate:
            raw_rate = float(raw_rate)
            if raw_rate < 1:
                # Формат: 0.0106 USDT за 1 RUB
                usdt_per_rub = raw_rate
            else:
                # Формат: 94.5 RUB за 1 USDT
                usdt_per_rub = 1.0 / raw_rate

        if not usdt_per_rub:
            # Fallback: запрашиваем через rates endpoint
            usdt_per_rub = await _fetch_usdt_rate(config.platega_merchant_id)

        if usdt_per_rub and usdt_per_rub > 0:
            usdt_amount = round(amount * usdt_per_rub, 2)
            rub_per_usdt_display = round(1.0 / usdt_per_rub, 1)

        logger.info(f"Crypto: usdt_per_rub={usdt_per_rub}, usdt_amount={usdt_amount}, raw_usdtRate={data.get('usdtRate')}")

    response = CreatePaymentResponse(
        transaction_id=transaction_id,
        method=body.method,
        product=body.product,
        amount=amount,
        redirect_url=redirect_url,
        expires_in=expires_in,
        usdt_rate=rub_per_usdt_display,   # RUB за 1 USDT (для показа в UI)
        usdt_amount=usdt_amount,
    )

    return response


@router.get("/platega/status/{transaction_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    transaction_id: str,
    container: Container = Depends(init_container),
):
    """Проверяет статус транзакции — используется фронтендом для поллинга."""
    config: Config = container.resolve(Config)

    headers = {
        "X-MerchantId": config.platega_merchant_id,
        "X-Secret": config.platega_secret,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PLATEGA_BASE_URL}/transaction/{transaction_id}",
                headers=headers,
            ) as resp:
                data = await resp.json()
                platega_status = data.get("status", "PENDING")
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=503, detail="Ошибка Platega")

    # Если подтверждено и ещё не активировано — активируем
    premium_activated = False
    if platega_status == "CONFIRMED":
        col = _get_transactions_collection(container)
        tx = await col.find_one({"transaction_id": transaction_id})

        if tx and tx.get("status") != "CONFIRMED":
            # Активируем Premium
            service: BaseUsersService = container.resolve(BaseUsersService)
            product_info = PRODUCTS.get(tx["product"], {})
            if product_info.get("premium_type"):
                until = datetime.utcnow() + timedelta(days=product_info["days"])
                try:
                    await service.update_user_info_after_reg(
                        telegram_id=tx["telegram_id"],
                        data={
                            "premium_type": product_info["premium_type"],
                            "premium_until": until,
                        },
                    )
                    premium_activated = True
                except Exception as e:
                    logger.error(f"Premium activation error: {e}")

            # Обновляем статус в БД
            await col.update_one(
                {"transaction_id": transaction_id},
                {"$set": {"status": "CONFIRMED", "confirmed_at": datetime.utcnow()}},
            )

    return PaymentStatusResponse(
        transaction_id=transaction_id,
        status=platega_status,
        premium_activated=premium_activated,
    )


@router.post("/platega/webhook", include_in_schema=False)
async def platega_webhook(
    request: Request,
    container: Container = Depends(init_container),
):
    """
    Webhook от Platega при смене статуса транзакции.
    Callback URL: https://lsjlove.duckdns.org/api/v1/payments/platega/webhook

    CallbackPayload: { id, amount, currency, status, paymentMethod }
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.info(f"Platega webhook: {data}")

    platega_status = data.get("status")
    transaction_id = str(data.get("id", ""))

    if platega_status != "CONFIRMED":
        return JSONResponse({"ok": True, "skipped": True})

    # Ищем транзакцию в MongoDB по transaction_id
    col = _get_transactions_collection(container)
    tx = await col.find_one({"transaction_id": transaction_id})

    if not tx:
        # Fallback: попробуем через payload если Platega его вернул
        payload = data.get("payload", "")
        if ":" in payload:
            parts = payload.split(":")
            try:
                telegram_id = int(parts[0])
                product = parts[1]
                tx = {"telegram_id": telegram_id, "product": product, "status": "PENDING"}
            except (ValueError, IndexError):
                logger.error(f"Transaction not found and no valid payload: {transaction_id}")
                return JSONResponse({"ok": True, "error": "transaction not found"})
        else:
            logger.error(f"Transaction not found: {transaction_id}")
            return JSONResponse({"ok": True, "error": "transaction not found"})

    if tx.get("status") == "CONFIRMED":
        return JSONResponse({"ok": True, "already_confirmed": True})

    product_info = PRODUCTS.get(tx["product"], {})
    if product_info.get("premium_type"):
        service: BaseUsersService = container.resolve(BaseUsersService)
        until = datetime.utcnow() + timedelta(days=product_info["days"])
        try:
            await service.update_user_info_after_reg(
                telegram_id=tx["telegram_id"],
                data={
                    "premium_type": product_info["premium_type"],
                    "premium_until": until,
                },
            )
            logger.info(f"Premium activated via webhook: user={tx['telegram_id']}")
        except Exception as e:
            logger.error(f"Premium activation failed: {e}")
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    await col.update_one(
        {"transaction_id": transaction_id},
        {"$set": {"status": "CONFIRMED", "confirmed_at": datetime.utcnow()}},
    )

    return JSONResponse({"ok": True})
