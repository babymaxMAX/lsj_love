from abc import (
    ABC,
    abstractmethod,
)
from dataclasses import dataclass
from typing import Iterable

from app.domain.entities.likes import LikesEntity
from app.domain.entities.users import UserEntity
from app.domain.values.users import AboutText
from app.infra.repositories.filters.users import GetAllUsersFilters


@dataclass
class BaseUsersRepository(ABC):
    @abstractmethod
    async def get_user_by_telegram_id(self, telegram_id: int) -> UserEntity: ...

    @abstractmethod
    async def check_user_is_active(self, telegram_id: int) -> bool: ...

    @abstractmethod
    async def get_all_user(self, filters: GetAllUsersFilters): ...

    @abstractmethod
    async def update_user_info_after_register(self, telegram_id: int, data: dict): ...

    @abstractmethod
    async def update_user_about(self, telegram_id: int, about: AboutText): ...

    @abstractmethod
    async def update_user_ai_fields(self, telegram_id: int, ai_fields: dict) -> None:
        """Обновляет AI-поля (search_text, ai_traits, ai_skills, ai_appearance)."""

    @abstractmethod
    async def create_user(self, user: UserEntity): ...

    @abstractmethod
    async def check_user_exist_by_telegram_id(self, telegram_id: int) -> bool: ...

    @abstractmethod
    async def get_users_liked_from(
        self,
        user_list: list[int],
    ) -> Iterable[UserEntity]: ...

    @abstractmethod
    async def get_users_liked_by(
        self,
        user_list: list[int],
    ) -> Iterable[UserEntity]: ...

    @abstractmethod
    async def get_best_result_for_user(
        self,
        telegram_id: int,
        exclude_ids: list[int] | None = None,
    ) -> Iterable[UserEntity]: ...

    async def get_ai_matchmaking_candidates(
        self,
        telegram_id: int,
        target_gender: str,
        exclude_ids: list[int] | None = None,
        age_min: int | None = None,
        age_max: int | None = None,
        city: str | None = None,
        city_include_neighbors: bool = False,
        limit: int = 300,
    ) -> list[UserEntity]:
        """Кандидаты для AI-подбора по жестким фильтрам. По умолчанию — заглушка."""
        return []

    @abstractmethod
    async def get_icebreaker_count(self, telegram_id: int) -> int: ...

    @abstractmethod
    async def get_icebreaker_total_count(self, telegram_id: int) -> int: ...

    @abstractmethod
    async def increment_icebreaker_count(self, telegram_id: int) -> int: ...

    @abstractmethod
    async def get_advisor_trial_start(self, telegram_id: int): ...

    @abstractmethod
    async def set_advisor_trial_start(self, telegram_id: int): ...

    @abstractmethod
    async def add_photo(self, telegram_id: int, s3_key: str) -> list[str]: ...

    @abstractmethod
    async def remove_photo(self, telegram_id: int, index: int) -> list[str]: ...

    @abstractmethod
    async def replace_photo(self, telegram_id: int, index: int, s3_key: str) -> list[str]: ...

    @abstractmethod
    async def get_photos(self, telegram_id: int) -> list[str]: ...


@dataclass
class BaseDislikesRepository(ABC):
    @abstractmethod
    async def add_dislike(self, from_user: int, to_user: int) -> None: ...

    @abstractmethod
    async def get_disliked_ids(self, user_id: int) -> list[int]: ...

    @abstractmethod
    async def remove_dislike(self, from_user: int, to_user: int) -> None: ...


@dataclass
class BaseLikesRepository(ABC):
    @abstractmethod
    async def check_like_is_exists(self, from_user: int, to_user: int) -> bool: ...

    @abstractmethod
    async def create_like(self, like: LikesEntity) -> LikesEntity: ...

    @abstractmethod
    async def delete_like(self, from_user: int, to_user: int): ...

    @abstractmethod
    async def get_users_ids_liked_from(self, user_id: int) -> list[int]: ...

    @abstractmethod
    async def get_users_ids_liked_by(self, user_id: int) -> list[int]: ...

    @abstractmethod
    async def count_likes_today(self, from_user: int) -> int: ...
