"""
Candidate Preselection: получает кандидатов для AI-подбора по жестким фильтрам.
"""
from app.domain.entities.users import UserEntity
from app.infra.repositories.base import BaseUsersRepository
from app.logic.ai_matchmaking.query_parser import ParsedQuery


async def get_ai_candidates(
    repository: BaseUsersRepository,
    telegram_id: int,
    parsed_query: ParsedQuery,
    exclude_ids: list[int] | None = None,
    city_include_neighbors: bool = False,
    limit: int = 300,
) -> list[UserEntity]:
    """
    Возвращает кандидатов для ранжирования.
    HARD фильтры: target_gender, age_min/max, city (с нормализацией).
    """
    candidates = await repository.get_ai_matchmaking_candidates(
        telegram_id=telegram_id,
        target_gender=parsed_query.target_gender,
        exclude_ids=exclude_ids,
        age_min=parsed_query.age_min,
        age_max=parsed_query.age_max,
        city=parsed_query.city,
        city_include_neighbors=city_include_neighbors,
        limit=limit,
    )
    return candidates if isinstance(candidates, list) else list(candidates)
