"""
Единый use-case для лайка: бот и API вызывают этот сервис.
Проверки лимитов, swipe_credits, матчи и уведомления — в одном месте.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.domain.entities.likes import LikesEntity
from app.domain.entities.users import UserEntity
from app.domain.exceptions.base import ApplicationException
from app.logic.services.base import BaseLikesService, BaseUsersService
from app.settings.config import Config


def _is_premium_active(user: UserEntity) -> bool:
    pt = getattr(user, "premium_type", None)
    until = getattr(user, "premium_until", None)
    if not pt or not until:
        return False
    if hasattr(until, "tzinfo") and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < until


@dataclass
class LikeActionResult:
    success: bool
    like: Optional[LikesEntity] = None
    is_match: bool = False
    error_message: Optional[str] = None  # При лимите — текст для CTA


@dataclass
class LikeActionUseCase:
    """Единый use-case: like с проверкой лимитов и уведомлениями."""

    likes_service: BaseLikesService
    users_service: BaseUsersService
    config: Config

    async def can_like(
        self,
        from_user_id: int,
        is_superlike: bool = False,
    ) -> tuple[bool, Optional[str]]:
        """
        Проверяет, может ли пользователь поставить лайк.
        Возвращает (can_like, error_message).
        """
        try:
            from_user = await self.users_service.get_user(telegram_id=from_user_id)
        except ApplicationException:
            return False, "Пользователь не найден"

        is_premium = _is_premium_active(from_user)

        if is_superlike:
            sl = getattr(from_user, "superlike_credits", 0) or 0
            if sl <= 0:
                return False, "Нет суперлайков. Купи суперлайк в разделе Premium."

        if not is_premium and not is_superlike:
            today = await self.likes_service.count_likes_today(from_user_id=from_user_id)
            swipe_credits = getattr(from_user, "swipe_credits", 0) or 0
            if today >= self.config.daily_likes_free and swipe_credits <= 0:
                return False, (
                    f"Лимит лайков на сегодня ({self.config.daily_likes_free}) исчерпан. "
                    "Оформи Premium для безлимитных лайков или купи пакет свайпов."
                )

        return True, None

    async def execute(
        self,
        from_user_id: int,
        to_user_id: int,
        is_superlike: bool = False,
    ) -> LikeActionResult:
        """
        Выполняет лайк: проверяет лимиты, создаёт like, отправляет уведомления.
        При лимите возвращает success=False и error_message.
        """
        can, err = await self.can_like(from_user_id, is_superlike=is_superlike)
        if not can:
            return LikeActionResult(success=False, error_message=err)

        try:
            from_user = await self.users_service.get_user(telegram_id=from_user_id)
        except ApplicationException:
            return LikeActionResult(success=False, error_message="Пользователь не найден")

        # Уже лайкнули — не ошибка, просто проверяем матч
        already = await self.likes_service.check_like_is_exists(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
        )

        if not already:
            try:
                like = await self.likes_service.create_like(
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                )
            except ApplicationException:
                return LikeActionResult(success=False, error_message="Не удалось создать лайк")

            # Списываем кредиты
            if is_superlike:
                new_sl = max(0, (getattr(from_user, "superlike_credits", 0) or 0) - 1)
                await self.users_service.update_user_info_after_reg(
                    telegram_id=from_user_id,
                    data={"superlike_credits": new_sl},
                )
            elif not _is_premium_active(from_user):
                today = await self.likes_service.count_likes_today(from_user_id=from_user_id)
                if today > self.config.daily_likes_free:
                    # Этот лайк сверх дневного лимита — списываем swipe_credits
                    credits = getattr(from_user, "swipe_credits", 0) or 0
                    if credits > 0:
                        await self.users_service.update_user_info_after_reg(
                            telegram_id=from_user_id,
                            data={"swipe_credits": credits - 1},
                        )
        else:
            like = None  # Лайк уже был

        is_match = await self.likes_service.check_match(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
        )

        # Уведомления
        try:
            from app.bot.utils.notificator import (
                send_liked_message,
                send_match_message,
                send_superlike_message,
            )
            if is_superlike:
                await send_superlike_message(target_id=to_user_id, sender=from_user)
            elif is_match:
                user_to = await self.users_service.get_user(telegram_id=to_user_id)
                await send_match_message(
                    to_user_id=to_user_id,
                    matched_user=from_user,
                    recipient_id=to_user_id,
                )
                await send_match_message(
                    to_user_id=from_user_id,
                    matched_user=user_to,
                    recipient_id=from_user_id,
                )
            else:
                await send_liked_message(to_user_id=to_user_id, sender=from_user)
        except Exception:
            pass

        return LikeActionResult(
            success=True,
            like=like,
            is_match=is_match,
        )
