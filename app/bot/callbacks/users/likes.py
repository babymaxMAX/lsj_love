from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from punq import Container

from app.bot.handlers.users.profile import profile
from app.bot.keyboards.inline import like_dislike_keyboard, match_keyboard, swipe_card_keyboard
from app.bot.utils.constants import match_text_message, profile_text_message
from app.bot.utils.states import MessageCompose, ReportForm
from app.domain.entities.users import UserEntity
from app.infra.repositories.base import BaseDislikesRepository
from app.logic.init import init_container
from app.logic.services.base import BaseLikesService, BaseUsersService
from app.logic.use_cases.like_action import LikeActionUseCase


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
    def __init__(self, users, use_swipe_card: bool = False):
        self.users = users
        self.current_index = 0
        self.use_swipe_card = use_swipe_card  # /match: Like, Skip, Message, Report

    def has_more_users(self):
        return self.current_index < len(self.users)

    def get_next_user(self):
        if self.has_more_users():
            user = self.users[self.current_index]
            self.current_index += 1
            return user
        return None


async def send_user_profile(callback: CallbackQuery, user: UserEntity, use_swipe_card: bool = False):
    """Отправляет профиль пользователя. use_swipe_card=True — клавиатура с Message, Report."""
    try:
        await callback.message.delete()
    except Exception:
        pass
    kb = swipe_card_keyboard(user.telegram_id) if use_swipe_card else like_dislike_keyboard(user.telegram_id)
    try:
        from app.bot.utils.notificator import _resolve_photo
        photo_raw = getattr(user, "photos", []) or []
        photo_raw = photo_raw[0] if photo_raw else (user.photo or "")
        resolved = await _resolve_photo(photo_raw, user.telegram_id) if photo_raw else None
        if resolved:
            from aiogram.types import BufferedInputFile
            photo_input = BufferedInputFile(resolved, "photo.jpg") if isinstance(resolved, bytes) else resolved
            await callback.message.answer_photo(
                photo=photo_input,
                caption=profile_text_message(user),
                reply_markup=kb,
                parse_mode="HTML",
            )
            return
    except Exception:
        pass
    try:
        await callback.message.answer_photo(
            photo=user.photo,
            caption=profile_text_message(user),
            reply_markup=kb,
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            text=profile_text_message(user),
            reply_markup=kb,
            parse_mode="HTML",
        )


