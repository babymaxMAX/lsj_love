from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from punq import Container

from app.application.api.schemas import ErrorSchema
from app.domain.exceptions.base import ApplicationException
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService


router = APIRouter(prefix="/gamification", tags=["Gamification"])

DAILY_QUESTIONS = [
    "Что для тебя важнее: карьера или семья?",
    "Идеальные выходные — это...",
    "Твоя любимая кухня мира?",
    "Ты жаворонок или сова?",
    "Что не простишь партнёру никогда?",
    "Море или горы?",
    "Домашнее животное — за или против?",
    "Твоя суперсила если бы она была?",
    "Что тебя сразу привлекает в людях?",
    "Любимый способ снять стресс?",
    "Путешествия или уют дома?",
    "Что ты ценишь в дружбе больше всего?",
    "Твой идеальный первый свидание?",
    "Спорт в жизни — насколько важен?",
    "Чем ты увлекаешься помимо работы?",
]


class DailyQuestionResponse(BaseModel):
    question: str
    question_id: int
    date: str


class StreakResponse(BaseModel):
    streak_days: int
    last_active: str
    bonus_likes: int


class HotRatingResponse(BaseModel):
    users: list[dict]


@router.get(
    "/daily-question",
    status_code=status.HTTP_200_OK,
    description="Возвращает вопрос дня",
    responses={status.HTTP_200_OK: {"model": DailyQuestionResponse}},
)
async def get_daily_question() -> DailyQuestionResponse:
    today = datetime.now(timezone.utc)
    question_id = today.timetuple().tm_yday % len(DAILY_QUESTIONS)
    return DailyQuestionResponse(
        question=DAILY_QUESTIONS[question_id],
        question_id=question_id,
        date=today.strftime("%Y-%m-%d"),
    )


@router.post(
    "/checkin/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Ежедневный чекин — обновляет streak",
    responses={
        status.HTTP_200_OK: {"model": StreakResponse},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def daily_checkin(
    user_id: int,
    container: Container = Depends(init_container),
) -> StreakResponse:
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        await service.get_user(telegram_id=user_id)
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": e.message})

    now = datetime.now(timezone.utc)
    streak_days = 1
    bonus_likes = min(streak_days, 5)

    return StreakResponse(
        streak_days=streak_days,
        last_active=now.isoformat(),
        bonus_likes=bonus_likes,
    )


@router.get(
    "/hot-rating",
    status_code=status.HTTP_200_OK,
    description="Топ-10 популярных профилей сегодня",
    responses={status.HTTP_200_OK: {"model": HotRatingResponse}},
)
async def get_hot_rating(
    container: Container = Depends(init_container),
) -> HotRatingResponse:
    service: BaseUsersService = container.resolve(BaseUsersService)

    from app.infra.repositories.filters.users import GetAllUsersFilters
    users = await service.get_all_users(
        filters=GetAllUsersFilters(limit=10, offset=0)
    )

    result = []
    for i, user in enumerate(users[0] if isinstance(users, tuple) else users):
        result.append({
            "rank": i + 1,
            "name": user.name,
            "age": user.age,
            "city": user.city,
            "photo": user.photo,
            "telegram_id": user.telegram_id,
        })

    return HotRatingResponse(users=result)
