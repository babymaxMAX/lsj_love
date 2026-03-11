"""Эндпоинты геокодинга для Mini App."""
from punq import Container

from fastapi import APIRouter, Depends

from app.infra.geocoding.base import BaseGeocoder
from app.logic.init import init_container

router = APIRouter(prefix="/geocode", tags=["geocode"])


@router.get(
    "/suggest",
    description="Подсказки городов для автодополнения в Mini App.",
)
async def geocode_suggest(
    q: str = "",
    limit: int = 5,
    container: Container = Depends(init_container),
):
    """Возвращает до limit вариантов городов по запросу q."""
    geocoder: BaseGeocoder = container.resolve(BaseGeocoder)
    q = (q or "").strip()
    if not q or len(q) < 2:
        return {"items": []}
    limit = max(1, min(limit, 10))
    results = await geocoder.geocode_suggest(q, limit=limit)
    items = [
        {
            "display_name": r.display_name,
            "city_name": r.city_name,
            "region_name": r.region_name,
            "country_name": r.country_name,
            "lat": r.lat,
            "lon": r.lon,
        }
        for r in results
    ]
    return {"items": items}
