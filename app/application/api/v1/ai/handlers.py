"""
AI Icebreaker — генератор первых сообщений с выбором темы, vision-анализом
фото и лимитами использования.
AI Советник диалога — чат-ассистент для помощи в переписке (VIP или 24ч пробный).
"""
import json
import logging
import random
from datetime import date, datetime, timezone
from math import radians, sin, cos, sqrt, atan2

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


# ─── Геолокация ──────────────────────────────────────────────────────────────

async def get_city_coordinates(city: str) -> tuple[float, float] | None:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": city, "format": "json", "limit": 1}
    headers = {"User-Agent": "LSJLove/1.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                data = await resp.json()
                if data:
                    return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


async def get_cached_coordinates(city: str, db) -> tuple[float, float] | None:
    if not city:
        return None
    cached = await db.city_coordinates.find_one({"city": city})
    if cached:
        return cached["lat"], cached["lon"]
    coords = await get_city_coordinates(city)
    if coords:
        await db.city_coordinates.insert_one({"city": city, "lat": coords[0], "lon": coords[1]})
    return coords


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

def _is_premium_active(user, required_type: str | None = None) -> bool:
    """Проверяет активна ли подписка (с учётом срока premium_until)."""
    pt = getattr(user, "premium_type", None)
    until = getattr(user, "premium_until", None)
    if not pt or not until:
        return False
    if hasattr(until, "tzinfo") and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) >= until:
        return False
    return required_type is None or pt == required_type


def _get_active_premium_type(user) -> str | None:
    """Возвращает тип подписки если она активна, иначе None."""
    if _is_premium_active(user):
        return getattr(user, "premium_type", None)
    return None


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

    premium_type = _get_active_premium_type(sender)
    is_premium = premium_type in ("premium", "vip")

    # Получаем использованное количество (с daily reset для подписчиков)
    used = await service.get_icebreaker_count(telegram_id=data.sender_id)
    limit = _get_limit(premium_type, config)

    # Daily reset для premium/vip пользователей
    if is_premium and used >= limit:
        from motor.motor_asyncio import AsyncIOMotorClient
        client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
        col = client[config.mongodb_dating_database][config.mongodb_users_collection]
        user_doc = await col.find_one({"telegram_id": data.sender_id}, {"icebreaker_reset_date": 1})
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        last_reset = (user_doc or {}).get("icebreaker_reset_date", "")
        if last_reset != today_str:
            await col.update_one(
                {"telegram_id": data.sender_id},
                {"$set": {"icebreaker_used": 0, "icebreaker_reset_date": today_str}},
            )
            used = 0

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

    premium_type = _get_active_premium_type(user)
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


# ─── AI Советник диалога ─────────────────────────────────────────────────────

ADVISOR_TRIAL_SECONDS = 86400  # 24 часа пробный период


class DialogMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class DialogAdvisorRequest(BaseModel):
    user_id: int
    message: str = ""
    image_base64: str | None = None
    history: list[DialogMessage] = []


class DialogAdvisorResponse(BaseModel):
    reply: str
    is_vip: bool
    trial_active: bool
    trial_hours_left: float | None = None


class AdvisorStatusResponse(BaseModel):
    is_vip: bool
    trial_active: bool
    trial_hours_left: float | None = None
    trial_expired: bool
    vip_expired: bool = False   # True когда был VIP, но истёк


