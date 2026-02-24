from typing import Optional

from pydantic import BaseModel

from app.application.api.schemas import BaseQueryResponseSchema
from app.domain.entities.users import UserEntity


class UserDetailSchema(BaseModel):
    telegram_id: int
    name: str
    username: Optional[str]
    gender: Optional[str]
    age: Optional[int]
    city: Optional[str]
    looking_for: Optional[str]
    about: Optional[str]
    photo: Optional[str]
    photos: list[str] = []
    is_active: bool

    @classmethod
    def from_entity(cls, user: UserEntity) -> "UserDetailSchema":
        uid = user.telegram_id

        # Главное фото (для обратной совместимости)
        photo = user.photo
        if photo and not photo.startswith("http"):
            photo = f"/api/v1/users/{uid}/photo"

        # Массив фото: если есть photos[] (S3 ключи) — строим URL по индексу
        user_photos: list = getattr(user, "photos", []) or []
        if user_photos:
            photos_urls = [f"/api/v1/users/{uid}/photo/{i}" for i in range(len(user_photos))]
        elif photo:
            # Обратная совместимость: одно фото → массив из одного
            photos_urls = [f"/api/v1/users/{uid}/photo"]
        else:
            photos_urls = []

        return UserDetailSchema(
            telegram_id=uid,
            name=user.name,
            username=user.username,
            gender=user.gender,
            age=user.age,
            city=user.city,
            looking_for=user.looking_for,
            about=user.about,
            photo=photo,
            photos=photos_urls,
            is_active=user.is_active,
        )


class GetUsersResponseSchema(BaseQueryResponseSchema):
    items: list[UserDetailSchema]


class GetUsersFromResponseSchema(BaseModel):
    items: list[UserDetailSchema]
