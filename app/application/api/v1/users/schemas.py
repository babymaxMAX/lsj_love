from datetime import datetime, timezone
from typing import Optional


def _to_utc_iso(dt: datetime | None) -> str | None:
    """Возвращает ISO-строку с явным UTC-офсетом, чтобы JavaScript не интерпретировал как локальное время."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

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
    last_seen: Optional[str] = None   # ISO-строка UTC
    profile_answers: Optional[dict] = None
    premium_type: Optional[str] = None  # "premium" | "vip" | None

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
            last_seen=_to_utc_iso(user.last_seen),
            profile_answers=getattr(user, "profile_answers", None),
            premium_type=getattr(user, "premium_type", None) if _is_sub_active(user) else None,
        )


def _is_sub_active(user) -> bool:
    from datetime import datetime, timezone
    pt = getattr(user, "premium_type", None)
    until = getattr(user, "premium_until", None)
    if not pt or not until:
        return False
    if hasattr(until, "tzinfo") and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < until


class GetUsersResponseSchema(BaseQueryResponseSchema):
    items: list[UserDetailSchema]


class GetUsersFromResponseSchema(BaseModel):
    items: list[UserDetailSchema]
