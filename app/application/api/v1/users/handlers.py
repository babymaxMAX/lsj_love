import aiohttp
import base64
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.routing import APIRouter
from pydantic import BaseModel

from punq import Container

from app.application.api.schemas import ErrorSchema
from app.application.api.v1.users.filters import GetUsersFilters
from app.application.api.v1.users.schemas import (
    GetUsersFromResponseSchema,
    GetUsersResponseSchema,
    UserDetailSchema,
)
from app.domain.exceptions.base import ApplicationException
from app.infra.s3.base import BaseS3Storage
from app.logic.init import init_container
from app.logic.services.base import (
    BaseLikesService,
    BaseUsersService,
)
from app.settings.config import Config


_EXT_MAP = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "video/mp4": "mp4",
    "video/quicktime": "mov",
    "video/webm": "webm",
    "video/avi": "avi",
}


class AddPhotoRequest(BaseModel):
    image_base64: str       # Raw base64 without data: prefix
    media_type: str = "image/jpeg"  # MIME type of the file
    replace_index: int | None = None  # If set, replace at this index


class PhotosResponse(BaseModel):
    photos: list[str]


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    about: Optional[str] = None


router = APIRouter(
    prefix="/users",
    tags=["User"],
)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    description="Get all users list.",
    responses={
        status.HTTP_200_OK: {"model": GetUsersResponseSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def get_all_users_handler(
    filters: GetUsersFilters = Depends(),
    container: Container = Depends(init_container),
) -> GetUsersResponseSchema:
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        users, count = await service.get_all_users(filters=filters.to_infra())
    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    return GetUsersResponseSchema(
        count=count,
        limit=filters.limit,
        offset=filters.offset,
        items=[UserDetailSchema.from_entity(user) for user in users],
    )


async def _serve_photo_from_s3(s3_key: str, uploader: BaseS3Storage):
    """Возвращает фото из S3 через presigned URL."""
    try:
        url = await uploader.upload_file.__func__  # Получаем presigned URL
    except Exception:
        pass
    # Генерируем presigned URL через get_client напрямую
    try:
        async with uploader.get_client() as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": uploader.bucket_name, "Key": s3_key},
                ExpiresIn=3600,
            )
            return RedirectResponse(url=url)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found in S3")


@router.get(
    "/{user_id}/photo/{index}",
    status_code=status.HTTP_302_FOUND,
    include_in_schema=False,
)
async def get_user_photo_by_index(
    user_id: int,
    index: int,
    container: Container = Depends(init_container),
):
    """Возвращает фото пользователя по индексу из массива photos[]."""
    service: BaseUsersService = container.resolve(BaseUsersService)
    uploader: BaseS3Storage = container.resolve(BaseS3Storage)

    try:
        photos = await service.get_photos(telegram_id=user_id)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not photos or index >= len(photos) or index < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    s3_key = photos[index]
    try:
        async with uploader.get_client() as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": uploader.bucket_name, "Key": s3_key},
                ExpiresIn=3600,
            )
            return RedirectResponse(url=url)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found in S3")


