import logging

from aiogram import (
    F,
    Router,
)
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from punq import Container

from app.bot.keyboards.inline import profile_inline_kb
from app.bot.utils.constants import user_profile_text_message
from app.bot.utils.notificator import _resolve_photo
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService


def _compute_boosts_left(user, now) -> int:
    """Считает оставшиеся бусты на этой неделе (максимум 3)."""
    from datetime import timezone, timedelta
    MAX_BOOSTS = 3
    week_reset = getattr(user, "boost_week_reset", None)
    boosts_used = getattr(user, "boosts_this_week", 0) or 0

    if week_reset:
        if hasattr(week_reset, "tzinfo") and week_reset.tzinfo is None:
            week_reset = week_reset.replace(tzinfo=timezone.utc)
        # Неделя прошла — сбрасываем
        if (now - week_reset).days >= 7:
            return MAX_BOOSTS

    return max(0, MAX_BOOSTS - boosts_used)

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

    from datetime import datetime, timezone
    caption = user_profile_text_message(user=user)

    # Проверяем VIP для кнопки буста
    pt = getattr(user, "premium_type", None)
    until = getattr(user, "premium_until", None)
    now = datetime.now(timezone.utc)
    if until and hasattr(until, "tzinfo") and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    is_vip = bool(pt == "vip" and until and now < until)
    boosts_left = _compute_boosts_left(user, now) if is_vip else 0

    profile_hidden = bool(getattr(user, "profile_hidden", False))
    gender = str(getattr(user, "gender", "") or "")
    allow_girls = bool(getattr(user, "allow_girls_write_first", False))
    keyboard = profile_inline_kb(
        user_id=update.from_user.id,
        liked_by=False,
        is_vip=is_vip,
        boosts_left=boosts_left,
        is_active=not profile_hidden,
        gender=gender,
        allow_girls_write_first=allow_girls,
    )

    if isinstance(update, Message):
        try:
            await update.delete()
        except Exception:
            pass
        target = update
    else:
        try:
            await update.message.delete()
        except Exception:
            pass
        target = update.message

    # Определяем фото: берём первое из photos[] если есть, иначе photo
    photos_list = getattr(user, "photos", []) or []
    raw_photo = photos_list[0] if photos_list else (user.photo or "")

    if raw_photo:
        resolved = await _resolve_photo(raw_photo, user_id=user.telegram_id)
        if resolved:
            try:
                photo_input = BufferedInputFile(resolved, filename="photo.jpg") if isinstance(resolved, bytes) else resolved
                await target.answer_photo(
                    photo=photo_input,
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
                return
            except Exception as e:
                logger.warning(f"answer_photo failed: {e}")

    # Fallback: показываем текст без фото
    await target.answer(
        text=caption,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@user_profile_router.callback_query(F.data == "referral_info")
async def referral_info(
    callback: CallbackQuery,
    container: Container = init_container(),
):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    service: BaseUsersService = container.resolve(BaseUsersService)
    await callback.answer()

    try:
        user = await service.get_user(telegram_id=callback.from_user.id)
    except Exception:
        await callback.message.answer("Ошибка получения профиля.")
        return

    # Получаем username бота для формирования ссылки
    try:
        bot_me = await callback.bot.get_me()
        bot_username = bot_me.username
    except Exception:
        bot_username = "LsJ_loveBot"

    referral_link = f"https://t.me/{bot_username}?start=ref_{callback.from_user.id}"
    balance = float(getattr(user, "referral_balance", 0) or 0)
    referred_by = getattr(user, "referred_by", None)

    referred_line = ""
    if referred_by:
        referred_line = f"\n📨 Ты пришёл по реферальной ссылке."

    text = (
        f"🔗 <b>Реферальная программа LSJLove</b>\n\n"
        f"Приглашай друзей — зарабатывай <b>50%</b> с каждой их покупки!\n\n"
        f"<b>Твоя ссылка:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        f"💰 <b>Твой баланс: {balance:.2f} ₽</b>\n"
        f"{referred_line}\n"
        f"─────────────────────\n"
        f"Как это работает:\n"
        f"1. Поделись ссылкой с другом\n"
        f"2. Друг регистрируется и оплачивает подписку или покупку\n"
        f"3. Ты автоматически получаешь <b>50%</b> от суммы на баланс\n"
        f"4. Деньги приходят мгновенно — ты получишь уведомление\n\n"
        f"💸 <b>Вывод средств:</b> нажми кнопку ниже — откроется чат,\n"
        f"сообщение о выводе заполнится автоматически.\n\n"
        f"<i>Баланс виден только тебе.</i>"
    )

    withdraw_text = "Здравствуйте, я хотел бы запросить вывод средств по реферальной системе LsJ_Love"
    import urllib.parse
    withdraw_url = f"https://t.me/babymaxx?text={urllib.parse.quote(withdraw_text)}"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Скопировать ссылку", switch_inline_query=referral_link)],
        [InlineKeyboardButton(text="💸 Запросить вывод средств", url=withdraw_url)],
        [InlineKeyboardButton(text="🔙 В профиль", callback_data="profile_page")],
    ])

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=back_kb)


