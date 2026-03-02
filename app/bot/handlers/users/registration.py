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
from app.bot.utils.moderation import check_image_safe
from app.bot.utils.states import UserForm
from app.domain.exceptions.base import ApplicationException
from app.infra.s3.base import BaseS3Storage
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService
from app.settings.config import Config


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


async def start_registration(message: Message, state: FSMContext):
    """Запускает форму регистрации — вызывается из /start."""
    await state.set_state(UserForm.name)
    await message.answer(
        text=f"Отлично, <b>{message.from_user.first_name}</b>! Давай заполним анкету.\n\n"
             f"Введи своё имя или нажми кнопку ниже:",
        reply_markup=user_name_keyboard(message.from_user.first_name),
        parse_mode="HTML",
    )


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
        await message.answer(text="Введи число — сколько тебе лет?")


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
            text="Расскажи немного о себе (или нажми «Пропустить»):",
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
        text="📸 Отправь своё фото:",
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
    config: Config = container.resolve(Config)

    # Получаем файл из Telegram
    photo_file_id = message.photo[-1].file_id
    file = await bot.get_file(photo_file_id)
    file_path = file.file_path
    photo_file_stream = await bot.download_file(file_path)
    photo_file_bytes = photo_file_stream.read()

    # Модерация: проверяем фото на 18+ ПЕРЕД сохранением состояния
    try:
        is_safe, reason = await check_image_safe(photo_file_bytes, config.openai_api_key)
        if not is_safe:
            # state НЕ сбрасываем — пользователь остаётся на шаге загрузки фото
            await message.answer(
                f"🚫 <b>Фото отклонено модерацией</b>\n\n"
                f"{reason}\n\n"
                f"Отправь другое фото — портрет или фото в полный рост.",
                parse_mode="HTML",
            )
            return
    except Exception as e:
        import logging as _log
        _log.getLogger(__name__).warning(f"Registration moderation check failed: {e}")

    # Фото прошло проверку — сохраняем данные
    data = await state.get_data()
    await state.clear()

    # Загружаем в S3 (для веб-приложения)
    s3_key = f"{message.from_user.id}_0.png"
    try:
        await uploader.upload_file(
            file=photo_file_bytes,
            file_name=s3_key,
        )
        # Сохраняем S3-ключ в массиве photos[] для Mini App
        data["photos"] = [s3_key]
    except Exception:
        pass  # S3 upload failure is non-critical

    # Храним Telegram file_id — Telegram его всегда знает и быстро отдаёт
    data["photo"] = photo_file_id
    data["is_active"] = True
    await service.update_user_info_after_reg(
        telegram_id=message.from_user.id,
        data=data,
    )

    await message.answer("✅ Анкета заполнена! Показываю твой профиль...")

    # Специальное приветствие для девушек — рассказываем об их бесплатных преимуществах
    registered_gender = str(data.get("gender", "") or "").lower()
    if registered_gender in ("female", "женский"):
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
        from app.settings.config import Config
        _config: Config = container.resolve(Config)
        app_url = f"{_config.front_end_url}/users/{message.from_user.id}"
        girl_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="💕 Открыть приложение",
                web_app=WebAppInfo(url=app_url),
            )],
        ])
        await message.answer(
            text=(
                "🎁 <b>Добро пожаловать, красавица!</b>\n\n"
                "В LSJLove у девушек особые привилегии — <b>абсолютно бесплатно</b>:\n\n"
                "❤️ <b>Безлимитные лайки</b>\n"
                "Ставь столько лайков, сколько хочешь — без ограничений навсегда.\n\n"
                "👁 <b>Кто тебя лайкнул</b>\n"
                "Видишь всех, кому ты понравилась — ещё до взаимного матча.\n\n"
                "✉️ <b>Написать первой</b>\n"
                "Если парень включил опцию «Девушки пишут первыми» — ты можешь написать ему сразу, без матча.\n\n"
                "Всё это <b>без подписки</b> — только для девушек! 💕"
            ),
            parse_mode="HTML",
            reply_markup=girl_kb,
        )

    await profile(message)


@registration_router.message(UserForm.photo, ~F.photo)
async def user_photo_error(message: Message, state: FSMContext):
    await message.answer("📸 Отправь именно фотографию!")


@registration_router.message(Command("form"))
async def registration_form(
    message: Message,
    state: FSMContext,
    container: Container = init_container(),
):
    """Команда /form оставлена для совместимости, но сейчас регистрация стартует из /start."""
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        user = await service.get_user(telegram_id=message.from_user.id)

        if user.is_active:
            await profile(message)
        elif not message.from_user.username:
            await message.answer(
                text="Сначала установи <b>username</b> в настройках Telegram, затем напиши /start",
                parse_mode="HTML",
            )
        else:
            await start_registration(message, state)

    except ApplicationException:
        await message.answer(text="Сначала напиши /start")
