"""Модуль геокодинга."""
from app.infra.geocoding.base import BaseGeocoder, GeocodingResult
from app.infra.geocoding.cache import CachedGeocoder
from app.infra.geocoding.nominatim import NominatimGeocoder

__all__ = [
    "BaseGeocoder",
    "GeocodingResult",
    "NominatimGeocoder",
    "CachedGeocoder",
]
