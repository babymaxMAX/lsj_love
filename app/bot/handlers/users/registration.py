from aiogram import (
    Bot,
    F,
    Router,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from punq import Container

from app.bot.handlers.users.profile import profile
from app.bot.keyboards.reply import (
    about_skip_keyboard,
    gender_select_keyboard,
    remove_keyboard,
    user_name_keyboard,
)
from app.bot.utils.constants import user_profile_text_message
from app.bot.utils.states import UserForm
from app.domain.exceptions.base import ApplicationException
from app.infra.s3.base import BaseS3Storage
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService


registration_router = Router(
    name="Registration router",
)


async def gender_check(message):
    if message.text.lower() == "👨 мужской":
        return "Man"
    elif message.text.lower() == "👧 женский":
        return "Female"
    else:
        await message.answer(
            text="Нажми на кнопку 👇",
            reply_markup=gender_select_keyboard,
        )
        return None


@registration_router.message(UserForm.name)
async def user_set_age(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(UserForm.age)
    await message.answer(
        text="Сколько тебе лет?",
        reply_markup=remove_keyboard,
    )


@registration_router.message(UserForm.age)
async def user_set_gender(message: Message, state: FSMContext):
    if message.text.isdigit():
        age = int(message.text)
        if age < 18 or age > 99:
            await message.answer(text="Введи корректный возраст (от 18 до 99).")
            return
        await state.update_data(age=message.text)
        await state.set_state(UserForm.gender)
        await message.answer(
            text="Твой пол?",
            reply_markup=gender_select_keyboard,
        )
    else:
        await message.answer(text="Введи число!")


@registration_router.message(UserForm.gender)
async def user_set_city(message: Message, state: FSMContext):
    gender = await gender_check(message)
    if gender is not None:
        await state.update_data(gender=gender)
        await state.set_state(UserForm.city)
        await message.answer(
            text="Из какого ты города?",
            reply_markup=remove_keyboard,
        )


@registration_router.message(UserForm.city)
async def user_set_looking_for(message: Message, state: FSMContext):
    if message.text.isdigit():
        await message.answer(text="Введи название города.")
    else:
        await state.update_data(city=message.text)
        await state.set_state(UserForm.looking_for)
        await message.answer(
            text="Кого ищешь?",
            reply_markup=gender_select_keyboard,
        )


@registration_router.message(UserForm.looking_for)
async def user_set_about(message: Message, state: FSMContext):
    gender = await gender_check(message)
    if gender is not None:
        await state.update_data(looking_for=gender)
        await state.set_state(UserForm.about)
        await message.answer(
            text="Расскажи немного о себе (или нажми кнопку чтобы пропустить)",
            reply_markup=about_skip_keyboard,
        )


@registration_router.message(UserForm.about)
async def user_set_photo(
    message: Message,
    state: FSMContext,
):
    if message.text.lower() == "🪪 пропустить":
        await state.update_data(about=None)
    else:
        await state.update_data(about=message.text)

    await state.set_state(UserForm.photo)
    await message.answer(
        text="Отправь своё фото.",
        reply_markup=remove_keyboard,
    )


@registration_router.message(UserForm.photo, F.photo)
async def user_reg(
    message: Message,
    state: FSMContext,
    bot: Bot,
    container: Container = init_container(),
):
    uploader: BaseS3Storage = container.resolve(BaseS3Storage)
    service: BaseUsersService = container.resolve(BaseUsersService)
    data = await state.get_data()
    await state.clear()

    photo_file_id = message.photo[-1].file_id
    file = await bot.get_file(photo_file_id)
    file_path = file.file_path
    photo_file_stream = await bot.download_file(file_path)
    photo_file_bytes = photo_file_stream.read()

    photo_url = await uploader.upload_file(
        file=photo_file_bytes,
        file_name=f"{message.from_user.id}.png",
    )

    data["photo"] = photo_url
    data["is_active"] = True
    await service.update_user_info_after_reg(
        telegram_id=message.from_user.id,
        data=data,
    )

    await message.answer("✅ Анкета заполнена! Сейчас покажу твой профиль...")
    await profile(message)


@registration_router.message(UserForm.photo, ~F.photo)
async def user_photo_error(message: Message, state: FSMContext):
    await message.answer("Отправь фото!")


@registration_router.message(Command("form"))
async def registration_form(
    message: Message,
    state: FSMContext,
    container: Container = init_container(),
):
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        user = await service.get_user(telegram_id=message.from_user.id)

        if user.is_active:
            await message.answer(
                text="Ты уже зарегистрирован(а).",
                reply_markup=remove_keyboard,
            )
            await message.answer(text=user_profile_text_message(user=user))

        elif not message.from_user.username:
            await message.answer(
                text="Сначала установи <b><i>username</i></b> в настройках Telegram."
                "\nЗатем снова используй команду /form",
            )

        else:
            await state.set_state(UserForm.name)
            await message.answer(
                text="Начнём! Введи своё имя.",
                reply_markup=user_name_keyboard(message.from_user.first_name),
            )

    except ApplicationException:
        await message.answer(text="Сначала введи команду: <b>/start</b>")
