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

    # Premium gate for "who liked you"
    try:
        requesting_user = await service_users.get_user(telegram_id=user_id)
        pt = getattr(requesting_user, "premium_type", None)
        until = getattr(requesting_user, "premium_until", None)
        now = datetime.now(timezone.utc)
        if until and hasattr(until, "tzinfo") and until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        is_premium = bool(pt and until and now < until)
    except Exception:
        is_premium = False

    if not is_premium:
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
