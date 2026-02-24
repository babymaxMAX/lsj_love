from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from punq import Container

from app.bot.handlers.users.profile import profile
from app.bot.handlers.users.registration import start_registration
from app.domain.entities.users import UserEntity
from app.domain.exceptions.base import ApplicationException
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService


user_router: Router = Router(
    name="User router",
)


@user_router.message(CommandStart())
async def start(message: Message, state: FSMContext, container: Container = init_container()):
    await state.clear()

    service: BaseUsersService = container.resolve(BaseUsersService)

    # Парсим реферальный параметр: /start ref_12345678
    referral_from: int | None = None
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        arg = parts[1].strip()
        if arg.startswith("ref_"):
            try:
                candidate = int(arg[4:])
                if candidate != message.from_user.id:
                    referral_from = candidate
            except ValueError:
                pass

    try:
        user = await service.get_user(telegram_id=message.from_user.id)

        if user.is_active:
            await message.answer(
                text=f"С возвращением, <b>{message.from_user.first_name}</b>! 💫",
                parse_mode="HTML",
            )
            await profile(message)
        else:
            if not message.from_user.username:
                await message.answer(
                    text="Сначала установи <b>username</b> в настройках Telegram, затем напиши /start снова.",
                    parse_mode="HTML",
                )
            else:
                await message.answer(
                    text=f"Привет, <b>{message.from_user.first_name}</b>! 👋\n"
                         f"Ты ещё не заполнил анкету. Давай сделаем это прямо сейчас!",
                    parse_mode="HTML",
                )
                await start_registration(message, state)

    except ApplicationException:
        # Новый пользователь
        user = UserEntity.from_telegram_user(user=message.from_user)

        # Если пришёл по реферальной ссылке — проверяем что реферер существует
        if referral_from:
            try:
                await service.get_user(telegram_id=referral_from)
                user.referred_by = referral_from
            except ApplicationException:
                pass  # реферер не найден — игнорируем

        await service.create_user(user)

        if not message.from_user.username:
            await message.answer(
                text=f"Привет, <b>{message.from_user.first_name}</b>! 👋\n\n"
                     f"Сначала установи <b>username</b> в настройках Telegram, "
                     f"затем напиши /start снова.",
                parse_mode="HTML",
            )
        else:
            welcome = (
                f"Добро пожаловать в <b>LSJLove</b> 💕\n\n"
                f"Здесь ты найдёшь свою вторую половинку.\n"
                f"Заполним анкету прямо сейчас — это займёт меньше минуты!"
            )
            if referral_from:
                welcome += "\n\n🎁 Ты зарегистрировался по реферальной ссылке!"
            await message.answer(text=welcome, parse_mode="HTML")
            await start_registration(message, state)
