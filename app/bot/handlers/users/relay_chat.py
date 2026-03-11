"""
Relay-чат: переписка через бота для матчей без username.
Пользователь пишет боту, бот пересылает сообщение второму участнику матча.
"""
import logging
from aiogram import F, Router
from aiogram.filters import BaseFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from punq import Container

from app.domain.exceptions.base import ApplicationException
from app.logic.init import init_container
from app.logic.services.base import BaseLikesService, BaseUsersService

logger = logging.getLogger(__name__)

relay_router = Router(name="Relay chat")


class RelayStates(StatesGroup):
    waiting_message = State()
    waiting_reply = State()


def _relay_reply_kb(sender_id: int, target_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✍️ Ответить",
            callback_data=f"relay_reply_{sender_id}_{target_id}",
        )],
    ])


def _check_match(service: BaseLikesService, user_a: int, user_b: int) -> bool:
    """Проверяет взаимный лайк."""
    try:
        return service.check_match(from_user_id=user_a, to_user_id=user_b)
    except Exception:
        return False


class RelayStartFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        text = message.text or ""
        parts = text.split(maxsplit=1)
        return len(parts) > 1 and parts[1].strip().startswith("chat_")


@relay_router.message(CommandStart(), RelayStartFilter())
async def relay_start(message: Message, state: FSMContext, container: Container = init_container()):
    """Обработка /start chat_SENDER_TARGET — начало relay-чата."""
    parts = message.text.split(maxsplit=1)
    arg = parts[1].strip()

    try:
        ids = arg[5:].split("_")  # chat_123_456 -> [123, 456]
        if len(ids) != 2:
            return
        sender_id = int(ids[0])
        target_id = int(ids[1])
    except (ValueError, IndexError):
        return

    my_id = message.from_user.id
    if my_id != sender_id and my_id != target_id:
        await message.answer("Эта ссылка не для тебя.")
        return

    service: BaseLikesService = container.resolve(BaseLikesService)
    users_service: BaseUsersService = container.resolve(BaseUsersService)

    if not _check_match(service, sender_id, target_id):
        await message.answer("❌ Сначала нужна взаимная симпатия. Свайпай анкеты!")
        return

    try:
        other_user = await users_service.get_user(telegram_id=target_id if my_id == sender_id else sender_id)
        other_name = getattr(other_user, "name", None) or "Собеседник"
    except ApplicationException:
        other_name = "Собеседник"

    await state.clear()
    await state.set_state(RelayStates.waiting_message)
    await state.update_data(
        my_id=my_id,
        sender_id=sender_id,
        target_id=target_id,
        other_name=str(other_name),
    )
    await message.answer(
        f"💬 <b>Чат с {other_name}</b>\n\nНапиши сообщение — я перешлю его.",
        parse_mode="HTML",
    )


@relay_router.message(RelayStates.waiting_message, F.text)
async def relay_send_message(message: Message, state: FSMContext, container: Container = init_container()):
    """Отправка сообщения второму участнику."""
    data = await state.get_data()
    sender_id = data.get("sender_id")
    target_id = data.get("target_id")
    my_id = data.get("my_id")
    other_name = data.get("other_name", "Собеседник")

    recipient_id = target_id if my_id == sender_id else sender_id
    sender_name = "Ты"  # для получателя показываем "от кого"
    try:
        users_service: BaseUsersService = container.resolve(BaseUsersService)
        sender_user = await users_service.get_user(telegram_id=my_id)
        sender_name = getattr(sender_user, "name", None) or "Собеседник"
    except Exception:
        pass

    text = (message.text or "").strip()
    if not text or len(text) > 4000:
        await message.answer("Сообщение должно быть от 1 до 4000 символов.")
        return

    await state.update_data(last_recipient=recipient_id)
    await state.set_state(RelayStates.waiting_message)

    try:
        kb = _relay_reply_kb(sender_id, target_id)
        await message.bot.send_message(
            chat_id=recipient_id,
            text=f"💌 <b>{sender_name}</b> пишет:\n\n<i>{text}</i>",
            parse_mode="HTML",
            reply_markup=kb,
        )
        await message.answer("✅ Сообщение отправлено!")
    except Exception as e:
        logger.warning(f"Relay send failed: {e}")
        await message.answer("Не удалось отправить. Возможно, собеседник заблокировал бота.")


@relay_router.callback_query(F.data.startswith("relay_reply_"))
async def relay_reply_callback(callback: CallbackQuery, state: FSMContext, container: Container = init_container()):
    """Кнопка 'Ответить' — входим в режим ввода ответа."""
    try:
        parts = callback.data.split("_")
        if len(parts) != 4:
            return
        sender_id = int(parts[2])
        target_id = int(parts[3])
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    my_id = callback.from_user.id
    if my_id != sender_id and my_id != target_id:
        await callback.answer("Эта кнопка не для тебя")
        return

    service: BaseLikesService = container.resolve(BaseLikesService)
    if not _check_match(service, sender_id, target_id):
        await callback.answer("Матч больше не активен")
        return

    users_service: BaseUsersService = container.resolve(BaseUsersService)
    try:
        other = await users_service.get_user(telegram_id=target_id if my_id == sender_id else sender_id)
        other_name = getattr(other, "name", None) or "Собеседник"
    except Exception:
        other_name = "Собеседник"

    await state.clear()
    await state.set_state(RelayStates.waiting_message)
    await state.update_data(
        my_id=my_id,
        sender_id=sender_id,
        target_id=target_id,
        other_name=str(other_name),
    )
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"💬 <b>Ответ {other_name}</b>\n\nНапиши сообщение:",
        parse_mode="HTML",
    )
    await callback.answer()
