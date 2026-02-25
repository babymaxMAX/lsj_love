from aiogram import (
    Bot,
    F,
    Router,
)
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from punq import Container

from app.bot.handlers.users.profile import profile
from app.bot.keyboards.reply import (
    about_skip_keyboard,
    remove_keyboard,
)
from app.bot.utils.states import (
    UserAboutUpdate,
    UserPhotoUpdate,
)
from app.domain.exceptions.base import ApplicationException
from app.domain.values.users import AboutText
from app.infra.s3.base import BaseS3Storage
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService
from app.settings.config import Config


profile_edit_router = Router()


@profile_edit_router.message(UserAboutUpdate.about)
async def about_edit_state(
    message: Message,
    state: FSMContext,
    container: Container = init_container(),
):
    service: BaseUsersService = container.resolve(BaseUsersService)
    try:
        if message.text and message.text.lower() == "🪪 пропустить":
            about = AboutText(None)
        else:
            about = AboutText(message.text)

        await state.clear()
        await message.answer(
            "✅ Раздел «О себе» обновлён!",
            reply_markup=remove_keyboard,
        )
        await service.update_user_about_info(
            telegram_id=message.from_user.id,
            about=about,
        )
        await profile(message)
    except ApplicationException as exception:
        await message.answer(
            text=f"{exception.message}\nВведи текст снова.",
            reply_markup=about_skip_keyboard,
        )


@profile_edit_router.message(UserPhotoUpdate.photo, F.photo)
async def photo_edit(
    message: Message,
    state: FSMContext,
    bot: Bot,
    container: Container = init_container(),
):
    uploader: BaseS3Storage = container.resolve(BaseS3Storage)
    service: BaseUsersService = container.resolve(BaseUsersService)
    # Не сбрасываем state до проверки модерации — иначе при отклонении
    # пользователь потеряет возможность отправить следующее фото

    # Получаем file_id из Telegram (надёжнее чем S3 URL)
    photo_file_id = message.photo[-1].file_id
    file = await bot.get_file(photo_file_id)
    file_path = file.file_path
    photo_file_stream = await bot.download_file(file_path)
    photo_file_bytes = photo_file_stream.read()

    # Модерация: проверяем фото на 18+
    try:
        from app.bot.utils.moderation import check_image_safe
        config: Config = container.resolve(Config)
        is_safe, reason = await check_image_safe(photo_file_bytes, config.openai_api_key)
        if not is_safe:
            # state НЕ сбрасываем — пользователь остаётся в режиме загрузки фото
            await message.answer(
                f"🚫 <b>Фото отклонено модерацией</b>\n\n"
                f"{reason}\n\n"
                f"Отправь другое фото — портрет или фото в полный рост.",
                parse_mode="HTML",
            )
            return
    except Exception as e:
        import logging as _log
        _log.getLogger(__name__).warning(f"Bot moderation check failed: {e}")

    # Фото прошло проверку — теперь сбрасываем состояние
    await state.clear()

    uid = message.from_user.id
    # S3-ключ в формате photos[]: {uid}_0.png — совпадает с Mini App
    s3_key = f"{uid}_0.png"

    # Загружаем в S3 под стандартным ключом photos[0]
    s3_ok = False
    try:
        await uploader.upload_file(file=photo_file_bytes, file_name=s3_key)
        s3_ok = True
    except Exception:
        pass

    # Обновляем базу: photo (file_id для бота) + photos[0] (S3 ключ для Mini App)
    try:
        user = await service.get_user(telegram_id=uid)
        photos = getattr(user, "photos", []) or []

        if s3_ok:
            if photos:
                # Чистим лайки старого фото[0] перед заменой
                try:
                    from app.infra.repositories.mongo import MongoDBPhotoLikesRepository
                    likes_repo: MongoDBPhotoLikesRepository = container.resolve(MongoDBPhotoLikesRepository)
                    await likes_repo.delete_likes_for_photo(owner_id=uid, photo_index=0)
                except Exception:
                    pass
                # Заменяем первый слот (photos[0])
                await service.replace_photo(telegram_id=uid, index=0, s3_key=s3_key)
            else:
                # Массив пустой — добавляем как первый элемент
                await service.add_photo(telegram_id=uid, s3_key=s3_key)

        # Всегда сохраняем file_id в поле photo (fallback для бота)
        await service.update_user_info_after_reg(
            telegram_id=uid,
            data={"photo": photo_file_id},
        )
    except Exception as e:
        import logging as _log
        _log.getLogger(__name__).warning(f"Photo DB update failed: {e}")
        # Fallback: сохраняем хотя бы file_id
        await service.update_user_info_after_reg(
            telegram_id=uid,
            data={"photo": photo_file_id},
        )

    await message.answer("✅ Фото обновлено!", reply_markup=remove_keyboard)
    await profile(message)


@profile_edit_router.message(UserPhotoUpdate.photo, ~F.photo)
async def user_photo_error(message: Message):
    await message.answer("📸 Отправь именно фотографию!")
