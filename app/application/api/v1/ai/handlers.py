"""
AI Icebreaker — генератор первых сообщений с выбором темы, vision-анализом
фото и лимитами использования.
"""
import json
import logging
import random
from datetime import date

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from punq import Container

from app.application.api.schemas import ErrorSchema
from app.domain.exceptions.base import ApplicationException
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService
from app.settings.config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])

# ─── Темы ────────────────────────────────────────────────────────────────────

TOPIC_PROMPTS: dict[str, str] = {
    "humor": (
        "Напиши смешное и остроумное первое сообщение. "
        "Используй лёгкий юмор, основанный на деталях профиля или внешности человека. "
        "Шутка должна быть доброй, не обидной."
    ),
    "compliment": (
        "Напиши искренний, запоминающийся комплимент. "
        "Обрати внимание на внешность (если видишь фото), стиль или что-то особенное в профиле. "
        "Комплимент должен быть конкретным — не 'ты красивая', а что именно зацепило."
    ),
    "intrigue": (
        "Напиши загадочное, интригующее сообщение, которое вызовет любопытство и желание ответить. "
        "Можно начать с неожиданного вопроса или наблюдения. "
        "Пусть собеседник захочет узнать продолжение."
    ),
    "common": (
        "Найди что-то общее: город, возраст, интересы из описания профиля. "
        "Напиши сообщение, которое показывает, что вы похожи или можете найти общий язык. "
        "Создай ощущение: 'мы точно поладим'."
    ),
    "direct": (
        "Напиши прямолинейное, честное сообщение о том, что человек понравился. "
        "Без лишних слов, но с теплотой. Смелость ценится — пусть это чувствуется в тексте."
    ),
}

TOPIC_LABELS: dict[str, str] = {
    "humor": "😄 Шутка",
    "compliment": "💫 Комплимент",
    "intrigue": "🧩 Интрига",
    "common": "🌍 Найти общее",
    "direct": "🔥 Прямолинейно",
}

# ─── Fallback сообщения (без OpenAI) ─────────────────────────────────────────

FALLBACK: dict[str, list[str]] = {
    "humor": [
        "Слушай, профиль такой интересный — даже алгоритм запутался, с чего начать 😄",
        "Твоя анкета нарушила мой скролл-ритм. Это комплимент, если что.",
        "Говорят, хорошие вещи приходят к тем, кто ждёт. Подождал — и вот ты 😄",
    ],
    "compliment": [
        "Что-то в твоём профиле сразу цепляет — не могу пройти мимо.",
        "Серьёзно, у тебя очень приятная энергетика даже через экран.",
        "Такие анкеты хочется сохранить 💫",
    ],
    "intrigue": [
        "У меня есть теория насчёт тебя. Хочешь узнать?",
        "Если бы мы встретились в реальной жизни — думаю, это была бы хорошая история.",
        "Что-то мне подсказывает, что разговор с тобой будет интересным. Проверим? 🧩",
    ],
    "common": [
        "Мы из одного города — значит, уже есть о чём поговорить!",
        "Смотрю на твой профиль и думаю: мы точно нашли бы общий язык.",
        "Что-то общее есть точно — хотя бы то, что мы оба здесь 😊",
    ],
    "direct": [
        "Ты мне понравилась. Хочу познакомиться.",
        "Не буду ходить вокруг да около — ты классная. Привет!",
        "Увидел тебя и сразу понял, что хочу написать. Так и сделал.",
    ],
}


def _get_fallbacks(name: str, topic: str) -> list[str]:
    base = FALLBACK.get(topic, FALLBACK["direct"])
    result = []
    for msg in base:
        result.append(msg.replace("тебя", name) if random.random() > 0.5 else msg)
    return result[:3]


# ─── Schemas ─────────────────────────────────────────────────────────────────

class IcebreakerRequest(BaseModel):
    sender_id: int
    target_id: int
    topic: str = "direct"  # humor / compliment / intrigue / common / direct


class IcebreakerResponse(BaseModel):
    variants: list[str]
    uses_left: int
    is_premium: bool


class IcebreakerSendRequest(BaseModel):
    sender_id: int
    target_id: int
    message: str


class IcebreakerSendResponse(BaseModel):
    success: bool


class ProfileTipsResponse(BaseModel):
    tips: list[str]
    score: int


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_limit(premium_type: str | None, config: Config) -> int:
    """Возвращает лимит для пользователя (всего для free, в день для подписчиков)."""
    if premium_type == "vip":
        return config.icebreaker_daily_vip
    if premium_type == "premium":
        return config.icebreaker_daily_premium
    return config.icebreaker_free_total


def _get_uses_left(used: int, limit: int) -> int:
    return max(0, limit - used)


