"""Создание индексов MongoDB при старте приложения."""
from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)


async def ensure_geo_indexes(
    client: AsyncIOMotorClient,
    db_name: str,
    users_collection: str,
) -> None:
    """Создаёт 2dsphere индекс для location (если поле есть у документов)."""
    col = client[db_name][users_collection]
    indexes = await col.index_information()
    if "location_2dsphere" in indexes:
        return
    try:
        await col.create_index([("location", "2dsphere")], name="location_2dsphere")
        logger.info("Created 2dsphere index on %s.%s.location", db_name, users_collection)
    except Exception as e:
        # Индекс может не создаться если нет документов с location — это ок
        logger.warning("Could not create location 2dsphere index: %s", e)
