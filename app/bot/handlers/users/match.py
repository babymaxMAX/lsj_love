"""
/match — bot-only свайпинг (лента анкет из best_result).
/matches — список взаимных матчей.
match_start — callback от кнопки "Смотреть анкеты" (когда ENABLE_WEBAPP=False).
"""
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from motor.motor_asyncio import AsyncIOMotorClient
from punq import Container

from app.bot.callbacks.users.likes import (
    UserSession,
    process_next_user,
    send_user_profile,
)
from app.bot.handlers.users.profile import profile
from app.bot.handlers.users.registration import start_registration
from app.bot.utils.constants import profile_text_message
from app.bot.utils.states import MessageCompose, ReportForm
from app.infra.repositories.base import BaseDislikesRepository
from app.logic.init import init_container
from app.logic.services.base import BaseLikesService, BaseUsersService
from app.logic.use_cases.like_action import LikeActionUseCase
from app.settings.config import Config


match_router = Router(name="Match router")


async def _start_match_flow(update: Message | CallbackQuery, state: FSMContext, container: Container):
    """Запускает сессию свайпов из best_result."""
    users_service: BaseUsersService = container.resolve(BaseUsersService)
    likes_service: BaseLikesService = container.resolve(BaseLikesService)
    dislikes_repo: BaseDislikesRepository = container.resolve(BaseDislikesRepository)
    config: Config = container.resolve(Config)

    if not getattr(config, "enable_bot_match", True):
        if isinstance(update, CallbackQuery):
            await update.answer()
        target = update.message if isinstance(update, CallbackQuery) else update
        await target.answer("Свайпы в боте временно отключены. Используйте сайт.")
        return

    user_id = update.from_user.id

    try:
        already_liked = await likes_service.get_telegram_id_liked_from(user_id=user_id)
        already_disliked = await dislikes_repo.get_disliked_ids(user_id=user_id)
        exclude_ids = list(set(already_liked) | set(already_disliked))
        users = await users_service.get_best_result_for_user(user_id, exclude_ids=exclude_ids)
    except Exception:
        target = update.message if isinstance(update, CallbackQuery) else update
        await target.answer("Ошибка загрузки анкет. Попробуй позже.")
        return

    if isinstance(update, CallbackQuery):
        try:
            await update.message.delete()
        except Exception:
            pass
        callback = update
    else:
        callback = None

    if not users:
        target = update.message if isinstance(update, CallbackQuery) else update
        await target.answer(
            "Пока нет новых анкет 🤷\nЗагляни позже или расширь критерии поиска.",
        )
        await profile(update)
        return

    session = UserSession(list(users), use_swipe_card=True)
    await state.update_data(session=session)
    if callback:
        await process_next_user(callback, session)
    else:
        first_user = session.get_next_user()
        if first_user:
            from aiogram.types import BufferedInputFile
            from app.bot.keyboards.inline import swipe_card_keyboard
            from app.bot.utils.notificator import _resolve_photo
            kb = swipe_card_keyboard(first_user.telegram_id)
            photo_raw = getattr(first_user, "photos", []) or []
            photo_raw = photo_raw[0] if photo_raw else (getattr(first_user, "photo", None) or "")
            try:
                resolved = await _resolve_photo(photo_raw, first_user.telegram_id) if photo_raw else None
                if resolved:
                    photo_input = BufferedInputFile(resolved, "photo.jpg") if isinstance(resolved, bytes) else resolved
                    await update.answer_photo(
                        photo=photo_input,
                        caption=profile_text_message(first_user),
                        reply_markup=kb,
                        parse_mode="HTML",
                    )
                    return
            except Exception:
                pass
            try:
                await update.answer_photo(
                    photo=getattr(first_user, "photo", None),
                    caption=profile_text_message(first_user),
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            except Exception:
                await update.answer(
                    text=profile_text_message(first_user),
                    reply_markup=kb,
                    parse_mode="HTML",
                )


@match_router.message(Command("match"))
async def cmd_match(message: Message, state: FSMContext, container: Container = init_container()):
    await _start_match_flow(message, state, container)


@match_router.callback_query(F.data == "match_start")
async def callback_match_start(
    callback: CallbackQuery,
    state: FSMContext,
    container: Container = init_container(),
):
    await callback.answer()
    await _start_match_flow(callback, state, container)


@match_router.message(Command("create"))
async def cmd_create(message: Message, state: FSMContext):
    """Алиас к /form — создание/редактирование анкеты."""
    await start_registration(message, state)


@match_router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия (Message/Report)."""
    await state.clear()
    await message.answer("Отменено.")


@match_router.message(F.text, StateFilter(MessageCompose.text))
async def handle_message_compose_text(
    message: Message,
    state: FSMContext,
    container: Container = init_container(),
):
    """Пользователь ввёл текст для Message (лайк + первое сообщение)."""
    data = await state.get_data()
    target_id = data.get("message_target_id")
    await state.clear()
    if not target_id:
        return
    text = (message.text or "").strip()
    if not text or text == "/cancel":
        await message.answer("Отменено.")
        return

    use_case: LikeActionUseCase = container.resolve(LikeActionUseCase)
    users_service = container.resolve(BaseUsersService)
    result = await use_case.execute(
        from_user_id=message.from_user.id,
        to_user_id=target_id,
        is_superlike=False,
    )
    if not result.success:
        await message.answer(f"⚠️ {result.error_message}")
        return

    try:
        sender = await users_service.get_user(message.from_user.id)
        from app.bot.utils.notificator import send_icebreaker_message
        await send_icebreaker_message(target_id=target_id, message=text, sender=sender)
    except Exception:
        pass
    await message.answer("💌 Сообщение отправлено! При взаимности — матч 💕")


@match_router.message(F.text, StateFilter(ReportForm.text))
async def handle_report_text(
    message: Message,
    state: FSMContext,
    container: Container = init_container(),
):
    """Пользователь ввёл текст репорта → сохраняем в MongoDB reports."""
    data = await state.get_data()
    target_id = data.get("report_target_id")
    category = data.get("report_category", "other")
    await state.clear()
    if not target_id:
        return
    text = (message.text or "").strip()
    if text == "/cancel":
        await message.answer("Отменено.")
        return

    config: Config = container.resolve(Config)
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    col = client[config.mongodb_dating_database]["reports"]
    await col.insert_one({
        "from_user": message.from_user.id,
        "to_user": target_id,
        "category": category,
        "text": text[:1000],
        "created_at": datetime.now(timezone.utc),
        "status": "pending",
    })
    await message.answer("✅ Репорт отправлен. Спасибо за помощь в поддержании сообщества.")
    # После репорта пользователь ввёл текст — возврата к свайпам нет (Message, не CallbackQuery)


@match_router.message(Command("matches"))
async def cmd_matches(message: Message, container: Container = init_container()):
    """Список взаимных матчей."""
    likes_service: BaseLikesService = container.resolve(BaseLikesService)
    users_service: BaseUsersService = container.resolve(BaseUsersService)
    config: Config = container.resolve(Config)

    try:
        liked_by_me = set(await likes_service.get_telegram_id_liked_from(message.from_user.id))
        liked_me = set(await likes_service.get_users_ids_liked_by(message.from_user.id))
        mutual_ids = list(liked_by_me & liked_me)
    except Exception:
        await message.answer("Ошибка загрузки матчей.")
        return

    if not mutual_ids:
        await message.answer("Пока нет взаимных симпатий 💫\nСвайпай анкеты — и матчи появятся!")
        return

    users = []
    for uid in mutual_ids[:20]:
        try:
            users.append(await users_service.get_user(uid))
        except Exception:
            pass

    lines = ["💕 <b>Твои матчи:</b>\n"]
    for u in users:
        name = str(getattr(u, "name", "") or "")
        username = getattr(u, "username", None) or ""
        uid = getattr(u, "telegram_id", 0)
        if username and username.strip():
            lines.append(f"• <a href='https://t.me/{username.strip()}'>{name}</a>")
        else:
            bot_username = getattr(config, "bot_username", "") or ""
            if bot_username:
                lines.append(f"• {name} — <a href='https://t.me/{bot_username}?start=chat_{message.from_user.id}_{uid}'>Написать</a>")
            else:
                lines.append(f"• {name}")
    if len(mutual_ids) > 20:
        lines.append(f"\n<i>... и ещё {len(mutual_ids) - 20}</i>")
    await message.answer("\n".join(lines), parse_mode="HTML")
