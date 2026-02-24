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
    lambda callback_query: callback_query.data.startswith("like_"),
)
async def handle_like_user(
    callback: CallbackQuery,
    state: FSMContext,
    container: Container = init_container(),
):
    likes_service: BaseLikesService = container.resolve(BaseLikesService)
    users_service: BaseUsersService = container.resolve(BaseUsersService)

    await callback.answer()

    liked_user_id = int(callback.data.split("_")[1])

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
    likes_service: BaseLikesService = container.resolve(BaseLikesService)
    users_service: BaseUsersService = container.resolve(BaseUsersService)

    await callback.answer()

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
