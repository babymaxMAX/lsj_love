import asyncio
import logging
from datetime import datetime, timezone

from fastapi import Depends, status
from fastapi.routing import APIRouter
from pydantic import BaseModel

from punq import Container

from app.infra.repositories.mongo import MongoDBPhotoLikesRepository
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/photo-interactions",
    tags=["PhotoInteractions"],
)


def _is_premium_active(user) -> bool:
    if not user:
        return False
    premium_type = getattr(user, "premium_type", None)
    premium_until = getattr(user, "premium_until", None)
    if not premium_type or not premium_until:
        return False
    try:
        now = datetime.now(timezone.utc)
        if hasattr(premium_until, "tzinfo") and premium_until.tzinfo is None:
            premium_until = premium_until.replace(tzinfo=timezone.utc)
        return now < premium_until
    except Exception:
        return False


class PhotoLikeRequest(BaseModel):
    from_user: int
    owner_id: int
    photo_index: int


class PhotoLikeResponse(BaseModel):
    liked: bool
    count: int
    liked_by_me: bool


def _get_likes_repo(container: Container) -> MongoDBPhotoLikesRepository:
    return container.resolve(MongoDBPhotoLikesRepository)


@router.post(
    "/likes",
    status_code=status.HTTP_200_OK,
    description="Лайк/дизлайк фотографии.",
)
async def toggle_photo_like(
    body: PhotoLikeRequest,
    container: Container = Depends(init_container),
) -> PhotoLikeResponse:
    repo = _get_likes_repo(container)
    liked = await repo.toggle_like(
        from_user=body.from_user,
        owner_id=body.owner_id,
        photo_index=body.photo_index,
    )
    info = await repo.get_likes_info(
        owner_id=body.owner_id,
        photo_index=body.photo_index,
        viewer_id=body.from_user,
    )

    # Уведомляем владельца если лайк добавлен (не снят) и это не лайк своего фото
    if liked and body.from_user != body.owner_id:
        async def _notify():
            try:
                service: BaseUsersService = container.resolve(BaseUsersService)
                liker = await service.get_user(telegram_id=body.from_user)
                owner = await service.get_user(telegram_id=body.owner_id)
                liker_name = str(getattr(liker, "name", "Кто-то") or "Кто-то")
                owner_is_premium = _is_premium_active(owner)
                from app.bot.utils.notificator import send_photo_liked_notification
                await send_photo_liked_notification(
                    owner_id=body.owner_id,
                    liker_name=liker_name,
                    photo_idx=body.photo_index,
                    owner_is_premium=owner_is_premium,
                )
            except Exception as e:
                logger.warning(f"Photo like notification failed: {e}")
        asyncio.create_task(_notify())

    return PhotoLikeResponse(liked=liked, count=info["count"], liked_by_me=info["liked_by_me"])


@router.get(
    "/likes/{owner_id}/{photo_index}",
    status_code=status.HTTP_200_OK,
    description="Получить количество лайков и статус для текущего пользователя.",
)
async def get_photo_likes(
    owner_id: int,
    photo_index: int,
    viewer_id: int = 0,
    container: Container = Depends(init_container),
) -> PhotoLikeResponse:
    repo = _get_likes_repo(container)
    info = await repo.get_likes_info(
        owner_id=owner_id,
        photo_index=photo_index,
        viewer_id=viewer_id,
    )
    return PhotoLikeResponse(
        liked=info["liked_by_me"],
        count=info["count"],
        liked_by_me=info["liked_by_me"],
    )
