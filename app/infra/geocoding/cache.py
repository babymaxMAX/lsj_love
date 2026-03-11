"""Кэширование результатов геокодинга в MongoDB."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta

from motor.motor_asyncio import AsyncIOMotorCollection

from app.infra.geocoding.base import BaseGeocoder, GeocodingResult

logger = logging.getLogger(__name__)


def _query_hash(query: str, mode: str = "geocode") -> str:
    """Хэш запроса для ключа кэша."""
    key = f"{mode}:{query.strip().lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _doc_to_result(doc: dict) -> GeocodingResult | None:
    if not doc:
        return None
    try:
        lat = float(doc.get("lat", 0))
        lon = float(doc.get("lon", 0))
        return GeocodingResult(
            lat=lat,
            lon=lon,
            city_name=doc.get("city_name", ""),
            region_name=doc.get("region_name", ""),
            country_name=doc.get("country_name", ""),
            display_name=doc.get("display_name", ""),
            confidence=float(doc.get("confidence", 1.0)),
        )
    except (TypeError, ValueError, KeyError) as e:
        logger.warning("Failed to deserialize cached geocode result: %s", e)
        return None


def _result_to_doc(r: GeocodingResult) -> dict:
    return {
        "lat": r.lat,
        "lon": r.lon,
        "city_name": r.city_name,
        "region_name": r.region_name,
        "country_name": r.country_name,
        "display_name": r.display_name,
        "confidence": r.confidence,
    }


class CachedGeocoder(BaseGeocoder):
    """Обёртка над геокодером с MongoDB-кэшем."""

    def __init__(
        self,
        delegate: BaseGeocoder,
        collection: AsyncIOMotorCollection,
        ttl_days: int = 90,
    ):
        self.delegate = delegate
        self.collection = collection
        self.ttl_days = ttl_days

    def _expires_at(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(days=self.ttl_days)

    async def geocode(self, query: str) -> GeocodingResult | None:
        if not query or not query.strip():
            return None
        h = _query_hash(query, "geocode")
        doc = await self.collection.find_one({"_id": h})
        if doc:
            expires = doc.get("expires_at")
            if expires and expires > datetime.now(timezone.utc):
                return _doc_to_result(doc)
            await self.collection.delete_one({"_id": h})

        result = await self.delegate.geocode(query)
        if result:
            cache_doc = {
                "_id": h,
                "query": query.strip(),
                "expires_at": self._expires_at(),
                **_result_to_doc(result),
            }
            await self.collection.update_one(
                {"_id": h},
                {"$set": cache_doc},
                upsert=True,
            )
        return result

    async def geocode_suggest(self, query: str, limit: int = 5) -> list[GeocodingResult]:
        return await self.delegate.geocode_suggest(query, limit=limit)

    async def reverse_geocode(self, lat: float, lon: float) -> GeocodingResult | None:
        query = f"{lat:.6f},{lon:.6f}"
        h = _query_hash(query, "reverse")
        doc = await self.collection.find_one({"_id": h})
        if doc:
            expires = doc.get("expires_at")
            if expires and expires > datetime.now(timezone.utc):
                return _doc_to_result(doc)
            await self.collection.delete_one({"_id": h})

        result = await self.delegate.reverse_geocode(lat, lon)
        if result:
            cache_doc = {
                "_id": h,
                "query": query,
                "expires_at": self._expires_at(),
                **_result_to_doc(result),
            }
            await self.collection.update_one(
                {"_id": h},
                {"$set": cache_doc},
                upsert=True,
            )
        return result
