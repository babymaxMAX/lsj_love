import logging
import urllib.parse
from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from punq import Container

from app.bot.handlers.users.profile import profile
from app.bot.handlers.users.registration import start_registration
from app.domain.entities.users import UserEntity
from app.domain.exceptions.base import ApplicationException
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService

logger = logging.getLogger(__name__)

user_router: Router = Router(name="User router")


def _referral_notify_kb() -> InlineKeyboardMarkup:
    """Клавиатура уведомления реферрера — кнопка вывода и просмотра баланса."""
    withdraw_text = "Здравствуйте, я хотел бы запросить вывод средств по реферальной системе LsJ_Love"
    withdraw_url = f"https://t.me/babymaxx?text={urllib.parse.quote(withdraw_text)}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Запросить вывод", url=withdraw_url)],
        [InlineKeyboardButton(text="🔗 Моя реферальная программа", callback_data="referral_info")],
    ])


async def _notify_referrer_registration(bot, referrer_id: int, new_user: Message, current_balance: float):
    """Уведомляет реферрера о новой регистрации по его ссылке."""
    try:
        tg_user = new_user.from_user
        name = tg_user.first_name or ""
        username_part = f" (@{tg_user.username})" if tg_user.username else ""

        await bot.send_message(
            chat_id=referrer_id,
            text=(
                f"🎉 <b>По твоей реферальной ссылке зарегистрировался новый пользователь!</b>\n\n"
                f"👤 <b>{name}{username_part}</b>\n\n"
                f"Когда он совершит покупку — ты получишь <b>50%</b> от суммы на баланс.\n\n"
                f"💰 Текущий баланс: <b>{current_balance:.2f} ₽</b>"
            ),
            parse_mode="HTML",
            reply_markup=_referral_notify_kb(),
        )
    except Exception as e:
        logger.warning(f"Referral registration notify failed: {e}")


@user_router.message(CommandStart())
async def start(message: Message, state: FSMContext, container: Container = init_container()):
    await state.clear()

    try:
        await message.delete()
    except Exception:
        pass

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
            from app.settings.config import Config
            from app.bot.handlers.users.admin import ADMIN_IDS
            config: Config = container.resolve(Config)
            await service.update_user_info_after_reg(
                telegram_id=message.from_user.id,
                data={"last_seen": datetime.now(timezone.utc)},
            )
            app_url = f"{config.front_end_url}/users/{message.from_user.id}"
            buttons = [
                [InlineKeyboardButton(
                    text="📱 Открыть как приложение",
                    web_app=WebAppInfo(url=app_url),
                )],
                [InlineKeyboardButton(text="🌐 Открыть как сайт", url=app_url)],
                [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile_page")],
                [InlineKeyboardButton(text="⭐ Premium", callback_data="premium_info")],
                [InlineKeyboardButton(text="💬 Поддержка LSJLove", url="https://t.me/babymaxx")],
            ]
            if message.from_user.id in ADMIN_IDS:
                buttons.append([InlineKeyboardButton(text="🛠 Панель администратора", callback_data="adm:main")])
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
            await message.answer(
                text=(
                    f"С возвращением, <b>{message.from_user.first_name}</b>! 💫\n\n"
                    f"Что нового:\n"
                    f"• 🔥 Свайпай анкеты и находи людей рядом\n"
                    f"• 🤖 AI поможет написать первое сообщение\n"
                    f"• 💕 Проверяй матчи и общайся\n\n"
                    f"Открой приложение и начни знакомиться! 👇"
                ),
                parse_mode="HTML",
                reply_markup=kb,
            )
            return
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

        # Проверяем реферера
        referrer = None
        if referral_from:
            try:
                referrer = await service.get_user(telegram_id=referral_from)
                user.referred_by = referral_from
            except ApplicationException:
                pass  # реферер не найден — игнорируем

        await service.create_user(user)

        # Уведомляем реферера о новой регистрации
        if referrer and referral_from:
            current_balance = float(getattr(referrer, "referral_balance", 0) or 0)
            await _notify_referrer_registration(
                bot=message.bot,
                referrer_id=referral_from,
                new_user=message,
                current_balance=current_balance,
            )

        if not message.from_user.username:
            await message.answer(
                text=f"Привет, <b>{message.from_user.first_name}</b>! 👋\n\n"
                     f"Сначала установи <b>username</b> в настройках Telegram, "
                     f"затем напиши /start снова.",
                parse_mode="HTML",
            )
        else:
            welcome = (
                "💕 Добро пожаловать в <b>LSJLove</b>!\n\n"
                "Здесь ты найдёшь свою вторую половинку.\n\n"
                "✨ <b>Что тебя ждёт:</b>\n"
                "• Свайпай анкеты и находи людей рядом\n"
                "• AI напишет первое сообщение за тебя\n"
                "• Подбор пары по фото и интересам\n\n"
                "Заполним анкету прямо сейчас — это займёт меньше минуты!"
            )
            if referral_from and referrer:
                welcome += "\n\n🎁 Ты зарегистрировался по реферальной ссылке!"
            await message.answer(text=welcome, parse_mode="HTML")
            await start_registration(message, state)
