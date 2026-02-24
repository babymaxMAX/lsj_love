from aiogram import (
    F,
    Router,
)
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.keyboards.inline import (
    about_confirm_keyboard,
    photo_confirm_keyboard,
    profile_edit_keyboard,
    re_registration_confirm_keyboard,
)
from app.bot.keyboards.reply import (
    about_skip_keyboard,
    user_name_keyboard,
)
from app.bot.utils.states import (
    UserAboutUpdate,
    UserForm,
    UserPhotoUpdate,
)


callback_profile_router = Router()


@callback_profile_router.callback_query(F.data == "profile_edit")
async def profile_edit(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        text=(
            "Что хочешь изменить?\n\n"
            "1️⃣ — Вернуться к профилю\n"
            "2️⃣ — Заполнить анкету заново\n"
            "3️⃣ — Сменить фото\n"
            "4️⃣ — Изменить текст «О себе»"
        ),
        reply_markup=profile_edit_keyboard(),
    )


@callback_profile_router.callback_query(F.data == "form")
async def re_registration_profile(callback: CallbackQuery):
    await callback.message.edit_text(
        text="Ты уверен(а), что хочешь заполнить анкету заново?\nВсе данные будут перезаписаны.",
        reply_markup=re_registration_confirm_keyboard(),
    )


@callback_profile_router.callback_query(F.data == "form_confirm")
async def form_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserForm.name)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        text="Хорошо! Введи своё имя:",
        reply_markup=user_name_keyboard(callback.from_user.first_name),
    )


@callback_profile_router.callback_query(F.data == "photo_edit")
async def photo_profile(callback: CallbackQuery):
    await callback.message.edit_text(
        text="Хочешь сменить своё фото?",
        reply_markup=photo_confirm_keyboard(),
    )


@callback_profile_router.callback_query(F.data == "photo_confirm")
async def photo_edit(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await state.set_state(UserPhotoUpdate.photo)
    await callback.message.answer(text="📸 Отправь новое фото для профиля:")


@callback_profile_router.callback_query(F.data == "about_edit")
async def about_edit(callback: CallbackQuery):
    await callback.message.edit_text(
        text="Хочешь изменить раздел «О себе»?",
        reply_markup=about_confirm_keyboard(),
    )


@callback_profile_router.callback_query(F.data == "about_confirm")
async def about_edit_confirm(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserAboutUpdate.about)
    await callback.message.delete()
    await callback.message.answer(
        text="✍️ Расскажи немного о себе (или нажми «Пропустить» чтобы очистить):",
        reply_markup=about_skip_keyboard,
    )