async def process_next_user(callback: CallbackQuery, session: UserSession):
    next_user = session.get_next_user()
    if next_user:
        await send_user_profile(callback, next_user, use_swipe_card=session.use_swipe_card)
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
    use_case: LikeActionUseCase = container.resolve(LikeActionUseCase)
    users_service: BaseUsersService = container.resolve(BaseUsersService)

    await callback.answer()

    try:
        liked_user_id = int(callback.data[len("like_"):])
    except (ValueError, IndexError):
        await callback.message.answer("⚠️ Ошибка: неверный формат данных")
        return

    result = await use_case.execute(
        from_user_id=callback.from_user.id,
        to_user_id=liked_user_id,
        is_superlike=False,
    )

    if not result.success:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        cta_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Premium", callback_data="premium_info")],
            [InlineKeyboardButton(text="💗 Смотреть анкеты", callback_data="profile_page")],
        ])
        await callback.message.answer(
            f"⚠️ {result.error_message}",
            reply_markup=cta_kb,
        )
        return

    try:
        user_liked = await users_service.get_user(liked_user_id)
    except Exception:
        user_liked = None

    if result.is_match and user_liked:
        try:
            await callback.message.delete()
        except Exception:
            pass
        username = getattr(user_liked, "username", None)
        match_caption = match_text_message(user_liked)
        from_id = callback.from_user.id
        to_id = user_liked.telegram_id
        bot_username = ""
        try:
            from app.application.api.lifespan import get_bot_username
            from app.logic.init import init_container as _ic
            from app.settings.config import Config
            cfg = _ic().resolve(Config)
            bot_username = getattr(cfg, "bot_username", None) or get_bot_username()
        except Exception:
            pass
        kb = match_keyboard(username=username, to_user_id=from_id, matched_user_id=to_id, bot_username=bot_username)
        try:
            from app.bot.utils.notificator import _resolve_photo
            photo_raw = getattr(user_liked, "photos", []) or []
            photo_raw = photo_raw[0] if photo_raw else (getattr(user_liked, "photo", None) or "")
            resolved = await _resolve_photo(photo_raw, to_id) if photo_raw else None
            if resolved:
                from aiogram.types import BufferedInputFile
                photo_input = BufferedInputFile(resolved, "photo.jpg") if isinstance(resolved, bytes) else resolved
                await callback.message.answer_photo(
                    photo=photo_input,
                    caption=match_caption,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            else:
                await callback.message.answer(text=match_caption, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await callback.message.answer(text=match_caption, reply_markup=kb, parse_mode="HTML")
    else:
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

    try:
        disliked_user_id = int(callback.data[len("dislike_"):])
    except (ValueError, IndexError):
        disliked_user_id = None

    if disliked_user_id:
        dislikes_repo: BaseDislikesRepository = container.resolve(BaseDislikesRepository)
        await dislikes_repo.add_dislike(
            from_user=callback.from_user.id,
            to_user=disliked_user_id,
        )

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


# ─── Message (counts as like) ─────────────────────────────────────────────────

@callback_like_router.callback_query(lambda c: c.data and c.data.startswith("message_"))
async def handle_message_button(
    callback: CallbackQuery,
    state: FSMContext,
    container: Container = init_container(),
):
    """Кнопка ✍️ Message: запрос текста → like + send_icebreaker."""
    await callback.answer()
    try:
        target_id = int(callback.data[len("message_"):])
    except (ValueError, IndexError):
        return
    await state.set_state(MessageCompose.text)
    await state.update_data(message_target_id=target_id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "✍️ Напиши первое сообщение для этого человека (или /cancel чтобы отменить):",
    )


# ─── Report ───────────────────────────────────────────────────────────────────

REPORT_CATEGORIES = [
    ("spam", "Спам"),
    ("inappropriate", "Неприемлемый контент"),
    ("scam", "Мошенничество"),
    ("fake", "Фейковый профиль"),
    ("other", "Другое"),
]


@callback_like_router.callback_query(
    lambda c: c.data and c.data.startswith("report_cat_"),
)
async def handle_report_category(
    callback: CallbackQuery,
    state: FSMContext,
    container: Container = init_container(),
):
    """Выбор категории репорта → переход к вводу текста."""
    await callback.answer()
    cat = callback.data[len("report_cat_"):].strip()
    data = await state.get_data()
    target_id = data.get("report_target_id")
    if not target_id:
        await state.clear()
        return
    await state.set_state(ReportForm.text)
    await state.update_data(report_category=cat)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "📝 Опиши ситуацию (или /cancel чтобы отменить):",
    )


@callback_like_router.callback_query(
    lambda c: c.data and c.data.startswith("report_") and not c.data.startswith("report_cat_") and c.data != "report_cancel",
)
async def handle_report_button(
    callback: CallbackQuery,
    state: FSMContext,
    container: Container = init_container(),
):
    """Кнопка 🚨 Report: выбор категории → текст → запись в reports."""
    await callback.answer()
    try:
        target_id = int(callback.data[len("report_"):])
    except (ValueError, IndexError):
        return
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    btns = [
        [InlineKeyboardButton(text=label, callback_data=f"report_cat_{key}")]
        for key, label in REPORT_CATEGORIES
    ]
    btns.append([InlineKeyboardButton(text="🔙 Отмена", callback_data="report_cancel")])
    await state.set_state(ReportForm.category)
    await state.update_data(report_target_id=target_id)
    try:
        await callback.message.edit_caption(
            caption=(callback.message.caption or "") + "\n\n🚨 Выбери причину репорта:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
        )
    except Exception:
        try:
            await callback.message.edit_text(
                (callback.message.text or "") + "\n\n🚨 Выбери причину репорта:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
            )
        except Exception:
            await callback.message.answer(
                "🚨 Выбери причину репорта:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
            )


@callback_like_router.callback_query(F.data == "report_cancel")
async def handle_report_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Отменено")
    data = await state.get_data()
    session = data.get("session")
    await state.clear()
    if session:
        from app.bot.callbacks.users.likes import process_next_user
        await process_next_user(callback, session)


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
