"""Lifespan: webhook при старте и остановке."""
from app.bot.main import bot, config, dp
from app.settings.logger import setup_logging

# Кэш username бота (для relay-чата при матчах без @username)
_cached_bot_username: str = ""


def get_bot_username() -> str:
    return _cached_bot_username or getattr(config, "bot_username", None) or ""


def start_logger():
    setup_logging()


async def set_bot_webhook():
    global _cached_bot_username
    await bot.set_webhook(
        url=config.full_webhook_url,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )
    if not getattr(config, "bot_username", None) or not str(config.bot_username).strip():
        try:
            me = await bot.get_me()
            _cached_bot_username = me.username or ""
        except Exception:
            _cached_bot_username = ""
    else:
        _cached_bot_username = str(config.bot_username).strip()


async def delete_bot_webhook():
    await bot.delete_webhook()
