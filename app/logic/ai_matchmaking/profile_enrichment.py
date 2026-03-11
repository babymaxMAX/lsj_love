"""
Profile Enrichment: извлекает AI-теги из текста анкеты и строит search_text.
"""
from __future__ import annotations

import json
import logging

from app.domain.entities.users import UserEntity

from app.logic.ai_matchmaking.constants import TAG_VOCABULARY

logger = logging.getLogger(__name__)


def _build_search_text(user: UserEntity) -> str:
    """Строит единый текстовый документ для поиска."""
    parts = []
    if user.name:
        name_val = user.name.as_generic_type() if hasattr(user.name, "as_generic_type") else str(user.name)
        parts.append(f"Имя: {name_val}")
    if user.age is not None:
        age_val = user.age.as_generic_type() if hasattr(user.age, "as_generic_type") else user.age
        parts.append(f"Возраст: {age_val}")
    if user.city:
        city_val = user.city.as_generic_type() if hasattr(user.city, "as_generic_type") else str(user.city)
        parts.append(f"Город: {city_val}")
    if user.about:
        about_val = user.about.as_generic_type() if hasattr(user.about, "as_generic_type") else str(user.about)
        parts.append(f"О себе: {about_val}")
    return " ".join(parts) if parts else ""


def _normalize_extracted_tags(tags: list[str]) -> list[str]:
    """Оставляет только теги из общего словаря."""
    allowed = set()
    for vals in TAG_VOCABULARY.values():
        for v in vals:
            allowed.add(v)
    return [t for t in tags if t in allowed]


async def enrich_profile_for_ai(user: UserEntity, api_key: str) -> dict:
    """
    Обогащает анкету для AI-поиска.
    Возвращает dict для $set в MongoDB: search_text, ai_traits, ai_skills, ai_appearance.
    """
    from openai import AsyncOpenAI

    search_text = _build_search_text(user)
    result = {
        "search_text": search_text,
        "ai_traits": [],
        "ai_skills": [],
        "ai_appearance": [],
    }

    about = ""
    if user.about:
        about = user.about.as_generic_type() if hasattr(user.about, "as_generic_type") else str(user.about)

    if not about or not about.strip():
        return result

    all_tags = (
        TAG_VOCABULARY["appearance"]
        + TAG_VOCABULARY["skills"]
        + TAG_VOCABULARY["traits"]
    )
    tags_str = ", ".join(sorted(set(all_tags)))

    system_prompt = f"""Извлеки из текста «О себе» теги для dating-профиля.
Верни ТОЛЬКО JSON: {{"ai_traits": [], "ai_skills": [], "ai_appearance": []}}

Допустимые теги:
{tags_str}

ai_traits: характер (calm, cheerful, romantic, family_oriented, career_focused, creative, introvert, extrovert, kind)
ai_skills: навыки и интересы (cooking, baking, fitness, sport, music, art, travel, photography, reading, dancing)
ai_appearance: внешность если упомянута (red_hair, blonde, brunette, slim, athletic, curvy, tall, short, tattoos, piercing, glasses)

Используй ТОЛЬКО теги из списка. Если ничего не подходит — пустой массив."""

    try:
        client = AsyncOpenAI(api_key=api_key)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Текст: {about}"},
            ],
            max_tokens=150,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()
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
        result["ai_traits"] = _normalize_extracted_tags(data.get("ai_traits") or [])
        result["ai_skills"] = _normalize_extracted_tags(data.get("ai_skills") or [])
        result["ai_appearance"] = _normalize_extracted_tags(data.get("ai_appearance") or [])
    except Exception as e:
        logger.warning(f"Profile enrichment failed for user {user.telegram_id}: {e}")

    return result
