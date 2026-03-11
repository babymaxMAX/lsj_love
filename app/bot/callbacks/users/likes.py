from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from punq import Container

from app.bot.handlers.users.profile import profile
from app.bot.keyboards.inline import like_dislike_keyboard, match_keyboard
from app.bot.utils.constants import match_text_message, profile_text_message
from app.domain.entities.users import UserEntity
from app.logic.init import init_container
from app.logic.services.base import BaseLikesService, BaseUsersService


callback_like_router = Router()


# ─── Icebreaker reply/skip handlers ──────────────────────────────────────────

@callback_like_router.callback_query(
    lambda c: c.data and c.data.startswith("icebreaker_reply_")
)
async def handle_icebreaker_reply(
    callback: CallbackQuery,
    container: Container = init_container(),
):
    """Пользователь нажал 'Ответить' на icebreaker → создаём лайк → проверяем матч."""
    await callback.answer()

    likes_service: BaseLikesService = container.resolve(BaseLikesService)
    users_service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        sender_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        return

    target_id = callback.from_user.id

    # Редактируем сообщение, убираем кнопки
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    try:
        target_user = await users_service.get_user(target_id)
        sender_user = await users_service.get_user(sender_id)
    except Exception:
        await callback.message.answer("Что-то пошло не так. Попробуй позже.")
        return

    # Создаём лайк от target к sender (если ещё нет)
    already = await likes_service.check_like_is_exists(
        from_user_id=target_id,
        to_user_id=sender_id,
    )
    if not already:
        try:
            await likes_service.create_like(
                from_user_id=target_id,
                to_user_id=sender_id,
            )
        except Exception:
            pass

    # Проверяем матч
    is_match = await likes_service.check_match(
        from_user_id=target_id,
        to_user_id=sender_id,
    )

    if is_match:
        # Уведомляем обоих о матче
        from app.bot.utils.notificator import send_match_message
        try:
            await send_match_message(to_user_id=target_id, matched_user=sender_user)
        except Exception:
            pass
        try:
            await send_match_message(to_user_id=sender_id, matched_user=target_user)
        except Exception:
            pass
    else:
        # Лайк создан, ждём ответного
        username = getattr(sender_user, "username", None)
        sender_name = getattr(sender_user, "name", "этого человека")
        text = (
            f"❤️ Ты ответил(а) на сообщение от <b>{sender_name}</b>!\n"
            f"Если он(а) тоже лайкнет тебя — это матч 💕"
        )
        if username:
            text += f"\n\n👉 <a href='https://t.me/{username}'>Написать {sender_name}</a>"
        await callback.message.answer(text)


@callback_like_router.callback_query(
    lambda c: c.data and c.data.startswith("icebreaker_skip_")
)
async def handle_icebreaker_skip(callback: CallbackQuery):
    """Пользователь нажал 'Пропустить' на icebreaker."""
    await callback.answer("Окей, пропускаем 👌")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


class UserSession:
    def __init__(self, users):
        self.users = users
        self.current_index = 0

    def has_more_users(self):
        return self.current_index < len(self.users)

    def get_next_user(self):
        if self.has_more_users():
            user = self.users[self.current_index]
            self.current_index += 1
            return user
        return None


async def send_user_profile(callback: CallbackQuery, user: UserEntity):
    """Отправляет профиль пользователя с клавиатурой лайк/дизлайк, удаляет предыдущее сообщение."""
    try:
        await callback.message.delete()
    except Exception:
        pass
    try:
        await callback.message.answer_photo(
            photo=user.photo,
            caption=profile_text_message(user),
            reply_markup=like_dislike_keyboard(user_id=user.telegram_id),
        )
    except Exception:
        await callback.message.answer(
            text=profile_text_message(user),
            reply_markup=like_dislike_keyboard(user_id=user.telegram_id),
        )


async def process_next_user(callback: CallbackQuery, session: UserSession):
    next_user = session.get_next_user()
    if next_user:
        await send_user_profile(callback, next_user)
    else:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer("Анкеты закончились 🤷‍♂️")
        await profile(callback)


