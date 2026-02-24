from abc import ABC
from dataclasses import dataclass
from typing import Iterable

from motor.core import AgnosticClient

from app.domain.entities.likes import LikesEntity
from app.domain.entities.users import UserEntity
from app.domain.values.users import AboutText
from app.infra.repositories.base import (
    BaseLikesRepository,
    BaseUsersRepository,
)
from app.infra.repositories.converters import (
    convert_like_entity_to_document,
    convert_user_document_to_entity,
    convert_user_entity_to_document,
)
from app.infra.repositories.filters.users import GetAllUsersFilters


@dataclass
class BaseMongoDBRepository(ABC):
    mongo_db_client: AgnosticClient
    mongo_db_name: str
    mongo_db_collection_name: str

    @property
    def _collection(self):
        return self.mongo_db_client[self.mongo_db_name][self.mongo_db_collection_name]


@dataclass
class MongoDBUserRepository(BaseUsersRepository, BaseMongoDBRepository):
    async def get_user_by_telegram_id(self, telegram_id: int) -> UserEntity | None:
        user_document = await self._collection.find_one(
            filter={"telegram_id": telegram_id},
        )

        if not user_document:
            return None

        return convert_user_document_to_entity(user_document=user_document)

    async def check_user_is_active(self, telegram_id: int) -> bool:
        user_document = await self._collection.find_one(
            filter={"telegram_id": telegram_id, "is_active": True},
        )

        return bool(user_document)

    async def update_user_info_after_register(self, telegram_id: int, data: dict):
        await self._collection.update_one(
            filter={"telegram_id": telegram_id},
            update={"$set": data},
        )

    async def update_user_about(self, telegram_id: int, about: AboutText):
        await self._collection.update_one(
            filter={"telegram_id": telegram_id},
            update={"$set": {"about": about.as_generic_type()}},
        )

    async def create_user(self, user: UserEntity):
        await self._collection.insert_one(convert_user_entity_to_document(user))

    async def check_user_exist_by_telegram_id(self, telegram_id: int) -> bool:
        return bool(
            await self._collection.find_one(
                filter={"telegram_id": telegram_id},
            ),
        )

    async def get_all_user(
        self,
        filters: GetAllUsersFilters,
    ) -> tuple[Iterable[UserEntity], int]:
        cursor = self._collection.find().skip(filters.offset).limit(filters.limit)

        count = await self._collection.count_documents({})
        chats = [
            convert_user_document_to_entity(user_document=user_document)
            async for user_document in cursor
        ]

        return chats, count

    async def get_best_result_for_user(
        self, telegram_id: int, exclude_ids: list[int] | None = None
    ) -> Iterable[UserEntity]:
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return []

        user_age = user.age
        user_city = user.city

        age_min = int(user_age) - 5
        age_max = int(user_age) + 5

        excluded = list(exclude_ids or [])
        excluded.append(telegram_id)

        query_filter: dict = {
            "telegram_id": {"$nin": excluded},
            "$expr": {
                "$and": [
                    {"$gte": [{"$toInt": "$age"}, age_min]},
                    {"$lte": [{"$toInt": "$age"}, age_max]},
                ],
            },
        }

        # Если известен пол — показываем противоположный
        if hasattr(user, "gender") and user.gender:
            gender_map = {"Мужской": "Женский", "Женский": "Мужской", "Man": "Female", "Female": "Man"}
            target_gender = gender_map.get(str(user.gender))
            if target_gender:
                query_filter["gender"] = target_gender

        users_documents = self._collection.find(filter=query_filter)

        return [
            convert_user_document_to_entity(user_document=user_document)
            async for user_document in users_documents
        ]

    async def get_users_liked_from(self, user_list: list[int]) -> Iterable[UserEntity]:
        users_documents = self._collection.find(
            filter={"telegram_id": {"$in": user_list}},
        )

        result = []
        async for user_document in users_documents:
            telegram_id = user_document.get("telegram_id")
            if telegram_id:
                user_entity = await self.get_user_by_telegram_id(
                    telegram_id=telegram_id,
                )
                if user_entity:
                    result.append(user_entity)

        return result

    async def get_users_liked_by(self, user_list: list[int]) -> Iterable[UserEntity]:
        users_documents = self._collection.find(
            filter={"telegram_id": {"$in": user_list}},
        )

        result = []
        async for user_document in users_documents:
            telegram_id = user_document.get("telegram_id")
            if telegram_id:
                user_entity = await self.get_user_by_telegram_id(
                    telegram_id=telegram_id,
                )
                if user_entity:
                    result.append(user_entity)

        return result

    async def get_icebreaker_count(self, telegram_id: int) -> int:
        doc = await self._collection.find_one(
            filter={"telegram_id": telegram_id},
            projection={"icebreaker_used": 1},
        )
        if not doc:
            return 0
        return int(doc.get("icebreaker_used", 0))

    async def increment_icebreaker_count(self, telegram_id: int) -> int:
        result = await self._collection.find_one_and_update(
            filter={"telegram_id": telegram_id},
            update={"$inc": {"icebreaker_used": 1}},
            return_document=True,
            projection={"icebreaker_used": 1},
        )
        if not result:
            return 1
        return int(result.get("icebreaker_used", 1))

    async def get_advisor_trial_start(self, telegram_id: int):
        doc = await self._collection.find_one(
            filter={"telegram_id": telegram_id},
            projection={"ai_advisor_first_used": 1},
        )
        if not doc:
            return None
        return doc.get("ai_advisor_first_used")

    async def set_advisor_trial_start(self, telegram_id: int):
        from datetime import datetime, timezone
        await self._collection.update_one(
            filter={"telegram_id": telegram_id},
            update={"$set": {"ai_advisor_first_used": datetime.now(timezone.utc)}},
        )

    async def get_photos(self, telegram_id: int) -> list[str]:
        doc = await self._collection.find_one(
            filter={"telegram_id": telegram_id},
            projection={"photos": 1},
        )
        if not doc:
            return []
        return doc.get("photos") or []

    async def add_photo(self, telegram_id: int, s3_key: str) -> list[str]:
        await self._collection.update_one(
            filter={"telegram_id": telegram_id},
            update={"$push": {"photos": s3_key}},
        )
        return await self.get_photos(telegram_id)

    async def remove_photo(self, telegram_id: int, index: int) -> list[str]:
        photos = await self.get_photos(telegram_id)
        if index < 0 or index >= len(photos):
            return photos
        photos.pop(index)
        # Обновляем первое фото для обратной совместимости
        main_photo = photos[0] if photos else None
        await self._collection.update_one(
            filter={"telegram_id": telegram_id},
            update={"$set": {"photos": photos, "photo": main_photo}},
        )
        return photos


