"""
Profile Questions — система вопросов для заполнения профиля.
20+ вопросов по категориям: образ жизни, личность, ценности, хобби.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from punq import Container

from app.logic.init import init_container
from app.settings.config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["Profile Questions"])

PROFILE_QUESTIONS = [
    # ── Образ жизни ──
    {"question_id": "weekend", "text": "Как проводишь выходные?", "type": "multiple_choice",
     "options": ["Активный отдых", "Дома с фильмом", "Встречи с друзьями", "Путешествую", "Работаю/учусь"],
     "category": "lifestyle", "emoji": "🌅"},
    {"question_id": "owl_lark", "text": "Ты сова или жаворонок?", "type": "multiple_choice",
     "options": ["Сова 🦉", "Жаворонок 🐦", "Зависит от дня"],
     "category": "lifestyle", "emoji": "🕐"},
    {"question_id": "sport", "text": "Как относишься к спорту?", "type": "multiple_choice",
     "options": ["Занимаюсь регулярно", "Иногда", "Люблю смотреть", "Не моё"],
     "category": "lifestyle", "emoji": "🏋️"},
    {"question_id": "cooking", "text": "Умеешь готовить?", "type": "multiple_choice",
     "options": ["Люблю готовить", "Могу, но лень", "Только яичницу", "Предпочитаю заказывать"],
     "category": "lifestyle", "emoji": "🍳"},
    {"question_id": "travel", "text": "Горы или море?", "type": "multiple_choice",
     "options": ["Горы ⛰️", "Море 🏖️", "И то и другое", "Город 🏙️"],
     "category": "lifestyle", "emoji": "✈️"},
    # ── Личность ──
    {"question_id": "career_family", "text": "Что для тебя важнее — карьера или семья?", "type": "multiple_choice",
     "options": ["Карьера", "Семья", "Баланс обоих", "Пока не определился"],
     "category": "personality", "emoji": "⚖️"},
    {"question_id": "introvert_extrovert", "text": "Ты интроверт или экстраверт?", "type": "multiple_choice",
     "options": ["Интроверт", "Экстраверт", "Амбиверт"],
     "category": "personality", "emoji": "🧠"},
    {"question_id": "conflict", "text": "Как решаешь конфликты?", "type": "multiple_choice",
     "options": ["Обсуждаю спокойно", "Эмоционально", "Избегаю конфликтов", "Ищу компромисс"],
     "category": "personality", "emoji": "🤝"},
    {"question_id": "humor_type", "text": "Какой у тебя юмор?", "type": "multiple_choice",
     "options": ["Сарказм", "Мемы", "Интеллектуальный", "Физический", "Всё подряд"],
     "category": "personality", "emoji": "😂"},
    {"question_id": "spontaneous", "text": "Ты спонтанный или планируешь всё?", "type": "multiple_choice",
     "options": ["Спонтанный", "Планирую всё", "Зависит от ситуации"],
     "category": "personality", "emoji": "🎲"},
    # ── Ценности ──
    {"question_id": "children", "text": "Как относишься к детям?", "type": "multiple_choice",
     "options": ["Хочу детей", "Уже есть", "Пока не думал", "Не хочу"],
     "category": "values", "emoji": "👶"},
    {"question_id": "ideal_evening", "text": "Что для тебя идеальный вечер?", "type": "multiple_choice",
     "options": ["Ужин вдвоём", "Вечеринка с друзьями", "Кино дома", "Прогулка по городу", "Настольные игры"],
     "category": "values", "emoji": "🌙"},
    {"question_id": "relationship_type", "text": "Что ищешь в отношениях?", "type": "multiple_choice",
     "options": ["Серьёзные отношения", "Лёгкое общение", "Дружбу", "Пока не знаю"],
     "category": "values", "emoji": "💕"},
    {"question_id": "pets", "text": "Как относишься к животным?", "type": "multiple_choice",
     "options": ["Обожаю, есть питомец", "Люблю, но нет", "Нейтрально", "Аллергия 😢"],
     "category": "values", "emoji": "🐾"},
    {"question_id": "smoking", "text": "Отношение к курению?", "type": "multiple_choice",
     "options": ["Не курю и не люблю", "Не курю, но нормально", "Курю иногда", "Курю"],
     "category": "values", "emoji": "🚭"},
    # ── Хобби ──
    {"question_id": "free_time", "text": "Чем занимаешься в свободное время?", "type": "multiple_choice",
     "options": ["Спорт", "Чтение", "Игры", "Творчество", "Сериалы", "Тусовки"],
     "category": "hobbies", "emoji": "🎯"},
    {"question_id": "movies", "text": "Любимый жанр фильмов?", "type": "multiple_choice",
     "options": ["Комедия", "Триллер", "Романтика", "Фантастика", "Документальные", "Хоррор"],
     "category": "hobbies", "emoji": "🎬"},
    {"question_id": "music", "text": "Музыка — какой жанр?", "type": "multiple_choice",
     "options": ["Поп", "Рок", "Рэп", "Электронная", "Классика", "Слушаю всё"],
     "category": "hobbies", "emoji": "🎵"},
    {"question_id": "books", "text": "Читаешь книги?", "type": "multiple_choice",
     "options": ["Читаю много", "Иногда", "Аудиокниги", "Не читаю", "Предпочитаю статьи"],
     "category": "hobbies", "emoji": "📚"},
    {"question_id": "gaming", "text": "Играешь в видеоигры?", "type": "multiple_choice",
     "options": ["Да, много", "Иногда", "Только мобильные", "Нет"],
     "category": "hobbies", "emoji": "🎮"},
    {"question_id": "social_media", "text": "Любимая соцсеть?", "type": "multiple_choice",
     "options": ["Instagram", "TikTok", "YouTube", "Telegram", "Не пользуюсь"],
     "category": "hobbies", "emoji": "📱"},
    {"question_id": "dream", "text": "Мечта на ближайший год?", "type": "open",
     "options": [], "category": "values", "emoji": "✨"},
]


def _get_questions_collection(container: Container):
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)
    return client[config.mongodb_dating_database]["profile_questions"]


def _get_users_collection(container: Container):
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)
    return client[config.mongodb_dating_database][config.mongodb_users_collection]


class AnswerRequest(BaseModel):
    telegram_id: int
    question_id: str
    answer: str | list[str]


class AnswerResponse(BaseModel):
    success: bool
    question_id: str


@router.get("/questions")
async def get_next_question(
    telegram_id: int,
    container: Container = Depends(init_container),
):
    """Возвращает следующий неотвеченный вопрос для пользователя."""
    col = _get_users_collection(container)
    user_doc = await col.find_one(
        {"telegram_id": telegram_id},
        {"profile_answers": 1},
    )
    answered = set((user_doc or {}).get("profile_answers", {}).keys())
    for q in PROFILE_QUESTIONS:
        if q["question_id"] not in answered:
            return {"question": q, "total": len(PROFILE_QUESTIONS), "answered": len(answered), "done": False}
    return {"question": None, "total": len(PROFILE_QUESTIONS), "answered": len(answered), "done": True}


@router.get("/questions/all")
async def get_all_questions():
    """Возвращает все вопросы профиля."""
    return {"questions": PROFILE_QUESTIONS}


@router.post("/answers")
async def save_answer(
    data: AnswerRequest,
    container: Container = Depends(init_container),
):
    """Сохраняет ответ пользователя на вопрос профиля."""
    valid_ids = {q["question_id"] for q in PROFILE_QUESTIONS}
    if data.question_id not in valid_ids:
        raise HTTPException(status_code=400, detail={"error": "Неизвестный вопрос"})

    col = _get_users_collection(container)
    await col.update_one(
        {"telegram_id": data.telegram_id},
        {"$set": {f"profile_answers.{data.question_id}": data.answer}},
        upsert=True,
    )
    return AnswerResponse(success=True, question_id=data.question_id)


@router.get("/answers/{user_id}")
async def get_user_answers(
    user_id: int,
    container: Container = Depends(init_container),
):
    """Возвращает все ответы пользователя на вопросы профиля."""
    col = _get_users_collection(container)
    user_doc = await col.find_one(
        {"telegram_id": user_id},
        {"profile_answers": 1},
    )
    answers = (user_doc or {}).get("profile_answers", {})
    questions_map = {q["question_id"]: q for q in PROFILE_QUESTIONS}
    result = []
    for qid, answer in answers.items():
        q = questions_map.get(qid)
        if q:
            result.append({
                "question_id": qid,
                "text": q["text"],
                "emoji": q["emoji"],
                "category": q["category"],
                "answer": answer,
            })
    return {"answers": result}


class ReformulateRequest(BaseModel):
    question: str
    answer: str


class ReformulateResponse(BaseModel):
    formatted: str


@router.post("/reformulate")
async def reformulate_answer(
    data: ReformulateRequest,
    container: Container = Depends(init_container),
):
    """AI красиво формулирует ответ пользователя для профиля."""
    config: Config = container.resolve(Config)
    if not config.openai_api_key:
        return ReformulateResponse(formatted=data.answer)

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=config.openai_api_key)

        system = (
            "Ты помогаешь оформить ответ пользователя на вопрос анкеты знакомств.\n"
            "Правила:\n"
            "- Формулируй от первого лица ('Люблю...', 'Занимаюсь...', 'Обожаю...')\n"
            "- Максимум 5-7 слов — коротко и ёмко\n"
            "- Добавь 1 подходящий эмодзи в конце\n"
            "- Не используй слово 'я' в начале\n"
            "- Пример: вопрос 'Увлекаетесь спортом?' + ответ 'да увлекаюсь' → 'Занимаюсь спортом регулярно 💪'\n"
            "Верни только готовую фразу, без пояснений."
        )
        user_msg = f"Вопрос: {data.question}\nОтвет пользователя: {data.answer}"

        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=50,
            temperature=0.8,
        )
        formatted = resp.choices[0].message.content.strip().strip('"')
        return ReformulateResponse(formatted=formatted)
    except Exception as e:
        logger.warning(f"Reformulate error: {e}")
        return ReformulateResponse(formatted=data.answer)