async def _generate_advisor_reply(
    api_key: str,
    message: str,
    image_base64: str | None,
    history: list[DialogMessage],
) -> str:
    """Вызывает OpenAI для советника диалога."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)

    system_prompt = (
        "Ты — AI Советник по знакомствам и общению. Твоя задача — помогать пользователю "
        "выстраивать диалог с человеком, который ему нравится.\n"
        "Если пользователь прислал скриншот переписки — проанализируй его, объясни что "
        "происходит в диалоге и предложи 2-3 конкретных варианта следующего сообщения.\n"
        "Если пользователь описывает ситуацию словами — дай конкретные советы и варианты реплик.\n"
        "Веди себя как умный и тактичный друг, а не как психолог.\n"
        "Будь конкретным: предлагай готовые фразы, которые можно скопировать и отправить.\n"
        "Отвечай на русском языке. Форматируй ответ читабельно — используй эмодзи и абзацы."
    )

    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    # Добавляем историю (последние 12 сообщений для контекста, пропускаем пустые)
    for h in history[-12:]:
        if h.content and h.content.strip():
            messages.append({"role": h.role, "content": h.content})

    # Текущее сообщение
    if image_base64:
        user_content: list | str = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_base64}",
                    "detail": "high",
                },
            },
            {"type": "text", "text": message or "Проанализируй эту переписку и помоги мне ответить."},
        ]
    else:
        user_content = message or "Помоги мне с диалогом."

    messages.append({"role": "user", "content": user_content})

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=700,
        temperature=0.8,
    )
    return response.choices[0].message.content.strip()


def _get_trial_info(trial_start) -> tuple[bool, float | None]:
    """Возвращает (trial_active, hours_left). trial_active=False если истёк."""
    if trial_start is None:
        return True, 24.0  # Ещё не начинал — у него ещё есть 24ч
    ts = trial_start
    if hasattr(ts, "tzinfo") and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - ts).total_seconds()
    if elapsed >= ADVISOR_TRIAL_SECONDS:
        return False, 0.0
    hours_left = (ADVISOR_TRIAL_SECONDS - elapsed) / 3600
    return True, round(hours_left, 1)


@router.get(
    "/dialog-advisor/status/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Возвращает статус доступа к AI Советнику диалога.",
)
async def get_advisor_status(
    user_id: int,
    container: Container = Depends(init_container),
) -> AdvisorStatusResponse:
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        user = await service.get_user(telegram_id=user_id)
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": e.message})

    is_vip = _is_premium_active(user, "vip")

    if is_vip:
        return AdvisorStatusResponse(
            is_vip=True,
            trial_active=False,
            trial_hours_left=None,
            trial_expired=False,
        )

    # Если пользователь когда-либо был VIP, но подписка истекла — не даём trial
    had_vip = getattr(user, "premium_type", None) == "vip"
    if had_vip:
        return AdvisorStatusResponse(
            is_vip=False,
            trial_active=False,
            trial_hours_left=None,
            trial_expired=True,
            vip_expired=True,
        )

    trial_start = await service.get_advisor_trial_start(telegram_id=user_id)
    trial_active, hours_left = _get_trial_info(trial_start)

    return AdvisorStatusResponse(
        is_vip=False,
        trial_active=trial_active,
        trial_hours_left=hours_left if trial_active else None,
        trial_expired=not trial_active,
        vip_expired=False,
    )


@router.post(
    "/dialog-advisor",
    status_code=status.HTTP_200_OK,
    description="AI Советник диалога. VIP — безлимит, остальным — 24ч пробный доступ.",
    responses={
        status.HTTP_200_OK: {"model": DialogAdvisorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorSchema},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
    },
)
async def dialog_advisor(
    data: DialogAdvisorRequest,
    container: Container = Depends(init_container),
) -> DialogAdvisorResponse:
    config: Config = container.resolve(Config)
    service: BaseUsersService = container.resolve(BaseUsersService)

    try:
        user = await service.get_user(telegram_id=data.user_id)
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": e.message})

    is_vip = _is_premium_active(user, "vip")

    if not is_vip:
        # Если пользователь был VIP, но подписка истекла — не даём trial, требуем продлить
        had_vip = getattr(user, "premium_type", None) == "vip"
        if had_vip:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Подписка VIP истекла. Обнови VIP для доступа к AI Советнику диалога."},
            )

        trial_start = await service.get_advisor_trial_start(telegram_id=data.user_id)
        if trial_start is None:
            await service.set_advisor_trial_start(telegram_id=data.user_id)
            trial_start = datetime.now(timezone.utc)

        trial_active, hours_left = _get_trial_info(trial_start)

        if not trial_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Пробный период истёк. Получи VIP для безлимитного доступа."},
            )
    else:
        trial_active = False
        hours_left = None

    if not config.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "OpenAI не настроен"},
        )

    try:
        reply = await _generate_advisor_reply(
            api_key=config.openai_api_key,
            message=data.message,
            image_base64=data.image_base64,
            history=data.history,
        )
    except Exception as e:
        err_str = str(e)
        logger.error(f"OpenAI dialog-advisor error: {err_str}")
        # Передаём понятное сообщение на клиент
        if "api_key" in err_str.lower() or "authentication" in err_str.lower() or "401" in err_str:
            detail_msg = "OpenAI API ключ недействителен. Обновите OPENAI_API_KEY в .env"
        elif "quota" in err_str.lower() or "429" in err_str:
            detail_msg = "Лимит OpenAI исчерпан. Проверьте баланс аккаунта."
        elif "model" in err_str.lower():
            detail_msg = f"Ошибка модели: {err_str[:120]}"
        else:
            detail_msg = f"Ошибка генерации: {err_str[:150]}"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": detail_msg},
        )

    return DialogAdvisorResponse(
        reply=reply,
        is_vip=is_vip,
        trial_active=not is_vip,
        trial_hours_left=hours_left,
    )


# ─── AI Подбор (Matchmaking) ──────────────────────────────────────────────────

class MatchmakingRequest(BaseModel):
    user_id: int
    message: str
    conversation: list[dict] = []   # [{"role": "user"|"assistant", "content": str}]
    shown_ids: list[int] = []       # ID анкет, уже показанных пользователю


class MatchmakingResponse(BaseModel):
    reply: str
    matches: list   # List of UserDetailSchema dicts


async def _s3_download_bytes(key: str, config: Config) -> bytes | None:
    """Загружает файл из S3 по ключу и возвращает bytes."""
    try:
        from aiobotocore.session import get_session
        session = get_session()
        async with session.create_client(
            "s3",
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
            region_name=config.region_name,
            endpoint_url=config.s3_endpoint_url,
        ) as client:
            resp = await client.get_object(Bucket=config.bucket_name, Key=key)
            data = await resp["Body"].read()
            return data
    except Exception as e:
        logger.warning(f"S3 download failed for key={key}: {e}")
        return None


def _clean_reply(text: str) -> str:
    """Убирает markdown-блоки кода и JSON-хвосты из ответа модели."""
    import re
    # Убираем ```json ... ``` и ``` ... ```
    text = re.sub(r"```[a-z]*\n?", "", text)
    text = text.strip().rstrip("`").strip()
    # Убираем JSON-объект в конце если он остался
    text = re.sub(r"\{[^{}]*\"matches\"\s*:\s*\[[^\]]*\][^{}]*\}\s*$", "", text).strip()
    return text


async def _matchmaking_text_screen(
    candidates_text: str,
    user_criteria: str,
    conversation: list[dict],
    shown_ids: list[int],
    api_key: str,
    user_info: str = "",
) -> list[int]:
    """
    Шаг 1: Текстовый скрининг — GPT-4o-mini выбирает топ-10 ID по критериям пользователя.
    Возвращает список telegram_id.
    """
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)

    shown_note = f"\nУже показанные пользователю (не повторяй): {shown_ids}" if shown_ids else ""
    user_context = f"\nИнформация о пользователе, который ищет: {user_info}" if user_info else ""

    system = (
        "Ты — умный и дружелюбный помощник по подбору пар в приложении знакомств LSJLove. "
        "Пользователь описывает, кого ищет. Тебе дан список анкет с ID, именем, возрастом, городом, описанием, "
        "типом подписки и ответами на вопросы профиля.\n\n"
        "Ты отлично понимаешь разговорный русский язык и неформальные описания внешности.\n"
        "Словарь синонимов телосложения — считай их одинаковыми:\n"
        "- 'пышная', 'в теле', 'покрупнее', 'не худая', 'полная', 'пухленькая', 'пухлая', 'крупная', "
        "'с формами', 'аппетитная' → телосложение: пышное/плюс-сайз\n"
        "- 'стройная', 'худая', 'тонкая', 'субтильная', 'хрупкая' → телосложение: стройное\n"
        "- 'спортивная', 'подтянутая', 'атлетичная' → телосложение: спортивное\n"
        "Словарь синонимов для волос:\n"
        "- 'рыжая', 'огненная', 'медная' → рыжие волосы\n"
        "- 'блондинка', 'светлая', 'белокурая' → светлые волосы\n"
        "- 'брюнетка', 'тёмная', 'чернявая' → тёмные волосы\n"
        "ВАЖНО: если пользователь пишет 'найди кого покрупнее' или 'она какая-то худая' — это значит он хочет "
        "пышную девушку. Никогда не отвечай 'не нашёл' только из-за нестандартной формулировки — "
        "всегда интерпретируй смысл запроса и ищи подходящих.\n\n"
        "Правила подбора:\n"
        "- Совпадение города — большой плюс, приоритизируй кандидатов из того же города\n"
        "- Учитывай возраст, описание (about), ответы на вопросы профиля для совместимости\n"
        "- Понимай разговорный язык и неточные описания ('добрая', 'весёлая', 'серьёзная')\n"
        "- Запрещено возвращать анкеты из списка shown_ids\n"
        "- Если пользователь уточняет критерии — ищи заново с учётом новых предпочтений\n"
        "Выбери до 10 НОВЫХ анкет, которые наилучшим образом соответствуют критериям. "
        "Ответь ТОЛЬКО JSON: {\"selected\": [id1, id2, ...]}"
    )

    messages: list[dict] = [{"role": "system", "content": system}]
    for h in conversation[-8:]:
        if h.get("content", "").strip():
            messages.append({"role": h["role"], "content": h["content"]})

    user_msg = (
        f"Критерии: {user_criteria}{shown_note}{user_context}\n\n"
        f"Доступные анкеты:\n{candidates_text}\n\n"
        "Верни JSON с отобранными ID."
    )
    messages.append({"role": "user", "content": user_msg})

    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=300,
        temperature=0.3,
    )
    raw = resp.choices[0].message.content.strip()

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
            return [int(i) for i in data.get("selected", [])]
    except Exception:
        pass
    return []


async def _matchmaking_vision_rank(
    candidates_info: list[dict],   # [{"id": int, "text": str, "photo_b64": str|None}]
    user_criteria: str,
    conversation: list[dict],
    shown_ids: list[int],
    api_key: str,
) -> tuple[list[int], str]:
    """
    Шаг 2: Vision-ранжирование — GPT-4o смотрит на фото + описания, выбирает топ 2-3.
    Возвращает (список ID, текст-объяснение для пользователя).
    """
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)

    shown_note = f" Не повторяй ID: {shown_ids}." if shown_ids else ""

    system = (
        "Ты — умный и дружелюбный помощник по подбору пар в приложении знакомств LSJLove. "
        "Общайся как живой человек-помощник, а не робот.\n\n"
        "ЗАДАЧА: Смотри на фотографии и описания кандидатов, выбери 2-3 анкеты которые подходят под критерии пользователя.\n\n"
        "VISION-АНАЛИЗ ФОТО (если есть):\n"
        "- Описывай внешность ОБЪЕКТИВНО: цвет и длина волос, телосложение, татуировки, стиль одежды, "
        "возраст на вид, общее впечатление\n"
        "- НЕ считай всех одинаково красивыми — делай объективные выводы на основе того что видишь\n"
        "- Если у анкеты пометка [фото недоступно] — анализируй ТОЛЬКО по тексту описания\n\n"
        "ПРАВИЛА:\n"
        "- Совпадение города — большой плюс\n"
        "- Учитывай возраст, описание (about), ответы на вопросы профиля\n"
        "- Если ни одна анкета НЕ подходит — честно скажи и предложи расширить критерии\n"
        "- НЕ показывай заведомо неподходящие анкеты\n"
        f"- Запрещено возвращать ID из списка: {shown_ids}\n\n"
        "ФОРМАТ ОТВЕТА:\n"
        "Напиши 1-2 коротких предложения объяснения (живым языком, с эмодзи).\n"
        "Затем на новой строке ТОЛЬКО: {\"matches\": [id1, id2]} (или [] если нет подходящих)"
    )

    messages: list[dict] = [{"role": "system", "content": system}]
    for h in conversation[-8:]:
        c = h.get("content", "")
        # Пропускаем служебные пометки о показанных анкетах
        if c.strip() and "[Показано" not in c:
            messages.append({"role": h["role"], "content": c})

    content: list[dict] = [
        {"type": "text", "text": f"Запрос пользователя: {user_criteria}\n\nАнкеты:"}
    ]

    for idx, c in enumerate(candidates_info, 1):
        content.append({"type": "text", "text": f"\n[Анкета ID={c['id']}] {c['text']}"})
        if c.get("photo_b64"):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{c['photo_b64']}",
                    "detail": "low",
                }
            })
        elif c.get("photo_url"):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": c["photo_url"],
                    "detail": "low",
                }
            })

    content.append({"type": "text", "text": f'\nВыбери 2-3 анкеты. Ответ: текст + {{"matches": [ids]}}'})
    messages.append({"role": "user", "content": content})

    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=500,
        temperature=0.6,
    )
    raw = resp.choices[0].message.content.strip()

    # Извлекаем JSON и очищаем текст
    matched_ids: list[int] = []
    reply_text = raw
    try:
        json_start = raw.rfind("{")
        json_end = raw.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            data = json.loads(raw[json_start:json_end])
            matched_ids = [int(i) for i in data.get("matches", [])]
            reply_text = raw[:json_start].strip()
    except Exception:
        pass

    reply_text = _clean_reply(reply_text)
    if not reply_text:
        reply_text = "Нашёл кое-кого интересного для тебя 💫"

    return matched_ids, reply_text


MATCHMAKING_TRIAL_SECONDS = 86400  # 24 часа


@router.get(
    "/matchmaking/status/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Проверяет доступ пользователя к AI-подбору (VIP или пробный 24ч).",
)
async def matchmaking_status(
    user_id: int,
    container: Container = Depends(init_container),
):
    service: BaseUsersService = container.resolve(BaseUsersService)
    try:
        user = await service.get_user(telegram_id=user_id)
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": e.message})

    is_vip = _is_premium_active(user, "vip")
    if is_vip:
        return {"access": True, "is_vip": True, "trial_active": False, "trial_hours_left": None, "trial_expired": False}

    from motor.motor_asyncio import AsyncIOMotorClient
    config: Config = container.resolve(Config)
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    col = client[config.mongodb_dating_database][config.mongodb_users_collection]
    doc = await col.find_one({"telegram_id": user_id}, {"matchmaking_trial_start": 1})
    trial_start = (doc or {}).get("matchmaking_trial_start")

    if trial_start is None:
        return {"access": True, "is_vip": False, "trial_active": True, "trial_hours_left": 24.0, "trial_expired": False}

    if hasattr(trial_start, "tzinfo") and trial_start.tzinfo is None:
        trial_start = trial_start.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - trial_start).total_seconds()
    if elapsed >= MATCHMAKING_TRIAL_SECONDS:
        return {"access": False, "is_vip": False, "trial_active": False, "trial_hours_left": 0, "trial_expired": True}

    hours_left = round((MATCHMAKING_TRIAL_SECONDS - elapsed) / 3600, 1)
    return {"access": True, "is_vip": False, "trial_active": True, "trial_hours_left": hours_left, "trial_expired": False}


@router.post(
    "/matchmaking",
    status_code=status.HTTP_200_OK,
    description="AI Подбор: анализирует критерии пользователя и возвращает подходящие анкеты. Доступ: VIP или 24ч пробный.",
)
async def ai_matchmaking(
    data: MatchmakingRequest,
    container: Container = Depends(init_container),
) -> MatchmakingResponse:
    config: Config = container.resolve(Config)
    service: BaseUsersService = container.resolve(BaseUsersService)

    if not config.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "OpenAI не настроен на сервере"},
        )

    # Загружаем текущего пользователя
    try:
        current_user = await service.get_user(telegram_id=data.user_id)
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": e.message})

    # ── Проверка доступа: VIP или 24ч пробный период ──
    is_vip = _is_premium_active(current_user, "vip")
    if not is_vip:
        from motor.motor_asyncio import AsyncIOMotorClient as _AMC
        _mc: _AMC = container.resolve(_AMC)
        _uc = _mc[config.mongodb_dating_database][config.mongodb_users_collection]
        _udoc = await _uc.find_one({"telegram_id": data.user_id}, {"matchmaking_trial_start": 1})
        trial_start = (_udoc or {}).get("matchmaking_trial_start")
        if trial_start is None:
            await _uc.update_one(
                {"telegram_id": data.user_id},
                {"$set": {"matchmaking_trial_start": datetime.now(timezone.utc)}},
            )
            trial_start = datetime.now(timezone.utc)
        else:
            if hasattr(trial_start, "tzinfo") and trial_start.tzinfo is None:
                trial_start = trial_start.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - trial_start).total_seconds()
            if elapsed >= 86400:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "trial_expired",
                        "message": "Пробный период AI-подбора истёк. Оформи VIP для безлимитного доступа.",
                    },
                )

    # shown_ids — анкеты уже показанные пользователю в этой сессии
    shown_ids: list[int] = list(set(data.shown_ids or []))

    # ── Загружаем ВСЕ активные анкеты напрямую из MongoDB (без фильтров по городу/полу) ──
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    db = mongo_client[config.mongodb_dating_database]
    users_col = db[config.mongodb_users_collection]

    all_users_cursor = users_col.find(
        {"is_active": True, "telegram_id": {"$ne": data.user_id}},
    )
    all_user_docs: list[dict] = []
    async for doc in all_users_cursor:
        if doc.get("profile_hidden"):
            continue
        all_user_docs.append(doc)

    # Исключаем shown_ids
    candidates_docs = [d for d in all_user_docs if d["telegram_id"] not in shown_ids]

    if not candidates_docs:
        if all_user_docs:
            candidates_docs = all_user_docs
        else:
            return MatchmakingResponse(
                reply="😔 Пока анкет нет. Зайди позже — новые появятся!",
                matches=[],
            )

    # ── Геосортировка: вычисляем расстояние от пользователя ──
    user_city = str(getattr(current_user, "city", "") or "")
    user_coords = await get_cached_coordinates(user_city, db) if user_city else None

    id_to_dist: dict[int, float | None] = {}
    for doc in candidates_docs:
        cand_city = str(doc.get("city", "") or "")
        if user_coords and cand_city:
            cand_coords = await get_cached_coordinates(cand_city, db)
            if cand_coords:
                id_to_dist[doc["telegram_id"]] = round(haversine_km(user_coords[0], user_coords[1], cand_coords[0], cand_coords[1]))
            else:
                id_to_dist[doc["telegram_id"]] = None
        else:
            id_to_dist[doc["telegram_id"]] = None

    candidates_docs.sort(key=lambda d: id_to_dist.get(d["telegram_id"]) or 99999)

    # ── Собираем profile_answers ──
    id_to_answers: dict[int, dict] = {}
    for doc in all_user_docs:
        id_to_answers[doc["telegram_id"]] = doc.get("profile_answers", {})

    current_user_doc = await users_col.find_one({"telegram_id": data.user_id}, {"profile_answers": 1})
    current_user_answers = (current_user_doc or {}).get("profile_answers", {})
    id_to_answers[data.user_id] = current_user_answers

    # Формируем info о текущем пользователе для AI
    from app.application.api.v1.profile_questions.handlers import PROFILE_QUESTIONS
    questions_map = {q["question_id"]: q for q in PROFILE_QUESTIONS}

    user_info_parts = [
        f"Имя: {current_user.name}, Возраст: {current_user.age}, Город: {user_city}"
    ]
    if getattr(current_user, "about", None):
        user_info_parts.append(f"О себе: {current_user.about}")
    if current_user_answers:
        ans_list = []
        for qid, ans in list(current_user_answers.items())[:10]:
            q = questions_map.get(qid)
            label = q["text"] if q else qid
            val = ", ".join(ans) if isinstance(ans, list) else ans
            ans_list.append(f"{label}: {val}")
        user_info_parts.append(f"Ответы на вопросы: {'; '.join(ans_list)}")
    user_info_str = " | ".join(user_info_parts)

    # ── Формируем текст анкет с расстоянием и ответами ──
    profiles_lines = []
    for doc in candidates_docs[:80]:
        uid = doc["telegram_id"]
        name = str(doc.get("name", "") or "")
        age = str(doc.get("age", "") or "")
        city = str(doc.get("city", "") or "")
        gender = str(doc.get("gender", "") or "")
        about = str(doc.get("about", "") or "")[:120]
        photos = doc.get("photos", []) or []
        dist = id_to_dist.get(uid)
        dist_str = f" (~{int(dist)}км)" if dist is not None else ""

        line = f"ID:{uid} | {name}, {age}л | {city}{dist_str} | Пол:{gender} | О себе: {about} | Фото: {len(photos)}шт"

        cand_answers = id_to_answers.get(uid, {})
        if cand_answers:
            ans_parts = []
            for qid, ans in list(cand_answers.items())[:6]:
                q = questions_map.get(qid)
                label = q["text"] if q else qid
                val = ", ".join(ans) if isinstance(ans, list) else ans
                ans_parts.append(f"{label}: {val}")
            line += f" | Ответы: {'; '.join(ans_parts)}"

        profiles_lines.append(line)

    candidates_text = "\n".join(profiles_lines)

    # ── Определяем: есть ли визуальные критерии ──
    VISUAL_KEYWORDS = [
        "рыж", "блонд", "брюнет", "волос", "татуир", "пирсинг",
        "строй", "пухл", "толст", "высок", "низк", "спортивн",
        "глаз", "карие", "голуб", "зелён", "кожа", "темнокож",
    ]
    msg_lower = data.message.lower()
    has_visual = any(kw in msg_lower for kw in VISUAL_KEYWORDS)

    # Маппинг telegram_id → doc для выбора после AI-скрининга
    id_to_doc = {d["telegram_id"]: d for d in candidates_docs}

    top_candidate_ids: list[int]
    if has_visual:
        top_candidate_ids = [d["telegram_id"] for d in candidates_docs[:12]]
    else:
        # ── Шаг 1: Текстовый скрининг ──
        try:
            selected_ids = await _matchmaking_text_screen(
                candidates_text=candidates_text,
                user_criteria=data.message,
                conversation=data.conversation,
                shown_ids=shown_ids,
                api_key=config.openai_api_key,
                user_info=user_info_str,
            )
        except Exception as e:
            logger.error(f"matchmaking text screen error: {e}")
            selected_ids = [d["telegram_id"] for d in candidates_docs[:8]]

        top_candidate_ids = [i for i in selected_ids if i in id_to_doc][:10]
        if not top_candidate_ids:
            top_candidate_ids = [d["telegram_id"] for d in candidates_docs[:10]]

    # ── Шаг 2: Vision-ранжирование ─────────────────────────────────────────
    import base64 as _b64
    candidates_with_photos: list[dict] = []
    for uid in top_candidate_ids:
        doc = id_to_doc.get(uid, {})
        photos_list = doc.get("photos", []) or []
        photo_b64: str | None = None
        photo_url: str | None = None

        if photos_list:
            raw_bytes = await _s3_download_bytes(photos_list[0], config)
            if raw_bytes:
                photo_b64 = _b64.b64encode(raw_bytes).decode()

        if not photo_b64:
            for fallback_key in [f"{uid}_0.png", f"{uid}_0.jpg", f"{uid}.png", f"{uid}.jpg"]:
                raw_bytes = await _s3_download_bytes(fallback_key, config)
                if raw_bytes:
                    photo_b64 = _b64.b64encode(raw_bytes).decode()
                    break

        if not photo_b64:
            photo_url = f"{config.url_webhook}/api/v1/users/{uid}/photo"

        name = str(doc.get("name", "") or "")
        age = str(doc.get("age", "") or "")
        city = str(doc.get("city", "") or "")
        about = str(doc.get("about", "") or "")[:200]
        dist = id_to_dist.get(uid)
        dist_str = f" (~{int(dist)}км)" if dist is not None else ""

        photo_note = "" if (photo_b64 or photo_url) else " [фото недоступно — анализируй по описанию]"

        candidates_with_photos.append({
            "id": uid,
            "text": f"{name}, {age}л, {city}{dist_str}. {about}{photo_note}",
            "photo_b64": photo_b64,
            "photo_url": photo_url,
        })

    try:
        final_ids, reply_text = await _matchmaking_vision_rank(
            candidates_info=candidates_with_photos,
            user_criteria=data.message,
            conversation=data.conversation,
            shown_ids=shown_ids,
            api_key=config.openai_api_key,
        )
    except Exception as e:
        logger.error(f"matchmaking vision rank error: {e}")
        final_ids = []
        reply_text = "Произошла ошибка анализа. Попробуй ещё раз."

    # Если AI нашёл совпадения — загружаем полные entity через сервис
    final_users = []
    for fid in final_ids:
        if fid in id_to_doc:
            try:
                u = await service.get_user(telegram_id=fid)
                final_users.append(u)
            except Exception:
                pass

    # Текстовый fallback для визуальных критериев
    if not final_users and has_visual:
        query_words = [w for w in msg_lower.split() if len(w) >= 3]
        for doc in candidates_docs:
            about_lower = str(doc.get("about", "") or "").lower()
            name_lower = str(doc.get("name", "") or "").lower()
            combined = about_lower + " " + name_lower
            if any(w in combined for w in query_words):
                try:
                    u = await service.get_user(telegram_id=doc["telegram_id"])
                    final_users.append(u)
                except Exception:
                    pass
            if len(final_users) >= 3:
                break
        if final_users:
            reply_text = "Нашёл по описанию анкеты 🔍"

    from app.application.api.v1.users.schemas import UserDetailSchema as _UDS
    matches_dicts = [_UDS.from_entity(u).model_dump() for u in final_users]

    return MatchmakingResponse(reply=reply_text, matches=matches_dicts)
