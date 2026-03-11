"""
Admin Panel API — управление пользователями, статистика, рассылки.
Защита: заголовок X-Admin-Key должен совпадать с ADMIN_SECRET_KEY из .env
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from punq import Container

from app.logic.init import init_container
from app.settings.config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Авторизация ────────────────────────────────────────────────────────────────

def _check_admin(x_admin_key: str = Header(None), container: Container = Depends(init_container)):
    config: Config = container.resolve(Config)
    secret = (getattr(config, "admin_secret_key", None) or "").strip()
    if not secret or x_admin_key != secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key")


# ── Схемы ──────────────────────────────────────────────────────────────────────

class BanRequest(BaseModel):
    ban: bool = True
    reason: str = ""


class PremiumGrantRequest(BaseModel):
    premium_type: str  # "premium" | "vip" | None
    days: int = 30


class BroadcastRequest(BaseModel):
    text: str
    photo_url: Optional[str] = None
    target: str = "all"        # "all" | "premium" | "vip" | "active_7d" | "no_premium"
    parse_mode: str = "HTML"


# ── Статистика ─────────────────────────────────────────────────────────────────

@router.get("/stats", dependencies=[Depends(_check_admin)])
async def admin_stats(container: Container = Depends(init_container)):
    """Общая статистика: пользователи, лайки, матчи, подписки."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)

    users_col = client[config.mongodb_dating_database][config.mongodb_users_collection]
    likes_col  = client[config.mongodb_dating_database][config.mongodb_likes_collection]

    now = datetime.now(timezone.utc)
    day_ago   = now - timedelta(days=1)
    week_ago  = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users    = await users_col.count_documents({})
    active_users   = await users_col.count_documents({"is_active": True})
    banned_users   = await users_col.count_documents({"is_banned": True})
    new_today      = await users_col.count_documents({"created_at": {"$gte": day_ago}})
    new_week       = await users_col.count_documents({"created_at": {"$gte": week_ago}})
    new_month      = await users_col.count_documents({"created_at": {"$gte": month_ago}})

    online_5min    = await users_col.count_documents({"last_seen": {"$gte": now - timedelta(minutes=5)}})
    online_hour    = await users_col.count_documents({"last_seen": {"$gte": now - timedelta(hours=1)}})

    premium_count  = await users_col.count_documents({"premium_type": "premium", "premium_until": {"$gt": now}})
    vip_count      = await users_col.count_documents({"premium_type": "vip", "premium_until": {"$gt": now}})

    total_likes    = await likes_col.count_documents({})
    matches_count  = await likes_col.count_documents({"is_match": True})
    likes_today    = await likes_col.count_documents({"created_at": {"$gte": day_ago}})

    male_count   = await users_col.count_documents({"gender": {"$in": ["Man", "man", "Male", "male", "Мужской", "мужской"]}})
    female_count = await users_col.count_documents({"gender": {"$in": ["Female", "female", "Woman", "woman", "Женский", "женский"]}})

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "banned": banned_users,
            "online_5min": online_5min,
            "online_hour": online_hour,
            "new_today": new_today,
            "new_week": new_week,
            "new_month": new_month,
            "male": male_count,
            "female": female_count,
        },
        "subscriptions": {
            "premium": premium_count,
            "vip": vip_count,
            "free": total_users - premium_count - vip_count,
        },
        "activity": {
            "total_likes": total_likes,
            "matches": matches_count,
            "likes_today": likes_today,
        },
    }


# ── Пользователи ───────────────────────────────────────────────────────────────

