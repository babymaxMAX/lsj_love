"""One-way migration bridge: legacy Mongo -> core_v2 PostgreSQL.

Usage:
  python -m core_v2.tools.migrate_mongo_to_v2 --dry-run
  python -m core_v2.tools.migrate_mongo_to_v2
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core_v2.backend.models import (
    Match,
    Payment,
    Profile,
    Swipe,
    User,
)
from core_v2.backend.settings import V2Settings


settings = V2Settings()


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def migrate_users(dry_run: bool) -> dict:
    mongo = AsyncIOMotorClient("mongodb://mongodb:27017")
    db = mongo["dating"]
    engine = create_async_engine(settings.postgres_dsn, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    migrated = 0
    async with session_factory() as session:
        async for doc in db["users"].find({}):
            telegram_id = int(doc.get("telegram_id", 0))
            if telegram_id <= 0:
                continue
            existing = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if existing:
                continue
            row = User(
                telegram_id=telegram_id,
                username=doc.get("username"),
                is_active=bool(doc.get("is_active", True)),
                is_premium=bool(doc.get("is_premium", False)),
                premium_until=_utc(doc.get("premium_until")),
                referral_code=doc.get("referral_code") or f"ref_{telegram_id}",
            )
            session.add(row)
            migrated += 1
        if not dry_run:
            await session.commit()
        else:
            await session.rollback()

    mongo.close()
    await engine.dispose()
    return {"users_migrated": migrated}


async def consistency_report() -> dict:
    mongo = AsyncIOMotorClient("mongodb://mongodb:27017")
    db = mongo["dating"]
    engine = create_async_engine(settings.postgres_dsn, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    mongo_users = await db["users"].count_documents({})
    mongo_likes = await db["likes"].count_documents({})
    mongo_transactions = await db["transactions"].count_documents({})

    async with session_factory() as session:
        pg_users = await session.scalar(select(func.count()).select_from(User))
        pg_profiles = await session.scalar(select(func.count()).select_from(Profile))
        pg_swipes = await session.scalar(select(func.count()).select_from(Swipe))
        pg_matches = await session.scalar(select(func.count()).select_from(Match))
        pg_payments = await session.scalar(select(func.count()).select_from(Payment))

    mongo.close()
    await engine.dispose()
    return {
        "mongo": {
            "users": mongo_users,
            "likes": mongo_likes,
            "transactions": mongo_transactions,
        },
        "postgres": {
            "users": pg_users or 0,
            "profiles": pg_profiles or 0,
            "swipes": pg_swipes or 0,
            "matches": pg_matches or 0,
            "payments": pg_payments or 0,
        },
        "checks": {
            "users_delta": (pg_users or 0) - mongo_users,
        },
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    migrated = await migrate_users(dry_run=args.dry_run)
    report = await consistency_report()
    print({"dry_run": args.dry_run, **migrated, "consistency": report})


if __name__ == "__main__":
    asyncio.run(main())