@router.get(
    "/{user_id}/photo",
    status_code=status.HTTP_302_FOUND,
    description="Get user photo (main, index 0 or legacy Telegram file_id).",
    include_in_schema=False,
)
async def get_user_photo(
    user_id: int,
    container: Container = Depends(init_container),
):
    service: BaseUsersService = container.resolve(BaseUsersService)
    config: Config = container.resolve(Config)
    uploader: BaseS3Storage = container.resolve(BaseS3Storage)

    try:
        user = await service.get_user(telegram_id=user_id)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Сначала пробуем photos[] (новый формат S3 ключей)
    photos = getattr(user, "photos", []) or []
    if photos:
        s3_key = photos[0]
        try:
            async with uploader.get_client() as client:
                url = await client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": uploader.bucket_name, "Key": s3_key},
                    ExpiresIn=3600,
                )
                return RedirectResponse(url=url)
        except Exception:
            pass

    # Фолбэк на старый photo (Telegram file_id или HTTP URL)
    photo = user.photo
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No photo")

    if photo.startswith("http"):
        return RedirectResponse(url=photo)

    # Это Telegram file_id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.telegram.org/bot{config.token}/getFile",
                params={"file_id": photo},
            ) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
                file_path = data["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{config.token}/{file_path}"
                return RedirectResponse(url=file_url)
    except aiohttp.ClientError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram API error")


@router.post(
    "/{user_id}/photos",
    status_code=status.HTTP_200_OK,
)
async def add_user_photo(
    user_id: int,
    body: AddPhotoRequest,
    container: Container = Depends(init_container),
) -> PhotosResponse:
    """Загружает новое фото в S3 и добавляет в массив photos[] пользователя."""
    service: BaseUsersService = container.resolve(BaseUsersService)
    uploader: BaseS3Storage = container.resolve(BaseS3Storage)

    # Проверяем существование пользователя
    try:
        user = await service.get_user(telegram_id=user_id)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current_photos = getattr(user, "photos", []) or []
    ext = _EXT_MAP.get(body.media_type, "jpg")
    is_replace = body.replace_index is not None

    if is_replace:
        idx = body.replace_index
        if idx < 0 or idx >= len(current_photos):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Неверный индекс для замены"},
            )
    else:
        if len(current_photos) >= 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Максимум 6 фото/видео"},
            )
        idx = len(current_photos)

    # Декодируем base64
    try:
        file_bytes = base64.b64decode(body.image_base64)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Неверный формат base64"},
        )

    # Модерация: проверяем фото на 18+ (только для изображений, не для видео)
    if not body.media_type.startswith("video/"):
        try:
            from app.bot.utils.moderation import check_image_safe
            config: Config = container.resolve(Config)
            is_safe, reason = await check_image_safe(file_bytes, config.openai_api_key)
            if not is_safe:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error": reason},
                )
        except HTTPException:
            raise
        except Exception as e:
            import logging as _log
            _log.getLogger(__name__).warning(f"Moderation check failed: {e}")

    # Загружаем в S3
    s3_key = f"{user_id}_{idx}.{ext}"
    try:
        await uploader.upload_file(file=file_bytes, file_name=s3_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": f"Ошибка загрузки в S3: {str(e)}"},
        )

    if is_replace:
        # Удаляем лайки старого фото перед заменой
        try:
            from app.infra.repositories.mongo import MongoDBPhotoLikesRepository
            likes_repo: MongoDBPhotoLikesRepository = container.resolve(MongoDBPhotoLikesRepository)
            deleted = await likes_repo.delete_likes_for_photo(owner_id=user_id, photo_index=idx)
            if deleted:
                import logging as _log
                _log.getLogger(__name__).info(f"Cleared {deleted} likes for photo {user_id}[{idx}] on replace")
        except Exception as e:
            import logging as _log
            _log.getLogger(__name__).warning(f"Failed to clear photo likes on replace: {e}")
        photos = await service.replace_photo(telegram_id=user_id, index=idx, s3_key=s3_key)
    else:
        photos = await service.add_photo(telegram_id=user_id, s3_key=s3_key)
        # Первое фото — обновляем photo для обратной совместимости
        if idx == 0:
            await service.update_user_info_after_reg(
                telegram_id=user_id,
                data={"photo": s3_key},
            )

    photos_urls = [f"/api/v1/users/{user_id}/photo/{i}" for i in range(len(photos))]
    return PhotosResponse(photos=photos_urls)


