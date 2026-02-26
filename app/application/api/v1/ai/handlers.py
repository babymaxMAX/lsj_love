"""
AI Icebreaker — генератор первых сообщений с выбором темы, vision-анализом
фото и лимитами использования.
AI Советник диалога — чат-ассистент для помощи в переписке (VIP или 24ч пробный).
"""
import json
import logging
import random
from datetime import date, datetime, timezone

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
) -> list[int]:
    """
    Шаг 1: Текстовый скрининг — GPT-4o-mini выбирает топ-10 ID по критериям пользователя.
    Возвращает список telegram_id.
    """
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)

    shown_note = f"\nУже показанные пользователю (не повторяй): {shown_ids}" if shown_ids else ""

    system = (
        "Ты — умный алгоритм подбора партнёров для приложения знакомств. "
        "Пользователь описывает, кого ищет. Тебе дан список анкет с ID, именем, возрастом, городом и описанием. "
        "Выбери до 10 НОВЫХ анкет, которые наилучшим образом соответствуют критериям. "
        "Не повторяй уже показанные ID. "
        "Ответь ТОЛЬКО JSON: {\"selected\": [id1, id2, ...]}"
    )

    messages: list[dict] = [{"role": "system", "content": system}]
    for h in conversation[-8:]:
        if h.get("content", "").strip():
            messages.append({"role": h["role"], "content": h["content"]})

    user_msg = (
        f"Критерии: {user_criteria}{shown_note}\n\n"
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
        "Ты — живой помощник-сваха в приложении знакомств. Общайся неформально, по-дружески, коротко.\n"
        "Анализируй фотографии и описания анкет, выбери 2-3 анкеты которые лучше всего подходят пользователю.\n"
        "ВАЖНО: описывай ТОЛЬКО то что реально видишь на фото или в описании. НЕ придумывай внешность.\n"
        "Напиши 1-2 предложения почему выбрал этих людей (без перечисления всех деталей).\n"
        f"Затем на новой строке ТОЛЬКО: {{\"matches\": [id1, id2]}}{shown_note}"
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


@router.post(
    "/matchmaking",
    status_code=status.HTTP_200_OK,
    description="AI Подбор: анализирует критерии пользователя и возвращает подходящие анкеты.",
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

    # shown_ids — анкеты уже показанные пользователю в этой сессии
    shown_ids: list[int] = list(set(data.shown_ids or []))

    # Получаем список тех, кого пользователь уже лайкнул
    from app.logic.services.base import BaseLikesService as _BaseLikesService
    likes_service: _BaseLikesService = container.resolve(_BaseLikesService)
    try:
        liked_ids = list(set(await likes_service.get_telegram_id_liked_from(user_id=data.user_id)))
    except Exception:
        liked_ids = []

    # Исключаем лайкнутых И показанных (если просят другие)
    exclude_ids = list(set(liked_ids + shown_ids))

    # Загружаем кандидатов через сервис (до 60 человек чтобы было из чего выбирать)
    try:
        candidates_iter = await service.get_best_result_for_user(
            telegram_id=data.user_id,
            exclude_ids=liked_ids,  # базовое исключение только лайкнутых
        )
        candidates_raw = list(candidates_iter)[:60]
    except Exception as e:
        logger.error(f"matchmaking: failed to get candidates: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Не удалось загрузить анкеты. Попробуй позже."},
        )

    # Фильтруем показанных отдельно (чтобы при "покажи ещё" были новые)
    candidates = [u for u in candidates_raw if u.telegram_id not in shown_ids]
    if not candidates:
        # Если новых нет — пробуем без фильтра shown_ids
        candidates = candidates_raw

    if not candidates:
        return MatchmakingResponse(
            reply="😔 Пока анкет нет. Зайди позже — новые появятся!",
            matches=[],
        )

    # ── Шаг 1: Текстовый скрининг ──────────────────────────────────────────
    profiles_lines = []
    for u in candidates:
        name = str(getattr(u, "name", "") or "")
        age = str(getattr(u, "age", "") or "")
        city = str(getattr(u, "city", "") or "")
        about = str(getattr(u, "about", "") or "")[:120]
        uid = u.telegram_id
        profiles_lines.append(f"ID:{uid} | {name}, {age} лет, {city} | О себе: {about}")

    candidates_text = "\n".join(profiles_lines)

    try:
        selected_ids = await _matchmaking_text_screen(
            candidates_text=candidates_text,
            user_criteria=data.message,
            conversation=data.conversation,
            shown_ids=shown_ids,
            api_key=config.openai_api_key,
        )
    except Exception as e:
        logger.error(f"matchmaking text screen error: {e}")
        selected_ids = [u.telegram_id for u in candidates[:8]]

    # Фильтруем кандидатов по отобранным ID
    id_to_user = {u.telegram_id: u for u in candidates_raw}
    top_candidates = [id_to_user[i] for i in selected_ids if i in id_to_user][:10]

    if not top_candidates:
        top_candidates = candidates[:5]

    # ── Шаг 2: Vision-ранжирование ─────────────────────────────────────────
    import base64 as _b64
    candidates_with_photos: list[dict] = []
    for u in top_candidates:
        uid = u.telegram_id
        photos_list = getattr(u, "photos", []) or []
        photo_b64: str | None = None

        if photos_list:
            s3_key = photos_list[0]
            raw_bytes = await _s3_download_bytes(s3_key, config)
            if raw_bytes:
                photo_b64 = _b64.b64encode(raw_bytes).decode()

        name = str(getattr(u, "name", "") or "")
        age = str(getattr(u, "age", "") or "")
        city = str(getattr(u, "city", "") or "")
        about = str(getattr(u, "about", "") or "")[:200]

        candidates_with_photos.append({
            "id": uid,
            "text": f"{name}, {age} лет, {city}. {about}",
            "photo_b64": photo_b64,
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
        final_ids = [u.telegram_id for u in top_candidates[:3]]
        reply_text = "Нашёл кое-кого интересного для тебя 💫"

    # Собираем финальных пользователей в правильном порядке
    final_users = [id_to_user[i] for i in final_ids if i in id_to_user]
    if not final_users:
        final_users = top_candidates[:3]

    from app.application.api.v1.users.schemas import UserDetailSchema as _UDS
    matches_dicts = [_UDS.from_entity(u).model_dump() for u in final_users]

    return MatchmakingResponse(reply=reply_text, matches=matches_dicts)