@callback_like_router.callback_query(
    # Исключаем like_back_ — его обрабатывает отдельный хендлер ниже
    lambda c: c.data and c.data.startswith("like_") and not c.data.startswith("like_back_"),
)
async def handle_like_user(
    callback: CallbackQuery,
    state: FSMContext,
    container: Container = init_container(),
):
    likes_service: BaseLikesService = container.resolve(BaseLikesService)
    users_service: BaseUsersService = container.resolve(BaseUsersService)

    await callback.answer()

    try:
        liked_user_id = int(callback.data[len("like_"):])
    except (ValueError, IndexError):
        await callback.message.answer("⚠️ Ошибка: неверный формат данных")
        return

    try:
        user_liked = await users_service.get_user(liked_user_id)
        user_who_liked = await users_service.get_user(callback.from_user.id)
    except Exception:
        data = await state.get_data()
        session = data.get("session")
        if session:
            await process_next_user(callback, session)
        return

    # Проверяем: не лайкали ли мы уже этого пользователя
    already_liked = await likes_service.check_like_is_exists(
        from_user_id=user_who_liked.telegram_id,
        to_user_id=user_liked.telegram_id,
    )

    if not already_liked:
        try:
            await likes_service.create_like(
                from_user_id=user_who_liked.telegram_id,
                to_user_id=user_liked.telegram_id,
            )
        except Exception:
            pass

    # Проверяем взаимный лайк (матч)
    is_match = await likes_service.check_match(
        from_user_id=user_who_liked.telegram_id,
        to_user_id=user_liked.telegram_id,
    )

    if is_match:
        # Удаляем текущее сообщение с анкетой
        try:
            await callback.message.delete()
        except Exception:
            pass

        # Отправляем матч обоим
        username = getattr(user_liked, "username", None)
        match_caption = match_text_message(user_liked)
        try:
            await callback.message.answer_photo(
                photo=user_liked.photo,
                caption=match_caption,
                reply_markup=match_keyboard(username),
            )
        except Exception:
            await callback.message.answer(
                text=match_caption,
                reply_markup=match_keyboard(username),
            )

        # Уведомляем второго участника если он ещё не знает
        try:
            from app.bot.utils.notificator import send_match_message
            await send_match_message(
                to_user_id=user_liked.telegram_id,
                matched_user=user_who_liked,
            )
        except Exception:
            pass
    else:
        # Просто переходим к следующей анкете
        data = await state.get_data()
        session = data.get("session")
        if session:
            await process_next_user(callback, session)


@callback_like_router.callback_query(
    lambda callback_query: callback_query.data.startswith("dislike_"),
)
async def handle_dislike_user(
    callback: CallbackQuery,
    state: FSMContext,
    container: Container = init_container(),
):
    await callback.answer()

    data = await state.get_data()
    session = data.get("session")

    if session:
        await process_next_user(callback, session)