async def _fetch_photo_base64(photo_url: str) -> str | None:
    """Загружает фото по URL и возвращает base64."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(photo_url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    import base64
                    data = await resp.read()
                    return base64.b64encode(data).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to fetch photo for vision: {e}")
    return None


async def _generate_with_openai(
    api_key: str,
    profile_info: str,
    photo_base64: str | None,
    topic: str,
) -> list[str]:
    """Вызывает OpenAI с vision (если фото доступно) и возвращает 3 варианта."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)

    topic_instruction = TOPIC_PROMPTS.get(topic, TOPIC_PROMPTS["direct"])

    system_prompt = (
        "Ты — эксперт по первым сообщениям для знакомств. "
        "Генерируй короткие (1-3 предложения), живые и оригинальные сообщения на русском языке. "
        "Никаких шаблонов вроде 'привет, как дела?'. "
        "Каждое сообщение должно быть уникальным и заряженным. "
        "Верни ровно 3 варианта в формате JSON-массива строк: [\"вариант 1\", \"вариант 2\", \"вариант 3\"]. "
        "Никаких пояснений — только JSON."
    )

    user_text = (
        f"Профиль человека: {profile_info}\n\n"
        f"Задача: {topic_instruction}\n\n"
        "Дай 3 разных варианта первого сообщения."
    )

    # Строим content: с картинкой или без
    if photo_base64:
        user_content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{photo_base64}",
                    "detail": "low",
                },
            },
            {"type": "text", "text": user_text},
        ]
        model = "gpt-4o-mini"
    else:
        user_content = user_text
        model = "gpt-4o-mini"

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=400,
        temperature=0.95,
    )

    raw = response.choices[0].message.content.strip()

    # Парсим JSON массив
    try:
        # Убираем возможные markdown блоки
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        variants = json.loads(raw)
        if isinstance(variants, list) and len(variants) >= 1:
            return [str(v).strip() for v in variants[:3]]
    except Exception:
        pass

    # Fallback: возвращаем весь текст как один вариант
    return [raw[:200] if raw else "Привет! Твой профиль меня заинтересовал."]


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
    "/icebreaker",
    status_code=status.HTTP_200_OK,
    description="Генерирует 3 варианта первого сообщения с выбором темы. Лимит: 5 для новых, 5/день для Premium, 10/день для VIP.",
    responses={
        status.HTTP_200_OK: {"model": IcebreakerResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def generate_icebreaker(
    data: IcebreakerRequest,
    container: Container = Depends(init_container),
) -> IcebreakerResponse:
    config: Config = container.resolve(Config)
    service: BaseUsersService = container.resolve(BaseUsersService)

    # Проверяем отправителя
    try:
        sender = await service.get_user(telegram_id=data.sender_id)
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": e.message})

    # Проверяем цель
    try:
        target = await service.get_user(telegram_id=data.target_id)
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": e.message})

    premium_type = getattr(sender, "premium_type", None)
    is_premium = premium_type in ("premium", "vip")

    # Получаем использованное количество
    used = await service.get_icebreaker_count(telegram_id=data.sender_id)
    limit = _get_limit(premium_type, config)

    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "limit_exceeded", "uses_left": 0, "is_premium": is_premium},
        )

    topic = data.topic if data.topic in TOPIC_PROMPTS else "direct"

    # Строим info о профиле
    profile_info = f"Имя: {target.name}, Возраст: {target.age}, Город: {target.city}"
    if getattr(target, "about", None):
        profile_info += f", О себе: {target.about}"

    variants: list[str] = []

    if config.openai_api_key:
        try:
            # Пробуем загрузить фото для vision
            photo_base64 = None
            photo = getattr(target, "photo", None)
            if photo:
                photo_url = f"{config.url_webhook}/api/v1/users/{target.telegram_id}/photo"
                photo_base64 = await _fetch_photo_base64(photo_url)

            variants = await _generate_with_openai(
                api_key=config.openai_api_key,
                profile_info=profile_info,
                photo_base64=photo_base64,
                topic=topic,
            )
        except Exception as e:
            logger.error(f"OpenAI icebreaker error: {e}")
            variants = _get_fallbacks(target.name, topic)
    else:
        variants = _get_fallbacks(target.name, topic)

    # Гарантируем 3 варианта
    while len(variants) < 3:
        fb = _get_fallbacks(target.name, topic)
        for f in fb:
            if f not in variants:
                variants.append(f)
                if len(variants) == 3:
                    break

    # Инкрементируем счётчик ПОСЛЕ успешной генерации
    new_used = await service.increment_icebreaker_count(telegram_id=data.sender_id)
    uses_left = _get_uses_left(new_used, limit)

    return IcebreakerResponse(
        variants=variants[:3],
        uses_left=uses_left,
        is_premium=is_premium,
    )


@router.post(
    "/icebreaker/send",
    status_code=status.HTTP_200_OK,
    description="Отправляет выбранный вариант icebreaker целевому пользователю через бот.",
    responses={
        status.HTTP_200_OK: {"model": IcebreakerSendResponse},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def send_icebreaker(
    data: IcebreakerSendRequest,
    container: Container = Depends(init_container),
) -> IcebreakerSendResponse:
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        sender = await service.get_user(telegram_id=data.sender_id)
        target = await service.get_user(telegram_id=data.target_id)
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": e.message})

    try:
        from app.bot.utils.notificator import send_icebreaker_message
        await send_icebreaker_message(
            target_id=data.target_id,
            message=data.message,
            sender=sender,
        )
        return IcebreakerSendResponse(success=True)
    except Exception as e:
        logger.error(f"Failed to send icebreaker message: {e}")
        return IcebreakerSendResponse(success=False)


@router.get(
    "/icebreaker/status/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Возвращает оставшийся лимит icebreakers для пользователя.",
)
async def get_icebreaker_status(
    user_id: int,
    container: Container = Depends(init_container),
):
    config: Config = container.resolve(Config)
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        user = await service.get_user(telegram_id=user_id)
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": e.message})

    premium_type = getattr(user, "premium_type", None)
    is_premium = premium_type in ("premium", "vip")
    used = await service.get_icebreaker_count(telegram_id=user_id)
    limit = _get_limit(premium_type, config)
    uses_left = _get_uses_left(used, limit)

    return {
        "uses_left": uses_left,
        "limit": limit,
        "used": used,
        "is_premium": is_premium,
    }


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
