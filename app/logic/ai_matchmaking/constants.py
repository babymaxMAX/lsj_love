"""
Константы для AI Matchmaking: словарь тегов и веса scoring.
"""

# Словарь допустимых тегов для парсера и матчинга
TAG_VOCABULARY: dict[str, list[str]] = {
    "appearance": [
        "red_hair",
        "blonde",
        "brunette",
        "black_hair",
        "slim",
        "athletic",
        "curvy",
        "tall",
        "short",
        "tattoos",
        "piercing",
        "glasses",
    ],
    "skills": [
        "cooking",
        "baking",
        "fitness",
        "sport",
        "music",
        "art",
        "travel",
        "photography",
        "reading",
        "dancing",
    ],
    "traits": [
        "calm",
        "cheerful",
        "romantic",
        "adventurous",
        "family_oriented",
        "career_focused",
        "creative",
        "introvert",
        "extrovert",
        "kind",
    ],
    "negative": [
        "party_lifestyle",
        "smoking",
        "alcohol",
    ],
}

# Веса для scoring MVP
WEIGHT_TAG_MATCH = 0.35
WEIGHT_CITY_MATCH = 0.25
WEIGHT_TEXT_RELEVANCE = 0.20
WEIGHT_ACTIVITY = 0.10
WEIGHT_PROFILE_QUALITY = 0.10

# Соседние города для city_match (копия из mongo, основные)
CITY_NEIGHBORS: dict[str, list[str]] = {
    "Москва": ["Химки", "Балашиха", "Подольск", "Мытищи", "Люберцы", "Королёв", "Одинцово"],
    "Санкт-Петербург": ["Гатчина", "Пушкин", "Выборг", "Всеволожск"],
}
