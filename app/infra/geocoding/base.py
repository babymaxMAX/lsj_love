"""Базовые типы для геокодинга."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GeocodingResult:
    """Результат геокодинга."""

    lat: float
    lon: float
    city_name: str
    region_name: str
    country_name: str
    display_name: str
    confidence: float = 1.0

    def to_geojson_point(self) -> dict:
        """GeoJSON Point для MongoDB 2dsphere (coordinates: [lon, lat])."""
        return {
            "type": "Point",
            "coordinates": [self.lon, self.lat],
        }


class BaseGeocoder(ABC):
    """Абстрактный геокодер."""

    @abstractmethod
    async def geocode(self, query: str) -> GeocodingResult | None:
        """Преобразует строку (город, адрес) в координаты и нормализованные поля."""
        ...

    @abstractmethod
    async def reverse_geocode(self, lat: float, lon: float) -> GeocodingResult | None:
        """Обратный геокодинг: координаты → город/регион."""
        ...

    async def geocode_suggest(self, query: str, limit: int = 5) -> list[GeocodingResult]:
        """Подсказки для автодополнения (город, адрес). По умолчанию возвращает до 5 вариантов."""
        return []
