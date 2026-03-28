from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

from core_v2.backend.settings import V2Settings


settings = V2Settings()
bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "AI Kupidon v2 запущен.\n"
        "Это parallel-run контур. Основной функционал будет расширяться по этапам."
    )


dp.include_router(router)


async def run_bot() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_bot())
