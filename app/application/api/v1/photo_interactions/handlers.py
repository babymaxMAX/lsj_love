import asyncio
import logging
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from punq import Container

from app.infra.repositories.mongo import MongoDBPhotoLikesRepository
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService
from app.settings.config import Config

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


@router.get(
    "/likes/{owner_id}/{photo_index}/detail",
    status_code=status.HTTP_200_OK,
    description="Detailed photo likes: total, viewer status, likers list (Premium only for owner).",
)
async def get_photo_likes_detail(
    owner_id: int,
    photo_index: int,
    viewer_id: int = 0,
    container: Container = Depends(init_container),
):
    repo = _get_likes_repo(container)
    info = await repo.get_likes_info(owner_id=owner_id, photo_index=photo_index, viewer_id=viewer_id)

    result = {
        "total_likes": info["count"],
        "viewer_liked": info["liked_by_me"],
        "likers": [],
        "access": "locked",
    }

    if viewer_id == owner_id and viewer_id != 0:
        service: BaseUsersService = container.resolve(BaseUsersService)
        try:
            owner = await service.get_user(telegram_id=owner_id)
            is_premium = _is_premium_active(owner)
        except Exception:
            is_premium = False

        if is_premium:
            result["access"] = "full"
            client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
            config: Config = container.resolve(Config)
            col = client[config.mongodb_dating_database]["photo_likes"]
            cursor = col.find(
                {"owner_id": owner_id, "photo_index": photo_index},
            ).sort("created_at", -1).limit(50)
            liker_ids = []
            liker_times = {}
            async for doc in cursor:
                liker_ids.append(doc["from_user"])
                liker_times[doc["from_user"]] = doc.get("created_at")

            if liker_ids:
                users_col = client[config.mongodb_dating_database][config.mongodb_users_collection]
                users_cursor = users_col.find(
                    {"telegram_id": {"$in": liker_ids}},
                    {"telegram_id": 1, "name": 1, "photos": 1},
                )
                users_map = {}
                async for u in users_cursor:
                    users_map[u["telegram_id"]] = u

                for lid in liker_ids:
                    u = users_map.get(lid, {})
                    name = str(u.get("name", "Пользователь") or "Пользователь")
                    photos = u.get("photos", []) or []
                    photo_url = f"/api/v1/users/{lid}/photo" if photos else ""
                    result["likers"].append({
                        "telegram_id": lid,
                        "name": name,
                        "photo_url": photo_url,
                        "liked_at": str(liker_times.get(lid, "")),
                    })

    return result


@router.get(
    "/my-likes/{user_id}",
    status_code=status.HTTP_200_OK,
    description="All likes across all photos for a user.",
)
async def get_my_likes(
    user_id: int,
    container: Container = Depends(init_container),
):
    service: BaseUsersService = container.resolve(BaseUsersService)
    try:
        owner = await service.get_user(telegram_id=user_id)
    except Exception:
        raise HTTPException(status_code=404, detail={"error": "User not found"})

    is_premium = _is_premium_active(owner)
    photos_list = getattr(owner, "photos", []) or []

    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)
    col = client[config.mongodb_dating_database]["photo_likes"]
    users_col = client[config.mongodb_dating_database][config.mongodb_users_collection]

    photos_data = []
    total_all = 0

    for idx in range(len(photos_list)):
        count = await col.count_documents({"owner_id": user_id, "photo_index": idx})
        total_all += count

        photo_url = f"/api/v1/users/{user_id}/photos/{idx}"
        entry = {"photo_index": idx, "photo_url": photo_url, "total_likes": count, "recent_likers": []}

        if is_premium and count > 0:
            cursor = col.find(
                {"owner_id": user_id, "photo_index": idx},
            ).sort("created_at", -1).limit(5)
            liker_ids = []
            async for doc in cursor:
                liker_ids.append(doc["from_user"])

            if liker_ids:
                u_cursor = users_col.find(
                    {"telegram_id": {"$in": liker_ids}},
                    {"telegram_id": 1, "name": 1, "photos": 1},
                )
                async for u in u_cursor:
                    name = str(u.get("name", "") or "Пользователь")
                    u_photos = u.get("photos", []) or []
                    purl = f"/api/v1/users/{u['telegram_id']}/photo" if u_photos else ""
                    entry["recent_likers"].append({
                        "telegram_id": u["telegram_id"],
                        "name": name,
                        "photo_url": purl,
                    })

        photos_data.append(entry)

    return {
        "photos": photos_data,
        "total_all_photos": total_all,
        "is_premium": is_premium,
    }
