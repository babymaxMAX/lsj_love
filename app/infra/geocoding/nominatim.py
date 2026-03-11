"""Nominatim (OpenStreetMap) геокодер."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.infra.geocoding.base import BaseGeocoder, GeocodingResult

logger = logging.getLogger(__name__)


def _normalize_query(raw: str) -> str:
    """Убирает префиксы г., город и т.п."""
    if not raw:
        return ""
    s = raw.strip()
    for prefix in ("г.", "г ", "город ", "гор. ", "гр. "):
        if s.lower().startswith(prefix):
            s = s[len(prefix) :].strip()
    return s.strip()


# Маленький словарь популярных алиасов
QUERY_ALIASES: dict[str, str] = {
    "мск": "Москва",
    "msk": "Москва",
    "moscow": "Москва",
    "спб": "Санкт-Петербург",
    "питер": "Санкт-Петербург",
    "piter": "Санкт-Петербург",
    "spb": "Санкт-Петербург",
    "saint petersburg": "Санкт-Петербург",
    "минск": "Минск",
    "minsk": "Минск",
    "мхч": "Махачкала",
    "makhachkala": "Махачкала",
    "махачкала": "Махачкала",
    "екб": "Екатеринбург",
    "екатеринбург": "Екатеринбург",
    "ekb": "Екатеринбург",
    "нн": "Нижний Новгород",
    "нижний новгород": "Нижний Новгород",
    "нск": "Новосибирск",
    "новосибирск": "Новосибирск",
}


class NominatimGeocoder(BaseGeocoder):
    """Геокодер через OSM Nominatim. Лимит ~1 req/sec, используйте кэш."""

    def __init__(
        self,
        base_url: str = "https://nominatim.openstreetmap.org",
        user_agent: str = "KupidonAI-DatingBot/1.0",
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout
        self._rate_limit = asyncio.Lock()
        self._last_request_time: float = 0.0

    async def _wait_rate_limit(self):
        """Nominatim требует не более 1 запроса в секунду."""
        async with self._rate_limit:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < 1.1:
                await asyncio.sleep(1.1 - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    def _extract_result(self, data: dict) -> GeocodingResult | None:
        lat = data.get("lat")
        lon = data.get("lon")
        if lat is None or lon is None:
            return None
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (TypeError, ValueError):
            return None

        def _s(v) -> str:
            return str(v).strip() if v is not None else ""

        address = data.get("address") or {}
        city = (
            _s(address.get("city"))
            or _s(address.get("town"))
            or _s(address.get("village"))
            or _s(address.get("municipality"))
            or _s(address.get("state_district"))
            or _s(address.get("state"))
            or _s(data.get("name"))
        )
        region = _s(address.get("state")) or _s(address.get("county"))
        country = _s(address.get("country"))
        display_name = _s(data.get("display_name")) or ", ".join(filter(None, [city or "?", region, country]))

        return GeocodingResult(
            lat=lat_f,
            lon=lon_f,
            city_name=city or "Неизвестно",
            region_name=region,
            country_name=country,
            display_name=display_name,
            confidence=0.9,
        )

    async def geocode(self, query: str) -> GeocodingResult | None:
        if not query or not query.strip():
            return None
        q = _normalize_query(query)
        if not q:
            return None

        # Попробовать алиас
        q_lower = q.lower().strip()
        if q_lower in QUERY_ALIASES:
            q = QUERY_ALIASES[q_lower]

        await self._wait_rate_limit()

        url = f"{self.base_url}/search"
        params = {
            "q": q,
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }
        headers = {"User-Agent": self.user_agent}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                items = resp.json()
        except Exception as e:
            logger.warning("Nominatim geocode failed for %r: %s", q, e)
            return None

        if not items or not isinstance(items, list):
            return None
        first = items[0]
        if not isinstance(first, dict):
            return None
        return self._extract_result(first)

    async def geocode_suggest(self, query: str, limit: int = 5) -> list[GeocodingResult]:
        """Подсказки для автодополнения города."""
        if not query or not query.strip() or limit < 1:
            return []
        q = _normalize_query(query)
        if not q:
            return []
        q_lower = q.lower().strip()
        if q_lower in QUERY_ALIASES:
            q = QUERY_ALIASES[q_lower]
        await self._wait_rate_limit()
        url = f"{self.base_url}/search"
        params = {
            "q": q,
            "format": "json",
            "limit": min(limit, 10),
            "addressdetails": 1,
        }
        headers = {"User-Agent": self.user_agent}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                items = resp.json()
        except Exception as e:
            logger.warning("Nominatim geocode_suggest failed for %r: %s", q, e)
            return []
        if not items or not isinstance(items, list):
            return []
        results: list[GeocodingResult] = []
        for item in items:
            if isinstance(item, dict) and (r := self._extract_result(item)):
                results.append(r)
        return results

    async def reverse_geocode(self, lat: float, lon: float) -> GeocodingResult | None:
        await self._wait_rate_limit()

        url = f"{self.base_url}/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "addressdetails": 1,
        }
        headers = {"User-Agent": self.user_agent}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning("Nominatim reverse_geocode failed for %.4f,%.4f: %s", lat, lon, e)
            return None

        if not data or not isinstance(data, dict):
            return None
        return self._extract_result(data)
