from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from punq import Container

from app.application.api.schemas import ErrorSchema
from app.application.api.v1.likes.schemas import (
    CreateLikeRequestSchema,
    CreateLikeResponseSchema,
    DeleteLikeRequestSchema,
    DeleteLikeResponseSchema,
    GetLikeRequestSchema,
    GetLikeResponseSchema,
)
from app.bot.utils.notificator import send_liked_message, send_match_message, send_superlike_message
from app.domain.exceptions.base import ApplicationException
from app.logic.init import init_container
from app.logic.services.base import BaseLikesService, BaseUsersService
from app.settings.config import Config


def _is_premium_active(user, required_type: str | None = None) -> bool:
    """Проверяет активна ли подписка пользователя."""
    pt = getattr(user, "premium_type", None)
    until = getattr(user, "premium_until", None)
    if not pt or not until:
        return False
    if hasattr(until, "tzinfo") and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) >= until:
        return False
    return required_type is None or pt == required_type


router = APIRouter(
    prefix="/likes",
    tags=["Like"],
)


@router.get(
    "/{from_user}/{to_user}",
    status_code=status.HTTP_200_OK,
    description="Get like.",
    responses={
        status.HTTP_200_OK: {"model": GetLikeRequestSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def get_like(
    from_user: int,
    to_user: int,
    container: Container = Depends(init_container),
) -> GetLikeResponseSchema:
    service: BaseLikesService = container.resolve(BaseLikesService)

    try:
        like = await service.check_like_is_exists(
            from_user_id=from_user,
            to_user_id=to_user,
        )
    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    return GetLikeResponseSchema(status=like)


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    description="Like a user. Enforces daily limits for free users.",
    responses={
        status.HTTP_200_OK: {"model": CreateLikeResponseSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
        status.HTTP_403_FORBIDDEN: {"model": ErrorSchema},
    },
)
async def add_like_to_user(
    schema: CreateLikeRequestSchema,
    container: Container = Depends(init_container),
) -> CreateLikeResponseSchema:
    service: BaseLikesService = container.resolve(BaseLikesService)
    users_service: BaseUsersService = container.resolve(BaseUsersService)
    config: Config = container.resolve(Config)

    # Загружаем текущего пользователя для проверки лимитов
    try:
        from_user = await users_service.get_user(telegram_id=schema.from_user)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "User not found"})

    is_premium = _is_premium_active(from_user)

    # Суперлайк: проверяем кредиты
    if schema.is_superlike:
        sl_credits = getattr(from_user, "superlike_credits", 0) or 0
        if sl_credits <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Нет суперлайков. Купи суперлайк в разделе Premium."},
            )

    # Дневной лимит для бесплатных пользователей
    if not is_premium and not schema.is_superlike:
        today_count = await service.count_likes_today(from_user_id=schema.from_user)
        if today_count >= config.daily_likes_free:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": f"Лимит лайков на сегодня ({config.daily_likes_free}) исчерпан. Оформи Premium для безлимитных лайков."},
            )

    try:
        like = await service.create_like(
            from_user_id=schema.from_user,
            to_user_id=schema.to_user,
        )

        # Если суперлайк — списываем кредит и уведомляем получателя
        if schema.is_superlike:
            try:
                new_credits = max(0, (getattr(from_user, "superlike_credits", 0) or 0) - 1)
                await users_service.update_user_info_after_reg(
                    telegram_id=schema.from_user,
                    data={"superlike_credits": new_credits},
                )
                await send_superlike_message(target_id=schema.to_user, sender=from_user)
            except Exception:
                pass
        else:
            # Проверяем взаимный лайк → матч
            is_match = await service.check_match(
                from_user_id=schema.from_user,
                to_user_id=schema.to_user,
            )

            if is_match:
                try:
                    user_to = await users_service.get_user(telegram_id=schema.to_user)
                    await send_match_message(
                        to_user_id=schema.to_user,
                        matched_user=from_user,
                        recipient_id=schema.to_user,
                    )
                    await send_match_message(
                        to_user_id=schema.from_user,
                        matched_user=user_to,
                        recipient_id=schema.from_user,
                    )
                except Exception:
                    pass
            else:
                try:
                    await send_liked_message(to_user_id=schema.to_user)
                except Exception:
                    pass

    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    return CreateLikeResponseSchema.from_entity(like)


@router.delete(
    "/",
    status_code=status.HTTP_200_OK,
    description="Delete like from user to user.",
    responses={
        status.HTTP_200_OK: {"model": DeleteLikeResponseSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def delete_like(
    schema: DeleteLikeRequestSchema,
    container: Container = Depends(init_container),
) -> DeleteLikeResponseSchema:
    service: BaseLikesService = container.resolve(BaseLikesService)

    try:
        await service.delete_like(
            from_user_id=schema.from_user,
            to_user_id=schema.to_user,
        )
    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    return DeleteLikeResponseSchema.delete_response()