@router.post(
    "/{user_id}/photos/upload",
    status_code=status.HTTP_200_OK,
    description="Загрузка фото/видео через multipart form (для больших файлов без base64 overhead).",
)
async def upload_user_media_multipart(
    user_id: int,
    file: UploadFile = File(...),
    replace_index: Optional[int] = Form(None),
    container: Container = Depends(init_container),
) -> PhotosResponse:
    """Принимает файл через multipart/form-data. Поддерживает видео до 60 МБ."""
    service: BaseUsersService = container.resolve(BaseUsersService)
    uploader: BaseS3Storage = container.resolve(BaseS3Storage)

    try:
        user = await service.get_user(telegram_id=user_id)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current_photos = getattr(user, "photos", []) or []
    media_type = file.content_type or "application/octet-stream"
    ext = _EXT_MAP.get(media_type, "jpg")

    is_replace = replace_index is not None
    if is_replace:
        idx = replace_index
        if idx < 0 or idx >= len(current_photos):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Неверный индекс для замены"},
            )
    else:
        if len(current_photos) >= 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Максимум 6 фото/видео"},
            )
        idx = len(current_photos)

    # Читаем файл
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Ошибка чтения файла: {str(e)}"},
        )

    # Модерация: проверяем изображение на 18+ (видео не проверяем)
    if not media_type.startswith("video/"):
        try:
            from app.bot.utils.moderation import check_image_safe
            config: Config = container.resolve(Config)
            is_safe, reason = await check_image_safe(file_bytes, config.openai_api_key)
            if not is_safe:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error": reason},
                )
        except HTTPException:
            raise
        except Exception as e:
            import logging as _log
            _log.getLogger(__name__).warning(f"Moderation check failed: {e}")

    # Загружаем в S3
    s3_key = f"{user_id}_{idx}.{ext}"
    try:
        await uploader.upload_file(file=file_bytes, file_name=s3_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": f"Ошибка загрузки в S3: {str(e)}"},
        )

    if is_replace:
        # Удаляем лайки старого фото перед заменой
        try:
            from app.infra.repositories.mongo import MongoDBPhotoLikesRepository
            likes_repo: MongoDBPhotoLikesRepository = container.resolve(MongoDBPhotoLikesRepository)
            await likes_repo.delete_likes_for_photo(owner_id=user_id, photo_index=idx)
        except Exception as e:
            import logging as _log
            _log.getLogger(__name__).warning(f"Failed to clear photo likes on multipart replace: {e}")
        photos = await service.replace_photo(telegram_id=user_id, index=idx, s3_key=s3_key)
    else:
        photos = await service.add_photo(telegram_id=user_id, s3_key=s3_key)
        if idx == 0:
            await service.update_user_info_after_reg(
                telegram_id=user_id,
                data={"photo": s3_key},
            )

    photos_urls = [f"/api/v1/users/{user_id}/photo/{i}" for i in range(len(photos))]
    return PhotosResponse(photos=photos_urls)


