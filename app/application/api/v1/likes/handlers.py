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
from app.domain.exceptions.base import ApplicationException
from app.infra.repositories.base import BaseDislikesRepository
from app.logic.init import init_container
from app.logic.services.base import BaseLikesService, BaseUsersService
from app.logic.use_cases.like_action import LikeActionUseCase
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
    "/bot-username",
    status_code=status.HTTP_200_OK,
    description="Bot username for relay chat (matches without @username).",
)
async def get_bot_username(
    container: Container = Depends(init_container),
):
    config: Config = container.resolve(Config)
    from app.application.api.lifespan import get_bot_username as _get
    return {"bot_username": config.bot_username or _get()}


@router.get(
    "/matches/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Get mutual matches for user (no premium required).",
)
async def get_matches(
    user_id: int,
    container: Container = Depends(init_container),
):
    """Возвращает список взаимных матчей (mutual likes) — доступно всем пользователям."""
    service: BaseLikesService = container.resolve(BaseLikesService)
    users_service: BaseUsersService = container.resolve(BaseUsersService)
    config: Config = container.resolve(Config)

    try:
        liked_by_me = set(await service.get_telegram_id_liked_from(user_id=user_id))
        liked_me = set(await service.get_users_ids_liked_by(user_id=user_id))
        mutual_ids = list(liked_by_me & liked_me)
        users = await users_service.get_users_liked_from(users_list=mutual_ids)
    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    from app.application.api.v1.users.schemas import UserDetailSchema
    from app.application.api.lifespan import get_bot_username
    bot_username = config.bot_username or get_bot_username()
    return {
        "items": [UserDetailSchema.from_entity(u) for u in users],
        "bot_username": bot_username,
    }


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
    use_case: LikeActionUseCase = container.resolve(LikeActionUseCase)

    result = await use_case.execute(
        from_user_id=schema.from_user,
        to_user_id=schema.to_user,
        is_superlike=bool(schema.is_superlike),
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": result.error_message},
        )

    if not result.like:
        from datetime import datetime, timezone
        from app.domain.entities.likes import LikesEntity
        from app.domain.values.likes import Like
        dummy = LikesEntity(
            from_user=Like(schema.from_user),
            to_user=Like(schema.to_user),
            created_at=datetime.now(timezone.utc),
        )
        return CreateLikeResponseSchema.from_entity(dummy)

    return CreateLikeResponseSchema.from_entity(result.like)


@router.post(
    "/dislike",
    status_code=status.HTTP_200_OK,
    description="Dislike (skip) a user. Persisted to DB so profile won't reappear.",
)
async def dislike_user(
    schema: CreateLikeRequestSchema,
    container: Container = Depends(init_container),
):
    dislikes_repo: BaseDislikesRepository = container.resolve(BaseDislikesRepository)
    await dislikes_repo.add_dislike(from_user=schema.from_user, to_user=schema.to_user)
    return {"ok": True}


@router.delete(
    "/dislike",
    status_code=status.HTTP_200_OK,
    description="Undo last dislike (Premium feature — rewind swipe).",
)
async def undo_dislike(
    schema: DeleteLikeRequestSchema,
    container: Container = Depends(init_container),
):
    """Откат дизлайка — Premium фича (перемотка свайпа)."""
    users_service: BaseUsersService = container.resolve(BaseUsersService)
    try:
        from_user = await users_service.get_user(telegram_id=schema.from_user)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "User not found"})

    if not _is_premium_active(from_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Откат свайпа доступен только с подпиской Premium."},
        )

    dislikes_repo: BaseDislikesRepository = container.resolve(BaseDislikesRepository)
    await dislikes_repo.remove_dislike(from_user=schema.from_user, to_user=schema.to_user)
    return {"ok": True}


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
