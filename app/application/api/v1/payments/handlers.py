"""
Platega Payment Integration
Docs: https://docs.platega.io/
Base URL: https://app.platega.io/
"""
import logging
from datetime import datetime, timedelta
from typing import Literal

import aiohttp
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from pydantic import BaseModel
from punq import Container

from app.logic.init import init_container
from app.logic.services.base import BaseUsersService
from app.settings.config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])

PLATEGA_BASE_URL = "https://app.platega.io"

# Способы оплаты Platega
PAYMENT_METHODS = {
    "card": 10,       # Карты RUB (МИР, Visa, Mastercard)
    "sbp": 2,         # СБП QR
    "crypto": 13,     # Криптовалюта
}

# Типы продуктов
PRODUCTS = {
    "premium": {"name": "Premium подписка (1 месяц)", "days": 30, "premium_type": "premium"},
    "vip":     {"name": "VIP подписка (1 месяц)",     "days": 30, "premium_type": "vip"},
    "superlike": {"name": "Суперлайк",                "days": 0,  "premium_type": None},
}


class CreatePaymentRequest(BaseModel):
    telegram_id: int
    product: Literal["premium", "vip", "superlike"]
    method: Literal["card", "sbp", "crypto"] = "card"


class CreatePaymentResponse(BaseModel):
    payment_url: str
    transaction_id: str
    amount: float
    product: str
    method: str


@router.post("/platega/create", response_model=CreatePaymentResponse)
async def create_platega_payment(
    body: CreatePaymentRequest,
    container: Container = Depends(init_container),
):
    """Создаёт платёж в Platega и возвращает ссылку для оплаты."""
    config: Config = container.resolve(Config)

    if not config.platega_merchant_id or not config.platega_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Platega не настроен",
        )

    # Определяем сумму
    prices = {
        "premium": config.platega_premium_price,
        "vip":     config.platega_vip_price,
        "superlike": config.platega_superlike_price,
    }
    amount = prices[body.product]
    product_info = PRODUCTS[body.product]

    payload = f"{body.telegram_id}:{body.product}"

    request_body = {
        "paymentMethod": PAYMENT_METHODS[body.method],
        "paymentDetails": {
            "amount": amount,
            "currency": "RUB",
        },
        "description": product_info["name"],
        "return": f"https://lsjlove.duckdns.org/users/{body.telegram_id}/premium?status=success",
        "failedUrl": f"https://lsjlove.duckdns.org/users/{body.telegram_id}/premium?status=failed",
        "payload": payload,
    }

    headers = {
        "X-MerchantId": config.platega_merchant_id,
        "X-Secret": config.platega_secret,
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{PLATEGA_BASE_URL}/api/transaction/create",
                json=request_body,
                headers=headers,
            ) as resp:
                data = await resp.json()
                if resp.status != 200 or not data.get("paymentUrl"):
                    logger.error(f"Platega create error: {resp.status} {data}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Ошибка Platega: {data}",
                    )

                return CreatePaymentResponse(
                    payment_url=data["paymentUrl"],
                    transaction_id=str(data.get("id", "")),
                    amount=amount,
                    product=body.product,
                    method=body.method,
                )
    except aiohttp.ClientError as e:
        logger.error(f"Platega network error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ошибка соединения с Platega",
        )


@router.post("/platega/webhook", include_in_schema=False)
async def platega_webhook(
    request: Request,
    container: Container = Depends(init_container),
):
    """
    Webhook от Platega — вызывается при изменении статуса платежа.
    Callback URL в ЛК Platega: https://lsjlove.duckdns.org/api/v1/payments/platega/webhook
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.info(f"Platega webhook received: {data}")

    transaction_status = data.get("status")
    payload = data.get("payload", "")

    # Обрабатываем только успешные платежи
    if transaction_status != "CONFIRMED":
        return JSONResponse({"ok": True, "skipped": True})

    # payload = "telegram_id:product"
    try:
        parts = payload.split(":")
        telegram_id = int(parts[0])
        product = parts[1]
    except (ValueError, IndexError):
        logger.error(f"Invalid payload in webhook: {payload}")
        return JSONResponse({"ok": True, "error": "invalid payload"})

    product_info = PRODUCTS.get(product)
    if not product_info or not product_info["premium_type"]:
        # Суперлайк или неизвестный продукт — просто логируем
        logger.info(f"Superlike purchased by {telegram_id}")
        return JSONResponse({"ok": True})

    # Активируем Premium в базе
    service: BaseUsersService = container.resolve(BaseUsersService)
    try:
        until = datetime.utcnow() + timedelta(days=product_info["days"])
        await service.update_user_info_after_reg(
            telegram_id=telegram_id,
            data={
                "premium_type": product_info["premium_type"],
                "premium_until": until,
            },
        )
        logger.info(
            f"Premium activated: user={telegram_id} type={product_info['premium_type']} until={until}"
        )
    except Exception as e:
        logger.error(f"Failed to activate premium for {telegram_id}: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    return JSONResponse({"ok": True})


@router.get("/platega/status/{transaction_id}")
async def get_payment_status(
    transaction_id: str,
    container: Container = Depends(init_container),
):
    """Проверяет статус транзакции в Platega."""
    config: Config = container.resolve(Config)

    headers = {
        "X-MerchantId": config.platega_merchant_id,
        "X-Secret": config.platega_secret,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{PLATEGA_BASE_URL}/api/transaction/{transaction_id}",
            headers=headers,
        ) as resp:
            data = await resp.json()
            return data
