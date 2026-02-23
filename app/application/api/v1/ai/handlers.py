from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from punq import Container

from app.application.api.schemas import ErrorSchema
from app.domain.exceptions.base import ApplicationException
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService
from app.settings.config import Config


router = APIRouter(prefix="/ai", tags=["AI"])


class IcebreakerRequest(BaseModel):
    sender_id: int
    target_id: int


class IcebreakerResponse(BaseModel):
    message: str


class ProfileTipsResponse(BaseModel):
    tips: list[str]
    score: int


@router.post(
    "/icebreaker",
    status_code=status.HTTP_200_OK,
    description="Генерирует первое сообщение с помощью AI на основе профиля собеседника",
    responses={
        status.HTTP_200_OK: {"model": IcebreakerResponse},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def generate_icebreaker(
    data: IcebreakerRequest,
    container: Container = Depends(init_container),
) -> IcebreakerResponse:
    config: Config = container.resolve(Config)
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        target = await service.get_user(telegram_id=data.target_id)
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": e.message})

    if not config.openai_api_key:
        fallback_messages = [
            f"Привет, {target.name}! Твой профиль меня заинтересовал — расскажи о себе побольше?",
            f"{target.name}, привет! Мы из одного города — как тебе здесь живётся?",
            f"Привет! Увидел твою анкету и захотел познакомиться. Как проходит твой день?",
        ]
        import random
        return IcebreakerResponse(message=random.choice(fallback_messages))

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=config.openai_api_key)

        profile_info = f"Имя: {target.name}, Возраст: {target.age}, Город: {target.city}"
        if target.about:
            profile_info += f", О себе: {target.about}"

        response = await client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты помощник для знакомств. Генерируй короткие (1-2 предложения), "
                        "тёплые и оригинальные первые сообщения для знакомства на русском языке. "
                        "Не используй шаблонные фразы вроде 'привет, как дела?'. "
                        "Опирайся на информацию из профиля собеседника."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Напиши первое сообщение для знакомства с этим человеком: {profile_info}",
                },
            ],
            max_tokens=100,
            temperature=0.9,
        )
        message = response.choices[0].message.content.strip()
        return IcebreakerResponse(message=message)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"AI сервис недоступен: {str(e)}"},
        )


@router.get(
    "/profile-tips/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Анализирует профиль и даёт советы по улучшению",
    responses={
        status.HTTP_200_OK: {"model": ProfileTipsResponse},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def get_profile_tips(
    user_id: int,
    container: Container = Depends(init_container),
) -> ProfileTipsResponse:
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        user = await service.get_user(telegram_id=user_id)
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": e.message})

    tips = []
    score = 0

    if user.photo:
        score += 30
    else:
        tips.append("Добавь фото — анкеты с фото получают в 10 раз больше лайков")

    if user.about and len(user.about) > 50:
        score += 30
    elif user.about:
        score += 15
        tips.append("Расширь раздел 'О себе' — напиши хотя бы 50 символов")
    else:
        tips.append("Заполни раздел 'О себе' — это делает анкету в 3 раза привлекательнее")

    if user.city:
        score += 20
    else:
        tips.append("Укажи город — пользователи ищут людей рядом")

    if user.age:
        score += 20
    else:
        tips.append("Укажи возраст")

    if not tips:
        tips.append("Твой профиль отлично заполнен! Регулярно обновляй фото для лучших результатов.")

    return ProfileTipsResponse(tips=tips, score=min(score, 100))