@router.get("/users", dependencies=[Depends(_check_admin)])
async def admin_list_users(
    page: int = 1,
    limit: int = 20,
    search: str = "",
    gender: str = "",
    premium: str = "",
    banned: str = "",
    container: Container = Depends(init_container),
):
    """Список пользователей с поиском и фильтрами."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)
    col = client[config.mongodb_dating_database][config.mongodb_users_collection]

    now = datetime.now(timezone.utc)
    query: dict = {}

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"username": {"$regex": search, "$options": "i"}},
            {"city": {"$regex": search, "$options": "i"}},
        ]
        # Поиск по telegram_id если число
        if search.isdigit():
            query["$or"].append({"telegram_id": int(search)})

    if gender in ("Man", "Female"):
        _ALL_MALE   = ["Man", "man", "Male", "male", "Мужской", "мужской"]
        _ALL_FEMALE = ["Female", "female", "Женский", "женский", "Woman", "woman"]
        query["gender"] = {"$in": _ALL_MALE if gender == "Man" else _ALL_FEMALE}

    if premium == "premium":
        query["premium_type"] = "premium"
        query["premium_until"] = {"$gt": now}
    elif premium == "vip":
        query["premium_type"] = "vip"
        query["premium_until"] = {"$gt": now}
    elif premium == "free":
        query["$or"] = query.get("$or", []) + [
            {"premium_type": None},
            {"premium_type": {"$exists": False}},
            {"premium_until": {"$lte": now}},
        ]

    if banned == "true":
        query["is_banned"] = True
    elif banned == "false":
        query["is_banned"] = {"$ne": True}

    total = await col.count_documents(query)
    skip = (page - 1) * limit

    cursor = col.find(query, {
        "telegram_id": 1, "name": 1, "username": 1, "gender": 1,
        "age": 1, "city": 1, "is_active": 1, "is_banned": 1,
        "premium_type": 1, "premium_until": 1, "last_seen": 1,
        "created_at": 1, "photos": 1, "photo": 1,
    }).sort("created_at", -1).skip(skip).limit(limit)

    users = []
    async for doc in cursor:
        doc.pop("_id", None)
        users.append(doc)

    return {"total": total, "page": page, "limit": limit, "items": users}


@router.get("/users/{user_id}", dependencies=[Depends(_check_admin)])
async def admin_get_user(user_id: int, container: Container = Depends(init_container)):
    """Детальная информация о пользователе."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)
    col = client[config.mongodb_dating_database][config.mongodb_users_collection]
    likes_col = client[config.mongodb_dating_database][config.mongodb_likes_collection]

    doc = await col.find_one({"telegram_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    doc.pop("_id", None)

    # Статистика лайков
    likes_given    = await likes_col.count_documents({"from_user": user_id})
    likes_received = await likes_col.count_documents({"to_user": user_id})
    matches        = await likes_col.count_documents({"$or": [
        {"from_user": user_id, "is_match": True},
        {"to_user": user_id, "is_match": True},
    ]})

    doc["stats"] = {
        "likes_given": likes_given,
        "likes_received": likes_received,
        "matches": matches,
    }
    return doc


@router.put("/users/{user_id}/ban", dependencies=[Depends(_check_admin)])
async def admin_ban_user(user_id: int, body: BanRequest, container: Container = Depends(init_container)):
    """Забанить / разбанить пользователя."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)
    col = client[config.mongodb_dating_database][config.mongodb_users_collection]

    update = {"is_banned": body.ban, "is_active": not body.ban}
    if body.reason:
        update["ban_reason"] = body.reason

    result = await col.update_one({"telegram_id": user_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"ok": True, "banned": body.ban, "user_id": user_id}


@router.delete("/users/{user_id}", dependencies=[Depends(_check_admin)])
async def admin_delete_user(user_id: int, container: Container = Depends(init_container)):
    """Удалить пользователя полностью."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)

    col = client[config.mongodb_dating_database][config.mongodb_users_collection]
    likes_col = client[config.mongodb_dating_database][config.mongodb_likes_collection]

    result = await col.delete_one({"telegram_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    # Удаляем лайки
    await likes_col.delete_many({"$or": [{"from_user": user_id}, {"to_user": user_id}]})

    return {"ok": True, "deleted": user_id}


@router.put("/users/{user_id}/premium", dependencies=[Depends(_check_admin)])
async def admin_grant_premium(user_id: int, body: PremiumGrantRequest, container: Container = Depends(init_container)):
    """Выдать или отозвать подписку вручную."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)
    col = client[config.mongodb_dating_database][config.mongodb_users_collection]

    now = datetime.now(timezone.utc)
    if body.premium_type in ("premium", "vip"):
        update = {
            "premium_type": body.premium_type,
            "premium_until": now + timedelta(days=body.days),
        }
    else:
        update = {"premium_type": None, "premium_until": None}

    result = await col.update_one({"telegram_id": user_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"ok": True, "user_id": user_id, "premium_type": body.premium_type, "days": body.days}


@router.put("/users/{user_id}/active", dependencies=[Depends(_check_admin)])
async def admin_toggle_active(user_id: int, active: bool = True, container: Container = Depends(init_container)):
    """Активировать / деактивировать анкету."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)
    col = client[config.mongodb_dating_database][config.mongodb_users_collection]

    result = await col.update_one({"telegram_id": user_id}, {"$set": {"is_active": active}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "is_active": active}


# ── Рассылка ───────────────────────────────────────────────────────────────────

# ── Репорты ──────────────────────────────────────────────────────────────────

class ResolveReportRequest(BaseModel):
    action: str  # "ban" | "unban" | "hide_profile" | "delete" | "dismiss"
    reason: str = ""


@router.get("/reports", dependencies=[Depends(_check_admin)])
async def admin_list_reports(
    page: int = 1,
    limit: int = 20,
    status: str = "",
    container: Container = Depends(init_container),
):
    """Список репортов с фильтром по статусу."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)
    col = client[config.mongodb_dating_database]["reports"]

    query = {}
    if status in ("pending", "resolved", "dismissed"):
        query["status"] = status
    total = await col.count_documents(query)
    skip = (page - 1) * limit
    cursor = col.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id", ""))
        items.append(doc)
    return {"total": total, "page": page, "limit": limit, "items": items}


@router.get("/reports/{report_id}", dependencies=[Depends(_check_admin)])
async def admin_get_report(
    report_id: str,
    container: Container = Depends(init_container),
):
    """Детали репорта."""
    from bson import ObjectId
    from motor.motor_asyncio import AsyncIOMotorClient
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)
    col = client[config.mongodb_dating_database]["reports"]
    try:
        doc = await col.find_one({"_id": ObjectId(report_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid report id")
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.put("/reports/{report_id}/resolve", dependencies=[Depends(_check_admin)])
async def admin_resolve_report(
    report_id: str,
    body: ResolveReportRequest,
    container: Container = Depends(init_container),
):
    """Обработать репорт: ban/unban, hide_profile, delete, dismiss."""
    from bson import ObjectId
    from motor.motor_asyncio import AsyncIOMotorClient
    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)
    col = client[config.mongodb_dating_database]["reports"]
    users_col = client[config.mongodb_dating_database][config.mongodb_users_collection]
    likes_col = client[config.mongodb_dating_database][config.mongodb_likes_collection]
    try:
        doc = await col.find_one({"_id": ObjectId(report_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid report id")
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")
    target_id = doc.get("to_user")
    from_user = doc.get("from_user")

    if body.action == "ban" and target_id:
        await users_col.update_one(
            {"telegram_id": target_id},
            {"$set": {"is_banned": True, "is_active": False, "ban_reason": body.reason}},
        )
    elif body.action == "unban" and target_id:
        await users_col.update_one(
            {"telegram_id": target_id},
            {"$set": {"is_banned": False, "is_active": True}, "$unset": {"ban_reason": ""}},
        )
    elif body.action == "hide_profile" and target_id:
        await users_col.update_one(
            {"telegram_id": target_id},
            {"$set": {"profile_hidden": True}},
        )
    elif body.action == "delete" and target_id:
        await users_col.delete_one({"telegram_id": target_id})
        await likes_col.delete_many({"$or": [{"from_user": target_id}, {"to_user": target_id}]})
    # dismiss = только закрыть репорт без действий

    await col.update_one(
        {"_id": ObjectId(report_id)},
        {"$set": {"status": "resolved" if body.action != "dismiss" else "dismissed", "resolved_action": body.action, "resolved_reason": body.reason}},
    )
    return {"ok": True, "action": body.action, "target_id": target_id}


# ── Рассылка ───────────────────────────────────────────────────────────────────

@router.post("/broadcast", dependencies=[Depends(_check_admin)])
async def admin_broadcast(body: BroadcastRequest, container: Container = Depends(init_container)):
    """Массовая рассылка сообщений через Telegram бот."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from aiogram import Bot

    client: AsyncIOMotorClient = container.resolve(AsyncIOMotorClient)
    config: Config = container.resolve(Config)
    col = client[config.mongodb_dating_database][config.mongodb_users_collection]

    now = datetime.now(timezone.utc)

    # Формируем фильтр получателей
    query: dict = {"is_banned": {"$ne": True}}
    if body.target == "premium":
        query["premium_type"] = "premium"
        query["premium_until"] = {"$gt": now}
    elif body.target == "vip":
        query["premium_type"] = "vip"
        query["premium_until"] = {"$gt": now}
    elif body.target == "active_7d":
        query["last_seen"] = {"$gte": now - timedelta(days=7)}
    elif body.target == "no_premium":
        query["$or"] = [
            {"premium_type": None},
            {"premium_type": {"$exists": False}},
            {"premium_until": {"$lte": now}},
        ]

    cursor = col.find(query, {"telegram_id": 1})
    user_ids = [doc["telegram_id"] async for doc in cursor]

    bot = Bot(token=config.token)
    sent = 0
    failed = 0

    for uid in user_ids:
        try:
            if body.photo_url:
                await bot.send_photo(
                    chat_id=uid,
                    photo=body.photo_url,
                    caption=body.text,
                    parse_mode=body.parse_mode,
                )
            else:
                await bot.send_message(
                    chat_id=uid,
                    text=body.text,
                    parse_mode=body.parse_mode,
                )
            sent += 1
        except Exception as e:
            logger.warning(f"broadcast: failed to send to {uid}: {e}")
            failed += 1

    await bot.session.close()
    return {"sent": sent, "failed": failed, "total": len(user_ids)}
