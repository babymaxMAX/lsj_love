"""
Безопасные endpoints: user_id берётся из сессии (cookie), не из client.
/app вызывает эти endpoints вместо /users/{user_id}/...
"""
from fastapi import APIRouter, Depends
from punq import Container

from pydantic import BaseModel

from app.application.api.v1.auth.handlers import get_current_user
from app.application.api.v1.likes.handlers import add_like_to_user, dislike_user
from app.application.api.v1.likes.schemas import CreateLikeRequestSchema, CreateLikeResponseSchema


class MeLikeRequestSchema(BaseModel):
    to_user: int
    is_superlike: bool = False


class MeDislikeRequestSchema(BaseModel):
    to_user: int
from app.application.api.v1.users.handlers import get_users_best_result
from app.application.api.v1.users.schemas import GetUsersFromResponseSchema
from app.domain.exceptions.base import ApplicationException
from app.logic.init import init_container
from app.logic.services.base import BaseLikesService, BaseUsersService
from app.settings.config import Config


router = APIRouter(prefix="/me", tags=["Me"])


@router.get("/best_result", response_model=GetUsersFromResponseSchema)
async def me_best_result(
    telegram_id: int = Depends(get_current_user),
    container: Container = Depends(init_container),
):
    """Best result для текущего пользователя из сессии."""
    return await get_users_best_result(user_id=telegram_id, container=container)


@router.get("/matches")
async def me_matches(
    telegram_id: int = Depends(get_current_user),
    container: Container = Depends(init_container),
):
    """Матчи текущего пользователя."""
    service: BaseLikesService = container.resolve(BaseLikesService)
    users_service: BaseUsersService = container.resolve(BaseUsersService)
    config: Config = container.resolve(Config)
    try:
        liked_by_me = set(await service.get_telegram_id_liked_from(user_id=telegram_id))
        liked_me = set(await service.get_users_ids_liked_by(user_id=telegram_id))
        mutual_ids = list(liked_by_me & liked_me)
        users = await users_service.get_users_liked_from(users_list=mutual_ids)
    except ApplicationException as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail={"error": exc.message})
    from app.application.api.v1.users.schemas import UserDetailSchema
    from app.application.api.lifespan import get_bot_username
    bot_username = config.bot_username or get_bot_username()
    return {
        "items": [UserDetailSchema.from_entity(u) for u in users],
        "bot_username": bot_username,
    }


@router.post("/likes", response_model=CreateLikeResponseSchema)
async def me_add_like(
    schema: MeLikeRequestSchema,
    telegram_id: int = Depends(get_current_user),
    container: Container = Depends(init_container),
):
    """Лайк от текущего пользователя — from_user из сессии."""
    full_schema = CreateLikeRequestSchema(from_user=telegram_id, to_user=schema.to_user, is_superlike=schema.is_superlike)
    return await add_like_to_user(schema=full_schema, container=container)


@router.post("/dislike")
async def me_dislike(
    schema: MeDislikeRequestSchema,
    telegram_id: int = Depends(get_current_user),
    container: Container = Depends(init_container),
):
    """Дизлайк от текущего пользователя."""
    full_schema = CreateLikeRequestSchema(from_user=telegram_id, to_user=schema.to_user)
    return await dislike_user(schema=full_schema, container=container)
