from typing import Optional

from pydantic import BaseModel

from app.application.api.schemas import BaseQueryResponseSchema
from app.domain.entities.users import UserEntity


_VIDEO_EXTS = {"mp4", "mov", "webm", "avi", "mkv"}


def _key_is_video(key: str) -> bool:
    ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
    return ext in _VIDEO_EXTS


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
    media_types: list[str] = []  # "image" | "video" for each item in photos
    is_active: bool
    referral_balance: float = 0.0

    @classmethod
    def from_entity(cls, user: UserEntity) -> "UserDetailSchema":
        uid = user.telegram_id

        photo = user.photo
        if photo and not photo.startswith("http"):
            photo = f"/api/v1/users/{uid}/photo"

        user_photos: list = getattr(user, "photos", []) or []
        if user_photos:
            photos_urls = [f"/api/v1/users/{uid}/photo/{i}" for i in range(len(user_photos))]
            media_types = ["video" if _key_is_video(k) else "image" for k in user_photos]
        elif photo:
            photos_urls = [f"/api/v1/users/{uid}/photo"]
            media_types = ["image"]
        else:
            photos_urls = []
            media_types = []

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
            media_types=media_types,
            is_active=user.is_active,
            referral_balance=float(getattr(user, "referral_balance", 0) or 0),
        )


class GetUsersResponseSchema(BaseQueryResponseSchema):
    items: list[UserDetailSchema]


class GetUsersFromResponseSchema(BaseModel):
    items: list[UserDetailSchema]
