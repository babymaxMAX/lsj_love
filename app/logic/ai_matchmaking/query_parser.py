"""
Query Parser: парсит естественный язык запроса пользователя в структурированный ParsedQuery.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.infra.repositories.cities import (
    CITY_ALIASES,
    CITY_COORDS,
    REGION_ALIASES,
    get_city_coords,
)

from app.logic.ai_matchmaking.constants import TAG_VOCABULARY

logger = logging.getLogger(__name__)


@dataclass
class ParsedQuery:
    """Структурированный запрос AI-подбора."""

    target_gender: str  # "male" | "female"
    city: str | None
    age_min: int | None
    age_max: int | None
    appearance_tags: list[str]
    skills_tags: list[str]
    traits_tags: list[str]
    negative_tags: list[str]
    raw_semantic_query: str


def _normalize_tags(tags: list[str], vocab_key: str) -> list[str]:
    """Оставляет только теги из словаря."""
    allowed = set(TAG_VOCABULARY.get(vocab_key, []))
    return [t for t in tags if t in allowed]


def _resolve_city(raw: str) -> str | None:
    """Нормализует название города через CITY_COORDS / REGION_ALIASES."""
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    s_lower = s.lower()
    if s_lower in REGION_ALIASES:
        return REGION_ALIASES[s_lower]
    if s_lower in CITY_ALIASES:
        return CITY_ALIASES[s_lower]
    if s in CITY_COORDS:
        return s
    if get_city_coords(s):
        for k in CITY_COORDS:
            if k.lower() == s_lower:
                return k
        return s
    return None


async def parse_user_query(
    text: str,
    current_user_gender: str | None,
    api_key: str,
) -> ParsedQuery:
    """
    Парсит естественный запрос пользователя в ParsedQuery.
    current_user_gender: "male"|"female"|None — для вывода target_gender, если не указан в тексте.
    """
    from openai import AsyncOpenAI

    all_tags = (
        TAG_VOCABULARY["appearance"]
        + TAG_VOCABULARY["skills"]
        + TAG_VOCABULARY["traits"]
        + TAG_VOCABULARY["negative"]
    )
    tags_str = ", ".join(sorted(set(all_tags)))

    system_prompt = f"""Ты — парсер запросов для dating-приложения. Пользователь пишет свободным текстом, кого ищет.
Извлеки структурированные данные. Отвечай ТОЛЬКО валидным JSON.

Схема ответа (все поля обязательны, используй null если не указано):
{{
  "target_gender": "male" | "female" | null,
  "city": "строка города или null",
  "age_min": число или null,
  "age_max": число или null,
  "appearance_tags": ["tag1", "tag2"],
  "skills_tags": ["tag1"],
  "traits_tags": ["tag1"],
  "negative_tags": ["tag1"],
  "raw_semantic_query": "короткое описание запроса на русском для пояснений"
}}

Словарь тегов (используй ТОЛЬКО эти значения):
{tags_str}

Маппинг русских выражений на теги:
- рыжая/рыжие/огненная/медная → red_hair
- блондинка/светлая/белокурая → blonde
- брюнетка/тёмная/чернявая → black_hair
- стройная/худая/тонкая → slim
- спортивная/подтянутая/атлетичная → athletic
- пышная/в теле/полная/с формами → curvy
- умеет готовить/любит готовить/готовит/пеку → cooking
- кухня/выпечка → baking
- спорт/фитнес/зал → fitness, sport
- спокойная/спокойный → calm
- весёлая/жизнерадостная → cheerful
- романтичная → romantic
- семейная/семья → family_oriented
- карьерист → career_focused
- без тусовок/не тусовщик → negative: party_lifestyle
- девушка/девушки/женщина → target_gender: female
- парень/парни/мужчина → target_gender: male

Города: Москва, Санкт-Петербург, Питер, СПб, Мск, Казань, Екатеринбург, Екб и т.д. — возвращай каноничное название (Москва, не moscow).
Фразы «с Москвы», «из Москвы», «девушку с Москвы» → city: Москва.
Регионы: Дагестан→Махачкала, Чечня→Грозный, КБР→Нальчик, Питер→Санкт-Петербург."""

    user_prompt = f"Запрос пользователя: {text}"

    client = AsyncOpenAI(api_key=api_key)
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=400,
        temperature=0.2,
    )
    raw = resp.choices[0].message.content.strip()

    try:
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.strip().startswith("json"):
                raw = raw[4:].strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
        else:
            data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(f"Query parser JSON decode error: {e}, raw={raw[:200]}")
        return _default_parsed_query(text, current_user_gender)

    target_gender = data.get("target_gender")
    if not target_gender and current_user_gender:
        g = str(current_user_gender).lower()
        target_gender = "female" if g in ("man", "male", "мужской", "м", "m") else "male"

    if not target_gender:
        target_gender = "female"

    city_raw = data.get("city")
    city = _resolve_city(city_raw) if city_raw else None

    age_min = data.get("age_min")
    age_max = data.get("age_max")
    if age_min is not None:
        try:
            age_min = int(age_min)
        except (TypeError, ValueError):
            age_min = None
    if age_max is not None:
        try:
            age_max = int(age_max)
        except (TypeError, ValueError):
            age_max = None

    appearance = data.get("appearance_tags") or []
    skills = data.get("skills_tags") or []
    traits = data.get("traits_tags") or []
    negative = data.get("negative_tags") or []

    appearance = _normalize_tags(appearance, "appearance")
    skills = _normalize_tags(skills, "skills")
    traits = _normalize_tags(traits, "traits")
    negative = _normalize_tags(negative, "negative")

    raw_semantic = data.get("raw_semantic_query") or text
    if not isinstance(raw_semantic, str):
        raw_semantic = text

    return ParsedQuery(
        target_gender=str(target_gender).lower(),
        city=city,
        age_min=age_min,
        age_max=age_max,
        appearance_tags=appearance,
        skills_tags=skills,
        traits_tags=traits,
        negative_tags=negative,
        raw_semantic_query=raw_semantic[:200],
    )


def _default_parsed_query(text: str, current_user_gender: str | None) -> ParsedQuery:
    """Fallback при ошибке парсинга."""
    target = "female"
    if current_user_gender:
        g = str(current_user_gender).lower()
        target = "female" if g in ("man", "male", "мужской", "м", "m") else "male"
    return ParsedQuery(
        target_gender=target,
        city=None,
        age_min=None,
        age_max=None,
        appearance_tags=[],
        skills_tags=[],
        traits_tags=[],
        negative_tags=[],
        raw_semantic_query=text[:200],
    )
