from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
from pydantic import BaseModel

from punq import Container

from app.infra.repositories.mongo import (
    MongoDBPhotoCommentsRepository,
    MongoDBPhotoLikesRepository,
)
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService
from app.domain.exceptions.base import ApplicationException


router = APIRouter(
    prefix="/photo-interactions",
    tags=["PhotoInteractions"],
)


class PhotoLikeRequest(BaseModel):
    from_user: int
    owner_id: int
    photo_index: int


class PhotoLikeResponse(BaseModel):
    liked: bool
    count: int
    liked_by_me: bool


class PhotoCommentRequest(BaseModel):
    from_user: int
    owner_id: int
    photo_index: int
    text: str


class PhotoCommentItem(BaseModel):
    id: str
    from_user: int
    from_name: str
    text: str
    created_at: str


class PhotoCommentsResponse(BaseModel):
    comments: list[PhotoCommentItem]


def _get_likes_repo(container: Container) -> MongoDBPhotoLikesRepository:
    return container.resolve(MongoDBPhotoLikesRepository)


def _get_comments_repo(container: Container) -> MongoDBPhotoCommentsRepository:
    return container.resolve(MongoDBPhotoCommentsRepository)


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
        try:
            service: BaseUsersService = container.resolve(BaseUsersService)
            liker = await service.get_user(telegram_id=body.from_user)
            owner = await service.get_user(telegram_id=body.owner_id)
            liker_name = str(getattr(liker, "name", "Кто-то") or "Кто-то")
            owner_is_premium = _is_premium_active(owner)
            from app.bot.utils.notificator import send_photo_liked_notification
            asyncio.create_task(send_photo_liked_notification(
                owner_id=body.owner_id,
                liker_name=liker_name,
                photo_idx=body.photo_index,
                owner_is_premium=owner_is_premium,
            ))
        except Exception as e:
            logger.warning(f"Photo like notification failed: {e}")

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


@router.post(
    "/comments",
    status_code=status.HTTP_200_OK,
    description="Добавить комментарий к фото.",
)
async def add_photo_comment(
    body: PhotoCommentRequest,
    container: Container = Depends(init_container),
) -> PhotoCommentItem:
    if not body.text or not body.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Комментарий не может быть пустым"},
        )
    text = body.text.strip()[:300]

    # Получаем имя автора
    service: BaseUsersService = container.resolve(BaseUsersService)
    from_name = "Пользователь"
    try:
        author = await service.get_user(telegram_id=body.from_user)
        from_name = str(author.name) if author.name else "Пользователь"
    except ApplicationException:
        pass

    repo = _get_comments_repo(container)
    doc = await repo.add_comment(
        from_user=body.from_user,
        from_name=from_name,
        owner_id=body.owner_id,
        photo_index=body.photo_index,
        text=text,
    )

    # Уведомляем владельца о комментарии (не своём)
    if body.from_user != body.owner_id:
        try:
            owner = await service.get_user(telegram_id=body.owner_id)
            owner_is_premium = _is_premium_active(owner)
            from app.bot.utils.notificator import send_photo_commented_notification
            asyncio.create_task(send_photo_commented_notification(
                owner_id=body.owner_id,
                commenter_name=from_name,
                comment_text=text,
                photo_idx=body.photo_index,
                owner_is_premium=owner_is_premium,
            ))
        except Exception as e:
            logger.warning(f"Photo comment notification failed: {e}")

    return PhotoCommentItem(
        id=doc.get("id", ""),
        from_user=doc["from_user"],
        from_name=doc.get("from_name", ""),
        text=doc["text"],
        created_at=doc.get("created_at", "").isoformat() if hasattr(doc.get("created_at", ""), "isoformat") else str(doc.get("created_at", "")),
    )


@router.get(
    "/comments/{owner_id}/{photo_index}",
    status_code=status.HTTP_200_OK,
    description="Получить комментарии к фото.",
)
async def get_photo_comments(
    owner_id: int,
    photo_index: int,
    container: Container = Depends(init_container),
) -> PhotoCommentsResponse:
    repo = _get_comments_repo(container)
    comments_raw = await repo.get_comments(
        owner_id=owner_id,
        photo_index=photo_index,
    )
    return PhotoCommentsResponse(
        comments=[
            PhotoCommentItem(
                id=c["id"],
                from_user=c["from_user"],
                from_name=c.get("from_name", ""),
                text=c["text"],
                created_at=c.get("created_at", ""),
            )
            for c in comments_raw
        ]
    )