@user_profile_router.callback_query(F.data == "toggle_visibility")
async def toggle_visibility(
    callback: CallbackQuery,
    container: Container = init_container(),
):
    service: BaseUsersService = container.resolve(BaseUsersService)
    await callback.answer()

    try:
        user = await service.get_user(telegram_id=callback.from_user.id)
    except Exception:
        await callback.message.answer("Ошибка получения профиля.")
        return

    currently_hidden = bool(getattr(user, "profile_hidden", False))
    new_hidden = not currently_hidden
    await service.update_user_info_after_reg(
        telegram_id=callback.from_user.id,
        data={"profile_hidden": new_hidden},
    )

    if not new_hidden:
        msg = "👀 <b>Анкета снова видна в поиске!</b>\n\nДругие пользователи смогут найти тебя."
    else:
        msg = "👻 <b>Анкета скрыта.</b>\n\nТебя не видно в поиске, пока не включишь снова."

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В профиль", callback_data="profile_page")]
    ])
    try:
        await callback.message.edit_text(msg, parse_mode="HTML", reply_markup=back_kb)
    except Exception:
        await callback.message.answer(msg, parse_mode="HTML", reply_markup=back_kb)


@user_profile_router.callback_query(F.data == "boost_profile")
async def boost_profile(
    callback: CallbackQuery,
    container: Container = init_container(),
):
    from datetime import datetime, timezone, timedelta
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    service: BaseUsersService = container.resolve(BaseUsersService)
    await callback.answer()

    try:
        user = await service.get_user(telegram_id=callback.from_user.id)
    except Exception:
        await callback.message.answer("Ошибка получения профиля.")
        return

    now = datetime.now(timezone.utc)

    # Проверяем VIP
    pt = getattr(user, "premium_type", None)
    until = getattr(user, "premium_until", None)
    if until and hasattr(until, "tzinfo") and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    if not (pt == "vip" and until and now < until):
        await callback.message.answer("🔒 Буст профиля доступен только с подпиской VIP.")
        return

    boosts_left = _compute_boosts_left(user, now)
    if boosts_left <= 0:
        await callback.message.answer(
            "⏳ <b>Бусты на эту неделю закончились.</b>\n\n"
            "Следующие 3 буста будут доступны через 7 дней с первого использования.",
            parse_mode="HTML",
        )
        return

    # Применяем буст
    week_reset = getattr(user, "boost_week_reset", None)
    boosts_used = getattr(user, "boosts_this_week", 0) or 0
    if week_reset and hasattr(week_reset, "tzinfo") and week_reset.tzinfo is None:
        week_reset = week_reset.replace(tzinfo=timezone.utc)

    is_new_week = not week_reset or (now - week_reset).days >= 7
    if is_new_week:
        new_boosts_used = 1
        new_week_reset = now
    else:
        new_boosts_used = boosts_used + 1
        new_week_reset = week_reset

    boost_until = now + timedelta(hours=24)
    await service.update_user_info_after_reg(
        telegram_id=callback.from_user.id,
        data={
            "boost_until": boost_until,
            "boosts_this_week": new_boosts_used,
            "boost_week_reset": new_week_reset,
        },
    )

    remaining = 3 - new_boosts_used
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_page")]
    ])
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        f"🚀 <b>Профиль забустирован на 24 часа!</b>\n\n"
        f"Твоя анкета показывается первой у всех подходящих пользователей.\n\n"
        f"Осталось бустов на этой неделе: <b>{remaining}</b> из 3",
        parse_mode="HTML",
        reply_markup=back_kb,
    )


@user_profile_router.callback_query(F.data == "toggle_girls_write_first")
async def toggle_girls_write_first(
    callback: CallbackQuery,
    container: Container = init_container(),
):
    service: BaseUsersService = container.resolve(BaseUsersService)
    await callback.answer()

    try:
        user = await service.get_user(telegram_id=callback.from_user.id)
    except Exception:
        await callback.message.answer("Ошибка получения профиля.")
        return

    current = bool(getattr(user, "allow_girls_write_first", False))
    new_val = not current
    await service.update_user_info_after_reg(
        telegram_id=callback.from_user.id,
        data={"allow_girls_write_first": new_val},
    )

    if new_val:
        msg = (
            "💬 <b>Девушки могут писать тебе первыми — включено!</b>\n\n"
            "Теперь девушки, которые находят твою анкету, смогут написать тебе сообщение "
            "без взаимного матча. Это увеличивает шансы познакомиться!"
        )
    else:
        msg = (
            "🔒 <b>Девушки пишут первыми — отключено.</b>\n\n"
            "Теперь переписка возможна только после взаимного лайка (матча)."
        )

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В профиль", callback_data="profile_page")]
    ])
    try:
        await callback.message.edit_text(msg, parse_mode="HTML", reply_markup=back_kb)
    except Exception:
        await callback.message.answer(msg, parse_mode="HTML", reply_markup=back_kb)
