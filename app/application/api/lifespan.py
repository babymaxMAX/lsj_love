"""Lifespan: webhook при старте и остановке."""
from app.bot.main import bot, config, dp
from app.settings.logger import setup_logging


def start_logger():
    setup_logging()


async def set_bot_webhook():
    await bot.set_webhook(
        url=config.full_webhook_url,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )


async def delete_bot_webhook():
    await bot.delete_webhook()
