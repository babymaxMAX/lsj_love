"""
Scoring: считает score и reasons для кандидатов AI-подбора.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.domain.entities.users import UserEntity
from app.logic.ai_matchmaking.constants import (
    CITY_NEIGHBORS,
    WEIGHT_ACTIVITY,
    WEIGHT_CITY_MATCH,
    WEIGHT_PROFILE_QUALITY,
    WEIGHT_TAG_MATCH,
    WEIGHT_TEXT_RELEVANCE,
)
from app.logic.ai_matchmaking.query_parser import ParsedQuery

# Human-readable labels for tags
TAG_LABELS: dict[str, str] = {
    "red_hair": "рыжие волосы",
    "blonde": "светлые волосы",
    "brunette": "тёмные волосы",
    "slim": "стройная",
    "athletic": "спортивная",
    "curvy": "с формами",
    "cooking": "умеет готовить",
    "baking": "любит выпечку",
    "fitness": "фитнес",
    "calm": "спокойная",
    "cheerful": "весёлая",
    "romantic": "романтичная",
    "family_oriented": "семейная",
}


def _tag_match_score(user: UserEntity, parsed: ParsedQuery) -> tuple[float, list[str]]:
    """Возвращает (0..1, reasons)."""
    query_tags = set(
        parsed.appearance_tags + parsed.skills_tags + parsed.traits_tags
    ) - set(parsed.negative_tags)
    if not query_tags:
        return 0.0, []

    user_tags = set()
    user_tags.update(getattr(user, "ai_appearance", []) or [])
    user_tags.update(getattr(user, "ai_skills", []) or [])
    user_tags.update(getattr(user, "ai_traits", []) or [])

    matches = query_tags & user_tags
    if matches:
        reasons = [TAG_LABELS.get(t, t) for t in matches]
        return min(1.0, len(matches) / max(1, len(query_tags))), reasons

    about = str(getattr(user, "about", "") or "")
    if hasattr(user.about, "as_generic_type"):
        about = str(user.about.as_generic_type())
    about_lower = about.lower()
    reasons = []
    for t in query_tags:
        lbl = TAG_LABELS.get(t, t)
        kw = t.replace("_", " ")
        if kw in about_lower or lbl in about_lower:
            reasons.append(lbl)
    if reasons:
        return 0.6, reasons
    return 0.0, []


def _city_match_score(user: UserEntity, query_city: str | None) -> tuple[float, list[str]]:
    """Возвращает (0|0.5|1.0, reasons)."""
    if not query_city:
        return 0.0, []
    user_city = str(getattr(user, "city", "") or "")
    if hasattr(user.city, "as_generic_type"):
        user_city = str(user.city.as_generic_type())
    user_city = user_city.strip()
    query_city = query_city.strip()
    if user_city.lower() == query_city.lower():
        return 1.0, ["город совпадает"]
    neighbors = CITY_NEIGHBORS.get(query_city, [])
    if user_city in neighbors or user_city.lower() in [c.lower() for c in neighbors]:
        return 0.5, ["рядом с городом"]
    return 0.0, []


def _text_relevance_score(user: UserEntity, raw_query: str) -> tuple[float, list[str]]:
    """Наличие слов запроса в about."""
    if not raw_query or len(raw_query) < 2:
        return 0.0, []
    about = str(getattr(user, "about", "") or "")
    if hasattr(user.about, "as_generic_type"):
        about = str(user.about.as_generic_type())
    about_lower = about.lower()
    words = [w for w in raw_query.lower().split() if len(w) >= 3]
    found = [w for w in words if w in about_lower]
    if found:
        return min(1.0, len(found) / max(1, len(words))), ["совпадение по описанию"]
    return 0.0, []


def _activity_score(user: UserEntity) -> float:
    """1.0 если last_seen < 7 дней, 0.5 если < 30, 0.2 иначе."""
    last = getattr(user, "last_seen", None)
    if not last:
        return 0.5
    try:
        if getattr(last, "tzinfo", None) is None:
            last = last.replace(tzinfo=timezone.utc)
        delta = (datetime.now(timezone.utc) - last).total_seconds()
        days = delta / 86400
        if days < 7:
            return 1.0
        if days < 30:
            return 0.5
    except Exception:
        pass
    return 0.2


def _profile_quality_score(user: UserEntity) -> float:
    """1.0 если about длинный и есть фото."""
    about = getattr(user, "about", "") or ""
    if hasattr(about, "as_generic_type"):
        about = str(about.as_generic_type())
    has_photo = bool(getattr(user, "photos", []) or getattr(user, "photo"))
    about_len = len(about)
    if has_photo and about_len >= 50:
        return 1.0
    if has_photo and about_len >= 20:
        return 0.7
    if has_photo:
        return 0.5
    return 0.2


def score_candidates(
    candidates: list[UserEntity],
    parsed_query: ParsedQuery,
) -> list[tuple[UserEntity, float, list[str]]]:
    """
    Возвращает список (user, score, reasons) отсортированный по score.
    """
    results: list[tuple[UserEntity, float, list[str]]] = []
    for user in candidates:
        tag_s, tag_r = _tag_match_score(user, parsed_query)
        city_s, city_r = _city_match_score(user, parsed_query.city)
        text_s, text_r = _text_relevance_score(user, parsed_query.raw_semantic_query)
        act_s = _activity_score(user)
        qual_s = _profile_quality_score(user)

        score = (
            WEIGHT_TAG_MATCH * tag_s
            + WEIGHT_CITY_MATCH * city_s
            + WEIGHT_TEXT_RELEVANCE * text_s
            + WEIGHT_ACTIVITY * act_s
            + WEIGHT_PROFILE_QUALITY * qual_s
        )
        reasons = list(dict.fromkeys(tag_r + city_r + text_r))
        if not reasons:
            reasons = ["подходящая анкета"]
        results.append((user, score, reasons))
    results.sort(key=lambda x: x[1], reverse=True)
    return results
