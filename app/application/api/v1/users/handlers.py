import aiohttp

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import RedirectResponse
from fastapi.routing import APIRouter

from punq import Container

from app.application.api.schemas import ErrorSchema
from app.application.api.v1.users.filters import GetUsersFilters
from app.application.api.v1.users.schemas import (
    GetUsersFromResponseSchema,
    GetUsersResponseSchema,
    UserDetailSchema,
)
from app.domain.exceptions.base import ApplicationException
from app.logic.init import init_container
from app.logic.services.base import (
    BaseLikesService,
    BaseUsersService,
)
from app.settings.config import Config


router = APIRouter(
    prefix="/users",
    tags=["User"],
)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    description="Get all users list.",
    responses={
        status.HTTP_200_OK: {"model": GetUsersResponseSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def get_all_users_handler(
    filters: GetUsersFilters = Depends(),
    container: Container = Depends(init_container),
) -> GetUsersResponseSchema:
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        users, count = await service.get_all_users(filters=filters.to_infra())
    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    return GetUsersResponseSchema(
        count=count,
        limit=filters.limit,
        offset=filters.offset,
        items=[UserDetailSchema.from_entity(user) for user in users],
    )


@router.get(
    "/{user_id}/photo",
    status_code=status.HTTP_302_FOUND,
    description="Get user photo by redirecting to Telegram file URL.",
    include_in_schema=False,
)
async def get_user_photo(
    user_id: int,
    container: Container = Depends(init_container),
):
    service: BaseUsersService = container.resolve(BaseUsersService)
    config: Config = container.resolve(Config)

    try:
        user = await service.get_user(telegram_id=user_id)
    except ApplicationException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    photo = user.photo
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No photo")

    # Если уже HTTP URL — просто редиректим
    if photo.startswith("http"):
        return RedirectResponse(url=photo)

    # Это Telegram file_id — получаем реальный URL через Bot API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.telegram.org/bot{config.token}/getFile",
                params={"file_id": photo},
            ) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
                file_path = data["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{config.token}/{file_path}"
                return RedirectResponse(url=file_url)
    except aiohttp.ClientError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram API error")


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Get information about the users.",
    responses={
        status.HTTP_200_OK: {"model": UserDetailSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def get_user_handler(
    user_id: int,
    container: Container = Depends(init_container),
) -> UserDetailSchema:
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        user = await service.get_user(telegram_id=user_id)
    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    return UserDetailSchema.from_entity(user)


@router.get(
    "/best_result/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Get best result for user (excludes already-liked profiles).",
    responses={
        status.HTTP_200_OK: {"model": GetUsersFromResponseSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def get_users_best_result(
    user_id: int,
    container: Container = Depends(init_container),
) -> GetUsersFromResponseSchema:
    service_users: BaseUsersService = container.resolve(BaseUsersService)
    service_likes: BaseLikesService = container.resolve(BaseLikesService)

    try:
        already_liked = await service_likes.get_telegram_id_liked_from(user_id=user_id)
        users = await service_users.get_best_result_for_user(user_id, exclude_ids=already_liked)
    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    return GetUsersFromResponseSchema(
        items=[UserDetailSchema.from_entity(user) for user in users],
    )


@router.get(
    "/from/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Get all users that the user liked.",
    responses={
        status.HTTP_200_OK: {"model": GetUsersFromResponseSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def get_users_liked_from(
    user_id: int,
    container: Container = Depends(init_container),
) -> GetUsersFromResponseSchema:
    service_likes: BaseLikesService = container.resolve(BaseLikesService)
    service_users: BaseUsersService = container.resolve(BaseUsersService)

    try:
        telegram_ids = await service_likes.get_telegram_id_liked_from(
            user_id=user_id,
        )
        users = await service_users.get_users_liked_from(users_list=telegram_ids)
    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    return GetUsersFromResponseSchema(
        items=[UserDetailSchema.from_entity(user) for user in users],
    )


@router.get(
    "/by/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Get all users that liked the user.",
    responses={
        status.HTTP_200_OK: {"model": GetUsersFromResponseSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def get_users_liked_by(
    user_id: int,
    container: Container = Depends(init_container),
) -> GetUsersFromResponseSchema:
    service_likes: BaseLikesService = container.resolve(BaseLikesService)
    service_users: BaseUsersService = container.resolve(BaseUsersService)

    try:
        telegram_ids = await service_likes.get_users_ids_liked_by(
            user_id=user_id,
        )
        users = await service_users.get_users_liked_by(users_list=telegram_ids)
    except ApplicationException as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exception.message},
        )

    return GetUsersFromResponseSchema(
        items=[UserDetailSchema.from_entity(user) for user in users],
    )
