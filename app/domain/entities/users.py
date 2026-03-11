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
    intention: Optional[str] = None  # serious/casual/friendship/exploring
    about: Optional[AboutText] = None
    photo: Optional[str] = None
    photos: list = None  # S3 ключи вида {telegram_id}_{index}.png
    is_active: bool = True
    profile_hidden: bool = False  # True = пользователь скрыл анкету из поиска
    # Premium статус: None = бесплатный, "premium" = Premium, "vip" = VIP
    premium_type: Optional[Literal["premium", "vip"]] = None
    premium_until: Optional[datetime] = None
    # Суперлайки
    superlike_credits: int = 0
    # Пакеты свайпов (40/80) — расходуются после исчерпания daily_likes_free
    swipe_credits: int = 0
    # Буст профиля
    boost_until: Optional[datetime] = None
    boosts_this_week: int = 0
    boost_week_reset: Optional[datetime] = None
    # Реферальная система
    referred_by: Optional[int] = None       # telegram_id кто пригласил
    referral_balance: float = 0.0           # заработанный реферальный баланс (руб)
    # Активность
    last_seen: Optional[datetime] = None    # последний раз онлайн
    # AI matchmaking
    search_text: Optional[str] = None       # конкатенация имени, возраста, города, about
    ai_traits: list = None                   # ["calm", "family_oriented"]
    ai_skills: list = None                   # ["cooking"]
    ai_appearance: list = None               # ["red_hair"]

    def __post_init__(self):
        if self.photos is None:
            self.photos = []
        if self.ai_traits is None:
            self.ai_traits = []
        if self.ai_skills is None:
            self.ai_skills = []
        if self.ai_appearance is None:
            self.ai_appearance = []

    @classmethod
    def from_telegram_user(cls, user: User) -> "UserEntity":
        # Имя в Telegram может быть 1 символ или пустым — подставляем fallback
        raw_name = (user.first_name or "").strip()
        if len(raw_name) < 2:
            raw_name = user.username or "Пользователь"
        if len(raw_name) < 2:
            raw_name = "Пользователь"
        return cls(
            telegram_id=user.id,
            username=user.username or "",
            name=Name(raw_name),
            created_at=datetime.now()
        )
