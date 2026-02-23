import logging

from aiogram import (
    F,
    Router,
)
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    Message,
)
from punq import Container

from app.bot.keyboards.inline import profile_inline_kb
from app.bot.utils.constants import user_profile_text_message
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService

logger = logging.getLogger(__name__)

user_profile_router: Router = Router(
    name="User profile router",
)


@user_profile_router.message(Command("profile"))
@user_profile_router.callback_query(F.data == "profile_page")
async def profile(
    update: Message | CallbackQuery,
    container: Container = init_container(),
):
    service: BaseUsersService = container.resolve(BaseUsersService)

    user = await service.get_user(telegram_id=update.from_user.id)

    photo = user.photo or ""
    caption = user_profile_text_message(user=user)
    keyboard = profile_inline_kb(user_id=update.from_user.id, liked_by=False)

    if isinstance(update, Message):
        target = update
    else:
        await update.message.delete()
        target = update.message

    if photo:
        try:
            await target.answer_photo(
                photo=photo,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            return
        except Exception as e:
            logger.warning(f"answer_photo failed (photo={photo!r}): {e}")

    # Fallback: показываем текст без фото
    await target.answer(
        text=caption,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