@callback_like_router.callback_query(F.data == "see_who_liked")
async def handle_see_who_liked(
    callback: CallbackQuery,
    state: FSMContext,
    container: Container = init_container(),
):
    from datetime import datetime, timezone
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    likes_service: BaseLikesService = container.resolve(BaseLikesService)
    users_service: BaseUsersService = container.resolve(BaseUsersService)

    await callback.answer()

    # Проверяем Premium-доступ
    try:
        current_user = await users_service.get_user(telegram_id=callback.from_user.id)
        pt = getattr(current_user, "premium_type", None)
        until = getattr(current_user, "premium_until", None)
        now = datetime.now(timezone.utc)
        if until and hasattr(until, "tzinfo") and until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        is_premium = bool(pt and until and now < until)
    except Exception:
        is_premium = False

    if not is_premium:
        gate_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Получить Premium", callback_data="premium_info")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_page")],
        ])
        try:
            await callback.message.edit_text(
                "🔒 <b>Кто тебя лайкнул</b> — функция Premium\n\n"
                "С подпиской ты видишь всех, кому понравился(ась), "
                "и можешь ответить взаимностью первым.\n\n"
                "<i>Бесплатно: получаешь только уведомление «кто-то поставил лайк».</i>",
                parse_mode="HTML",
                reply_markup=gate_kb,
            )
        except Exception:
            await callback.message.answer(
                "🔒 Эта функция доступна с подпиской <b>Premium</b>.",
                parse_mode="HTML",
                reply_markup=gate_kb,
            )
        return

    try:
        await callback.message.delete()
    except Exception:
        pass

    likes = await likes_service.get_users_ids_liked_by(callback.from_user.id)

    if likes:
        # Фильтруем тех, кого мы уже лайкали (уже матч)
        pending = []
        for uid in likes:
            already = await likes_service.check_like_is_exists(
                from_user_id=callback.from_user.id,
                to_user_id=uid,
            )
            if not already:
                pending.append(uid)

        if not pending:
            await callback.message.answer("Нет новых лайков от других пользователей 🤷")
            await profile(callback)
            return

        liked_users = []
        for user_id in pending:
            try:
                liked_users.append(await users_service.get_user(user_id))
            except Exception:
                pass

        if not liked_users:
            await callback.message.answer("Нет новых лайков 🤷")
            await profile(callback)
            return

        session = UserSession(liked_users)
        await state.update_data(session=session)
        await process_next_user(callback, session)
    else:
        await callback.message.answer("Тебя ещё никто не лайкнул 🙈\nСвайпай анкеты — и лайки придут!")
        await profile(callback)


@callback_like_router.callback_query(lambda c: c.data and c.data.startswith("like_back_"))
async def handle_like_back(
    callback: CallbackQuery,
    container: Container = init_container(),
):
    """Ответный лайк из уведомления — доступен Premium и VIP."""
    from datetime import datetime, timezone
    await callback.answer()

    users_service: BaseUsersService = container.resolve(BaseUsersService)
    likes_service: BaseLikesService = container.resolve(BaseLikesService)

    try:
        current_user = await users_service.get_user(telegram_id=callback.from_user.id)
        pt    = getattr(current_user, "premium_type", None)
        until = getattr(current_user, "premium_until", None)
        if until and hasattr(until, "tzinfo") and until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        is_premium = bool(pt in ("vip", "premium") and until and datetime.now(timezone.utc) < until)
    except Exception:
        is_premium = False

    if not is_premium:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        gate_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Получить Premium", callback_data="premium_info")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_page")],
        ])
        try:
            await callback.message.edit_text(
                "💎 <b>Ответ на лайк — функция Premium</b>\n\n"
                "Оформи подписку <b>Premium</b> или <b>VIP</b>, чтобы видеть кто тебя лайкает и отвечать взаимностью.",
                parse_mode="HTML", reply_markup=gate_kb,
            )
        except Exception:
            await callback.message.answer(
                "💎 Эта функция доступна только с подпиской <b>Premium</b> или <b>VIP</b>.",
                parse_mode="HTML", reply_markup=gate_kb,
            )
        return

    try:
        liker_id = int(callback.data.split("like_back_")[1])
    except (ValueError, IndexError):
        return

    from_id = callback.from_user.id
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    try:
        await likes_service.create_like(from_user_id=from_id, to_user_id=liker_id)
    except Exception:
        pass

    try:
        is_match = await likes_service.check_match(from_user_id=from_id, to_user_id=liker_id)
        if is_match:
            from app.bot.utils.notificator import send_match_message
            liker_user = await users_service.get_user(telegram_id=liker_id)
            await send_match_message(to_user_id=from_id, matched_user=liker_user, recipient_id=from_id)
            await send_match_message(to_user_id=liker_id, matched_user=current_user, recipient_id=liker_id)
        else:
            await callback.message.answer("💗 Лайк отправлен! Ждём взаимности...")
    except Exception:
        await callback.message.answer("💗 Лайк отправлен!")