@dataclass
class MongoDBLikesRepository(BaseLikesRepository, BaseMongoDBRepository):
    async def check_like_is_exists(self, from_user: int, to_user: int) -> bool:
        return bool(
            await self._collection.find_one(
                filter={
                    "from_user": from_user,
                    "to_user": to_user,
                },
            ),
        )

    async def create_like(self, like: LikesEntity) -> LikesEntity:
        await self._collection.insert_one(convert_like_entity_to_document(like))
        return like

    async def delete_like(self, from_user: int, to_user: int):
        await self._collection.delete_one(
            filter={
                "from_user": from_user,
                "to_user": to_user,
            },
        )

    async def get_users_ids_liked_from(self, user_id: int) -> list[int]:
        users_documents = self._collection.find(
            filter={"from_user": user_id},
        )

        result = []
        async for user_document in users_documents:
            telegram_id = user_document.get("to_user")
            if telegram_id:
                result.append(telegram_id)

        return result

    async def get_users_ids_liked_by(self, user_id: int) -> list[int]:
        users_documents = self._collection.find(
            filter={"to_user": user_id},
        )

        result = []
        async for user_document in users_documents:
            telegram_id = user_document.get("from_user")
            if telegram_id:
                result.append(telegram_id)

        return result


@dataclass
class MongoDBPhotoLikesRepository(BaseMongoDBRepository):
    """Лайки к конкретным фотографиям."""

    async def toggle_like(self, from_user: int, owner_id: int, photo_index: int) -> bool:
        """Добавляет или удаляет лайк. Возвращает True если лайк добавлен."""
        existing = await self._collection.find_one(
            filter={"from_user": from_user, "owner_id": owner_id, "photo_index": photo_index},
        )
        if existing:
            await self._collection.delete_one({"_id": existing["_id"]})
            return False
        from datetime import datetime, timezone
        await self._collection.insert_one({
            "from_user": from_user,
            "owner_id": owner_id,
            "photo_index": photo_index,
            "created_at": datetime.now(timezone.utc),
        })
        return True

    async def get_likes_info(self, owner_id: int, photo_index: int, viewer_id: int) -> dict:
        count = await self._collection.count_documents(
            {"owner_id": owner_id, "photo_index": photo_index}
        )
        liked_by_me = bool(await self._collection.find_one(
            {"from_user": viewer_id, "owner_id": owner_id, "photo_index": photo_index}
        ))
        return {"count": count, "liked_by_me": liked_by_me}


@dataclass
class MongoDBPhotoCommentsRepository(BaseMongoDBRepository):
    """Комментарии к фотографиям."""

    async def add_comment(self, from_user: int, from_name: str, owner_id: int, photo_index: int, text: str) -> dict:
        from datetime import datetime, timezone
        doc = {
            "from_user": from_user,
            "from_name": from_name,
            "owner_id": owner_id,
            "photo_index": photo_index,
            "text": text,
            "created_at": datetime.now(timezone.utc),
        }
        result = await self._collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        return doc

    async def get_comments(self, owner_id: int, photo_index: int, limit: int = 20) -> list[dict]:
        cursor = self._collection.find(
            filter={"owner_id": owner_id, "photo_index": photo_index},
        ).sort("created_at", -1).limit(limit)
        comments = []
        async for doc in cursor:
            comments.append({
                "id": str(doc.get("_id", "")),
                "from_user": doc["from_user"],
                "from_name": doc.get("from_name", ""),
                "text": doc["text"],
                "created_at": doc["created_at"].isoformat() if doc.get("created_at") else "",
            })
        return list(reversed(comments))