@router.delete(
    "/{user_id}/photos/{index}",
    status_code=status.HTTP_200_OK,
)
async def delete_user_photo(
    user_id: int,
    index: int,
    container: Container = Depends(init_container),
) -> PhotosResponse:
    """Удаляет фото по индексу из массива photos[] пользователя."""
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        await service.get_user(telegram_id=user_id)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Удаляем лайки удаляемого фото
    try:
        from app.infra.repositories.mongo import MongoDBPhotoLikesRepository
        likes_repo: MongoDBPhotoLikesRepository = container.resolve(MongoDBPhotoLikesRepository)
        await likes_repo.delete_likes_for_photo(owner_id=user_id, photo_index=index)
    except Exception as e:
        import logging as _log
        _log.getLogger(__name__).warning(f"Failed to clear photo likes on delete: {e}")

    photos = await service.remove_photo(telegram_id=user_id, index=index)
    photos_urls = [f"/api/v1/users/{user_id}/photo/{i}" for i in range(len(photos))]
    return PhotosResponse(photos=photos_urls)


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Get information about the users.",
    responses={
        status.HTTP_200_OK: {"model": UserDetailSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def get_user_handler(
    user_id: int,
    container: Container = Depends(init_container),
) -> UserDetailSchema:
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        user = await service.get_user(telegram_id=user_id)
    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    return UserDetailSchema.from_entity(user)


@router.get(
    "/best_result/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Get best result for user (excludes already-liked profiles).",
    responses={
        status.HTTP_200_OK: {"model": GetUsersFromResponseSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def get_users_best_result(
    user_id: int,
    container: Container = Depends(init_container),
) -> GetUsersFromResponseSchema:
    service_users: BaseUsersService = container.resolve(BaseUsersService)
    service_likes: BaseLikesService = container.resolve(BaseLikesService)

    try:
        already_liked = await service_likes.get_telegram_id_liked_from(user_id=user_id)
        users = await service_users.get_best_result_for_user(user_id, exclude_ids=already_liked)
    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    return GetUsersFromResponseSchema(
        items=[UserDetailSchema.from_entity(user) for user in users],
    )


@router.get(
    "/from/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Get all users that the user liked.",
    responses={
        status.HTTP_200_OK: {"model": GetUsersFromResponseSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def get_users_liked_from(
    user_id: int,
    container: Container = Depends(init_container),
) -> GetUsersFromResponseSchema:
    service_likes: BaseLikesService = container.resolve(BaseLikesService)
    service_users: BaseUsersService = container.resolve(BaseUsersService)

    try:
        telegram_ids = await service_likes.get_telegram_id_liked_from(
            user_id=user_id,
        )
        users = await service_users.get_users_liked_from(users_list=telegram_ids)
    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    return GetUsersFromResponseSchema(
        items=[UserDetailSchema.from_entity(user) for user in users],
    )


@router.get(
    "/by/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Get all users that liked the user (Premium required).",
    responses={
        status.HTTP_200_OK: {"model": GetUsersFromResponseSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
        status.HTTP_403_FORBIDDEN: {"model": ErrorSchema},
    },
)
async def get_users_liked_by(
    user_id: int,
    container: Container = Depends(init_container),
) -> GetUsersFromResponseSchema:
    from datetime import datetime, timezone
    service_likes: BaseLikesService = container.resolve(BaseLikesService)
    service_users: BaseUsersService = container.resolve(BaseUsersService)

    # Premium gate for "who liked you" — женщины видят бесплатно
    try:
        requesting_user = await service_users.get_user(telegram_id=user_id)
        gender = str(getattr(requesting_user, "gender", "") or "").lower()
        is_female = gender in ("female", "женский")
        pt = getattr(requesting_user, "premium_type", None)
        until = getattr(requesting_user, "premium_until", None)
        now = datetime.now(timezone.utc)
        if until and hasattr(until, "tzinfo") and until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        is_premium = bool(pt and until and now < until)
    except Exception:
        is_female = False
        is_premium = False

    if not is_premium and not is_female:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Функция «Кто тебя лайкнул» доступна с подпиской Premium.", "requires_premium": True},
        )

    try:
        telegram_ids = await service_likes.get_users_ids_liked_by(
            user_id=user_id,
        )
        users = await service_users.get_users_liked_by(users_list=telegram_ids)
    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    return GetUsersFromResponseSchema(
        items=[UserDetailSchema.from_entity(user) for user in users],
    )


@router.post(
    "/{user_id}/toggle-girls-write-first",
    status_code=status.HTTP_200_OK,
    description="Переключить функцию 'Девушки пишут первыми' для мужчины.",
)
async def toggle_girls_write_first(
    user_id: int,
    container: Container = Depends(init_container),
):
    service: BaseUsersService = container.resolve(BaseUsersService)
    try:
        user = await service.get_user(telegram_id=user_id)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    current = bool(getattr(user, "allow_girls_write_first", False))
    new_val = not current
    await service.update_user_info_after_reg(telegram_id=user_id, data={"allow_girls_write_first": new_val})
    return {"ok": True, "allow_girls_write_first": new_val}


@router.get(
    "/{user_id}/can-girl-write/{girl_id}",
    status_code=status.HTTP_200_OK,
    description="Может ли девушка написать мужчине до матча.",
)
async def can_girl_write_first(
    user_id: int,
    girl_id: int,
    container: Container = Depends(init_container),
):
    service: BaseUsersService = container.resolve(BaseUsersService)
    try:
        man = await service.get_user(telegram_id=user_id)
        girl = await service.get_user(telegram_id=girl_id)
    except ApplicationException:
        return {"can_write": False}
    girl_gender = str(getattr(girl, "gender", "") or "").lower()
    is_female = girl_gender in ("female", "женский")
    if not is_female:
        return {"can_write": False}
    allowed = bool(getattr(man, "allow_girls_write_first", False))
    return {"can_write": allowed}


@router.patch(
    "/{user_id}/profile",
    status_code=status.HTTP_200_OK,
    description="Обновить имя, город, описание пользователя из Mini App.",
)
async def update_user_profile(
    user_id: int,
    body: UpdateProfileRequest,
    container: Container = Depends(init_container),
):
    service: BaseUsersService = container.resolve(BaseUsersService)
    try:
        await service.get_user(telegram_id=user_id)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    data: dict = {}
    if body.name is not None and body.name.strip():
        data["name"] = body.name.strip()
    if body.city is not None and body.city.strip():
        data["city"] = body.city.strip()
    if body.about is not None:
        data["about"] = body.about.strip()
    if data:
        await service.update_user_info_after_reg(telegram_id=user_id, data=data)
    return {"ok": True}


@router.post(
    "/{user_id}/ping",
    status_code=status.HTTP_200_OK,
    description="Update last_seen timestamp for a user (called when Mini App is open).",
)
async def ping_user(
    user_id: int,
    container: Container = Depends(init_container),
):
    """Обновляет last_seen пользователя — вызывается с фронта каждые 60 секунд."""
    service: BaseUsersService = container.resolve(BaseUsersService)
    now = datetime.now(timezone.utc)
    await service.update_user_info_after_reg(
        telegram_id=user_id,
        data={"last_seen": now},
    )
    return {"ok": True}


@router.post(
    "/{user_id}/daily-grants",
    status_code=status.HTTP_200_OK,
    description="Начислить ежедневные бонусы Premium/VIP: 1 суперлайк и/или 10 icebreakers.",
)
async def apply_daily_grants(
    user_id: int,
    container: Container = Depends(init_container),
):
    """
    Вызывается при открытии свайп-страницы.
    - Premium/VIP: начисляет 1 суперлайк, если ещё не начислялось сегодня.
    - VIP: начисляет 10 icebreakers, если ещё не начислялось сегодня.
    """
    from motor.motor_asyncio import AsyncIOMotorClient
    config: Config = container.resolve(Config)
    client = AsyncIOMotorClient(config.mongodb_connection_uri)
    db = client[config.mongodb_dating_database]
    col = db[config.mongodb_users_collection]
    now = datetime.now(timezone.utc)
    today = now.date()

    doc = await col.find_one({"telegram_id": user_id})
    client.close()
    if not doc:
        return {"ok": False, "reason": "user not found"}

    premium_type = doc.get("premium_type")
    premium_until = doc.get("premium_until")

    # Проверяем активность подписки
    if not premium_type or not premium_until:
        return {"ok": True, "granted": []}
    if hasattr(premium_until, "tzinfo") and premium_until.tzinfo is None:
        premium_until = premium_until.replace(tzinfo=timezone.utc)
    if now >= premium_until:
        return {"ok": True, "granted": []}

    # Переоткрываем клиент для обновлений
    client = AsyncIOMotorClient(config.mongodb_connection_uri)
    db = client[config.mongodb_dating_database]
    col = db[config.mongodb_users_collection]

    granted = []

    # 1) Суперлайк 1/день для Premium и VIP
    if premium_type in ("premium", "vip"):
        last_sl = doc.get("last_superlike_grant")
        if last_sl:
            if hasattr(last_sl, "tzinfo") and last_sl.tzinfo is None:
                last_sl = last_sl.replace(tzinfo=timezone.utc)
            last_sl_date = last_sl.date()
        else:
            last_sl_date = None

        if last_sl_date != today:
            await col.update_one(
                {"telegram_id": user_id},
                {
                    "$inc": {"superlike_credits": 1},
                    "$set": {"last_superlike_grant": now},
                },
            )
            granted.append("superlike")

    # 2) 10 icebreakers/день только для VIP
    if premium_type == "vip":
        last_ice = doc.get("last_icebreaker_grant")
        if last_ice:
            if hasattr(last_ice, "tzinfo") and last_ice.tzinfo is None:
                last_ice = last_ice.replace(tzinfo=timezone.utc)
            last_ice_date = last_ice.date()
        else:
            last_ice_date = None

        if last_ice_date != today:
            await col.update_one(
                {"telegram_id": user_id},
                {
                    "$inc": {"icebreaker_used": -10},  # -10 = +10 кредитов
                    "$set": {"last_icebreaker_grant": now},
                },
            )
            granted.append("icebreakers_10")

    client.close()
    return {"ok": True, "granted": granted}


class UpdateProfileRequest(BaseModel):
    about: str | None = None
    name: str | None = None
    city: str | None = None


@router.patch(
    "/{user_id}/profile",
    status_code=status.HTTP_200_OK,
    description="Update user profile fields (about, name, city).",
)
async def update_user_profile(
    user_id: int,
    body: UpdateProfileRequest,
    container: Container = Depends(init_container),
):
    service: BaseUsersService = container.resolve(BaseUsersService)
    data = {}
    if body.about is not None:
        data["about"] = body.about
    if body.name is not None:
        data["name"] = body.name
    if body.city is not None:
        data["city"] = body.city
    if not data:
        return {"ok": True}
    try:
        await service.update_user_info_after_reg(telegram_id=user_id, data=data)
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": e.message})
    return {"ok": True}


@router.delete(
    "/admin/reset-all",
    status_code=status.HTTP_200_OK,
    description="[ADMIN] Delete ALL users and related data. Use only for testing.",
)
async def reset_all_users(
    secret: str,
    container: Container = Depends(init_container),
):
    """Полная очистка базы данных — только для тестов."""
    if secret != "lsjlove_reset_2026":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden"})

    config: Config = container.resolve(Config)
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(config.mongodb_connection_uri)
    db = client[config.mongodb_dating_database]

    collections_to_clear = [
        config.mongodb_users_collection,
        config.mongodb_likes_collection,
        "photo_likes",
        "photo_comments",
        "transactions",
        "referrals",
        "daily_question_answers",
    ]

    results = {}
    for col_name in collections_to_clear:
        try:
            col = db[col_name]
            res = await col.delete_many({})
            results[col_name] = res.deleted_count
        except Exception as e:
            results[col_name] = f"error: {e}"

    client.close()
    return {"ok": True, "deleted": results}


# ─────────────────────────── ADMIN API ───────────────────────────

ADMIN_SECRET = "lsjlove_admin_2026"


def _check_admin(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "Forbidden"})


@router.get("/admin/stats", status_code=status.HTTP_200_OK)
async def admin_stats(secret: str, container: Container = Depends(init_container)):
    _check_admin(secret)
    from motor.motor_asyncio import AsyncIOMotorClient
    from datetime import datetime, timezone, timedelta
    config: Config = container.resolve(Config)
    client = AsyncIOMotorClient(config.mongodb_connection_uri)
    db = client[config.mongodb_dating_database]
    users_col = db[config.mongodb_users_collection]

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total = await users_col.count_documents({})
    active = await users_col.count_documents({"is_active": True, "is_banned": {"$ne": True}})
    banned = await users_col.count_documents({"is_banned": True})
    premium = await users_col.count_documents({"premium_type": {"$in": ["premium", "vip"]}, "premium_until": {"$gt": now}})
    vip = await users_col.count_documents({"premium_type": "vip", "premium_until": {"$gt": now}})
    new_today = await users_col.count_documents({"created_at": {"$gte": today_start}})
    online_5min = await users_col.count_documents({"last_seen": {"$gte": now - timedelta(minutes=5)}})
    male = await users_col.count_documents({"gender": {"$in": ["male", "мужской"]}})
    female = await users_col.count_documents({"gender": {"$in": ["female", "женский"]}})
    client.close()
    return {
        "total": total, "active": active, "banned": banned,
        "premium": premium, "vip": vip, "new_today": new_today,
        "online_5min": online_5min, "male": male, "female": female,
    }


@router.get("/admin/users/list", status_code=status.HTTP_200_OK)
async def admin_list_users(
    secret: str,
    page: int = 1,
    limit: int = 20,
    search: str = "",
    container: Container = Depends(init_container),
):
    _check_admin(secret)
    from motor.motor_asyncio import AsyncIOMotorClient
    config: Config = container.resolve(Config)
    client = AsyncIOMotorClient(config.mongodb_connection_uri)
    db = client[config.mongodb_dating_database]
    users_col = db[config.mongodb_users_collection]

    query: dict = {}
    if search:
        try:
            sid = int(search)
            query = {"telegram_id": sid}
        except ValueError:
            query = {"$or": [
                {"name": {"$regex": search, "$options": "i"}},
                {"username": {"$regex": search, "$options": "i"}},
            ]}

    skip = (page - 1) * limit
    total = await users_col.count_documents(query)
    cursor = users_col.find(query, {"_id": 0, "telegram_id": 1, "name": 1, "username": 1,
                                     "gender": 1, "age": 1, "city": 1, "premium_type": 1,
                                     "premium_until": 1, "is_active": 1, "is_banned": 1,
                                     "created_at": 1, "last_seen": 1}).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    for it in items:
        for k in ["premium_until", "created_at", "last_seen"]:
            if k in it and it[k]:
                it[k] = str(it[k])
    client.close()
    return {"total": total, "page": page, "items": items}


@router.get("/admin/users/{target_id}", status_code=status.HTTP_200_OK)
async def admin_get_user(secret: str, target_id: int, container: Container = Depends(init_container)):
    _check_admin(secret)
    service: BaseUsersService = container.resolve(BaseUsersService)
    try:
        user = await service.get_user(telegram_id=target_id)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "telegram_id": user.telegram_id,
        "name": str(user.name),
        "username": user.username,
        "gender": str(getattr(user, "gender", "")),
        "age": str(getattr(user, "age", "")),
        "city": str(getattr(user, "city", "")),
        "about": str(getattr(user, "about", "")),
        "premium_type": getattr(user, "premium_type", None),
        "premium_until": str(getattr(user, "premium_until", None)),
        "is_active": getattr(user, "is_active", True),
        "is_banned": getattr(user, "is_banned", False),
        "referral_balance": getattr(user, "referral_balance", 0),
        "superlike_credits": getattr(user, "superlike_credits", 0),
        "photos": getattr(user, "photos", []),
        "created_at": str(getattr(user, "created_at", None)),
        "last_seen": str(getattr(user, "last_seen", None)),
        "allow_girls_write_first": getattr(user, "allow_girls_write_first", False),
    }


class AdminSetPremiumRequest(BaseModel):
    premium_type: Optional[str] = None   # "premium", "vip", None
    days: int = 30


@router.post("/admin/users/{target_id}/set-premium", status_code=status.HTTP_200_OK)
async def admin_set_premium(
    secret: str,
    target_id: int,
    body: AdminSetPremiumRequest,
    container: Container = Depends(init_container),
):
    _check_admin(secret)
    service: BaseUsersService = container.resolve(BaseUsersService)
    try:
        await service.get_user(telegram_id=target_id)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    from datetime import datetime, timezone, timedelta
    if body.premium_type:
        until = datetime.now(timezone.utc) + timedelta(days=body.days)
        data = {"premium_type": body.premium_type, "premium_until": until}
    else:
        data = {"premium_type": None, "premium_until": None}
    await service.update_user_info_after_reg(telegram_id=target_id, data=data)
    return {"ok": True}


@router.post("/admin/users/{target_id}/ban", status_code=status.HTTP_200_OK)
async def admin_ban_user(
    secret: str,
    target_id: int,
    container: Container = Depends(init_container),
):
    _check_admin(secret)
    service: BaseUsersService = container.resolve(BaseUsersService)
    try:
        await service.get_user(telegram_id=target_id)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await service.update_user_info_after_reg(telegram_id=target_id, data={"is_banned": True, "is_active": False})
    return {"ok": True}


@router.post("/admin/users/{target_id}/unban", status_code=status.HTTP_200_OK)
async def admin_unban_user(
    secret: str,
    target_id: int,
    container: Container = Depends(init_container),
):
    _check_admin(secret)
    service: BaseUsersService = container.resolve(BaseUsersService)
    try:
        await service.get_user(telegram_id=target_id)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await service.update_user_info_after_reg(telegram_id=target_id, data={"is_banned": False, "is_active": True})
    return {"ok": True}


@router.delete("/admin/users/{target_id}", status_code=status.HTTP_200_OK)
async def admin_delete_user(
    secret: str,
    target_id: int,
    container: Container = Depends(init_container),
):
    _check_admin(secret)
    from motor.motor_asyncio import AsyncIOMotorClient
    config: Config = container.resolve(Config)
    client = AsyncIOMotorClient(config.mongodb_connection_uri)
    db = client[config.mongodb_dating_database]

    await db[config.mongodb_users_collection].delete_one({"telegram_id": target_id})
    await db[config.mongodb_likes_collection].delete_many({"$or": [{"from_user": target_id}, {"to_user": target_id}]})
    client.close()
    return {"ok": True}
