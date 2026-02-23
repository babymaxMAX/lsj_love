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
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        user = await service.get_user(telegram_id=message.from_user.id)

        if user.is_active:
            # Пользователь уже зарегистрирован — показываем профиль
            await message.answer(
                text=f"С возвращением, <b>{message.from_user.first_name}</b>! 💫",
                parse_mode="HTML",
            )
            await profile(message)
        else:
            # Пользователь есть в базе, но не заполнил анкету
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
        await service.create_user(user)

        if not message.from_user.username:
            await message.answer(
                text=f"Привет, <b>{message.from_user.first_name}</b>! 👋\n\n"
                     f"Сначала установи <b>username</b> в настройках Telegram, "
                     f"затем напиши /start снова.",
                parse_mode="HTML",
            )
        else:
            await message.answer(
                text=f"Добро пожаловать в <b>LSJLove</b> 💕\n\n"
                     f"Здесь ты найдёшь свою вторую половинку.\n"
                     f"Заполним анкету прямо сейчас — это займёт меньше минуты!",
                parse_mode="HTML",
            )
            await start_registration(message, state)
