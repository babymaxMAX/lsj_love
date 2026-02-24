from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Literal

from aiogram.types import User

from app.domain.entities.base import BaseEntity
from app.domain.values.users import (
    AboutText,
    Age,
    City,
    Gender,
    Name,
)


@dataclass
class UserEntity(BaseEntity):
    telegram_id: int
    name: Name
    username: Optional[str] = None
    gender: Optional[Gender] = None
    age: Optional[Age] = None
    city: Optional[City] = None
    looking_for: Optional[Gender] = None
    about: Optional[AboutText] = None
    photo: Optional[str] = None
    photos: list = None  # S3 ключи вида {telegram_id}_{index}.png
    is_active: bool = False
    # Premium статус: None = бесплатный, "premium" = Premium, "vip" = VIP
    premium_type: Optional[Literal["premium", "vip"]] = None
    premium_until: Optional[datetime] = None
    # Суперлайки
    superlike_credits: int = 0
    # Буст профиля
    boost_until: Optional[datetime] = None
    boosts_this_week: int = 0
    boost_week_reset: Optional[datetime] = None

    def __post_init__(self):
        if self.photos is None:
            self.photos = []

    @classmethod
    def from_telegram_user(cls, user: User) -> "UserEntity":
        return cls(
            telegram_id=user.id,
            username=user.username or "",
            name=Name(user.first_name),
            created_at=datetime.now()
        )
