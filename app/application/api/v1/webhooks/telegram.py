import logging

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from aiogram.types import Update

from app.bot.main import (
    bot,
    dp,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Telegram"],
)


@router.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
    return JSONResponse({"ok": True})
