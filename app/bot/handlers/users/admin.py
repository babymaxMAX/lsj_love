"""
Административная панель бота LSJ Love.
Полный функционал: статистика, пользователи, поиск, подписки, баны,
рассылки, онлайн, новые регистрации.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from motor.motor_asyncio import AsyncIOMotorClient
from punq import Container

from app.logic.init import init_container
from app.logic.services.base import BaseUsersService
from app.settings.config import Config

logger = logging.getLogger(__name__)

admin_router: Router = Router(name="Admin panel router")

ADMIN_IDS = {7741189969}

_container: Container = init_container()
_config: Config = _container.resolve(Config)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class AdminStates(StatesGroup):
    waiting_search = State()
    waiting_ban_id = State()
    waiting_unban_id = State()
    waiting_broadcast_text = State()
    waiting_broadcast_filter = State()
    waiting_premium_uid = State()
    waiting_premium_days = State()


# ─── Keyboards ───────────────────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats"),
            InlineKeyboardButton(text="🆕 Новые", callback_data="adm:recent"),
        ],
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="adm:users:1"),
            InlineKeyboardButton(text="🟢 Онлайн", callback_data="adm:online"),
        ],
        [
            InlineKeyboardButton(text="🔍 Поиск", callback_data="adm:search"),
            InlineKeyboardButton(text="🚫 Забаненные", callback_data="adm:banned"),
        ],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm:broadcast_menu")],
    ])


def back_kb(cb: str = "adm:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data=cb)]
    ])


def user_detail_kb(uid: int, is_banned: bool) -> InlineKeyboardMarkup:
    ban_text = "✅ Разбанить" if is_banned else "🚫 Забанить"
    ban_cb = f"adm:unban:{uid}" if is_banned else f"adm:ban:{uid}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ Premium 30д", callback_data=f"adm:prem:{uid}:premium:30"),
            InlineKeyboardButton(text="💎 VIP 30д", callback_data=f"adm:prem:{uid}:vip:30"),
        ],
        [
            InlineKeyboardButton(text="⭐ Premium 7д", callback_data=f"adm:prem:{uid}:premium:7"),
            InlineKeyboardButton(text="💎 VIP 7д", callback_data=f"adm:prem:{uid}:vip:7"),
        ],
        [InlineKeyboardButton(text="❌ Снять подписку", callback_data=f"adm:prem:{uid}:none:0")],
        [
            InlineKeyboardButton(text="💫 +5 Суперлайков", callback_data=f"adm:give:superlike:{uid}:5"),
            InlineKeyboardButton(text="💌 +5 Icebreakers", callback_data=f"adm:give:icebreaker:{uid}:5"),
        ],
        [
            InlineKeyboardButton(text=ban_text, callback_data=ban_cb),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"adm:del:{uid}"),
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="adm:main")],
    ])


def broadcast_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Всем пользователям", callback_data="adm:bc:all")],
        [InlineKeyboardButton(text="👨 Только мужчинам", callback_data="adm:bc:male")],
        [InlineKeyboardButton(text="👩 Только женщинам", callback_data="adm:bc:female")],
        [InlineKeyboardButton(text="⭐ Premium и VIP", callback_data="adm:bc:premium")],
        [InlineKeyboardButton(text="🆕 Новые (≤7 дней)", callback_data="adm:bc:new")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="adm:main")],
    ])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_db():
    client: AsyncIOMotorClient = _container.resolve(AsyncIOMotorClient)
    return client[_config.mongodb_dating_database]


def fmt_premium(pt: Optional[str], until) -> str:
    if not pt:
        return "Нет"
    label = {"premium": "⭐ Premium", "vip": "💎 VIP"}.get(pt, pt)
    if until:
        try:
            if isinstance(until, str):
                until = datetime.fromisoformat(until.replace("Z", "+00:00"))
            if hasattr(until, "tzinfo") and until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            days = (until - datetime.now(timezone.utc)).days
            return f"{label} ({days}д.)"
        except Exception:
            pass
    return label


def gender_icon(gender: str) -> str:
    g = (gender or "").lower().strip()
    if g in ("female", "женский", "женщина"):
        return "👩"
    if g in ("male", "man", "мужской", "мужчина"):
        return "👨"
    return "👤"


async def _build_user_card(doc: dict) -> str:
    uid = doc.get("telegram_id", "?")
    name = doc.get("name", "?")
    uname = f"@{doc['username']}" if doc.get("username") else "—"
    g_icon = gender_icon(doc.get("gender", ""))
    age = doc.get("age", "—")
    city = doc.get("city", "—")
    pt = fmt_premium(doc.get("premium_type"), doc.get("premium_until"))
    banned = " 🚫 ЗАБАНЕН" if doc.get("is_banned") else ""
    bal = float(doc.get("referral_balance", 0) or 0)
    photos = len(doc.get("photos", []) or [])
    last = doc.get("last_seen")
    last_str = "—"
    if last:
        try:
            if hasattr(last, "tzinfo") and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            mins = (datetime.now(timezone.utc) - last).seconds // 60
            if (datetime.now(timezone.utc) - last).days == 0 and mins < 5:
                last_str = "🟢 Онлайн"
            elif (datetime.now(timezone.utc) - last).days == 0:
                last_str = f"🟡 {mins}мин назад"
            else:
                last_str = f"⚪ {(datetime.now(timezone.utc) - last).days}д назад"
        except Exception:
            pass
    about = str(doc.get("about", "") or "")[:100]
    return (
        f"{g_icon} <b>{name}</b>{banned}\n"
        f"ID: <code>{uid}</code> | {uname}\n"
        f"Возраст: {age} | Город: {city}\n"
        f"Подписка: {pt}\n"
        f"Реф. баланс: {bal:.1f}₽ | Фото: {photos}шт\n"
        f"Статус: {last_str}\n"
        + (f"📝 {about}" if about else "")
    )


# ─── /admin command ───────────────────────────────────────────────────────────

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа.")
        return
    await message.answer(
        "🛠 <b>Панель администратора Kupidon AI</b>\n\nВыберите раздел:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


# ─── Main menu ────────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "adm:main")
async def cb_main(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    await state.clear()
    try:
        await cq.message.edit_text(
            "🛠 <b>Панель администратора Kupidon AI</b>\n\nВыберите раздел:",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
    except Exception:
        await cq.message.answer(
            "🛠 <b>Панель администратора Kupidon AI</b>",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
    await cq.answer()


# ─── Statistics ───────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "adm:stats")
async def cb_stats(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    await cq.answer("⏳")
    db = _get_db()
    col = db[_config.mongodb_users_collection]
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    total = await col.count_documents({})
    active = await col.count_documents({"is_active": True, "is_banned": {"$ne": True}})
    banned = await col.count_documents({"is_banned": True})
    new_today = await col.count_documents({"created_at": {"$gte": today}})
    new_week = await col.count_documents({"created_at": {"$gte": week_ago}})
    online = await col.count_documents({"last_seen": {"$gte": now - timedelta(minutes=5)}})
    premium = await col.count_documents({"premium_type": "premium", "premium_until": {"$gt": now}})
    vip = await col.count_documents({"premium_type": "vip", "premium_until": {"$gt": now}})
    male = await col.count_documents({"gender": {"$in": ["male", "мужской"]}})
    female = await col.count_documents({"gender": {"$in": ["female", "женский"]}})
    with_photo = await col.count_documents({"$or": [
        {"photos": {"$exists": True, "$not": {"$size": 0}}},
        {"photo": {"$exists": True, "$ne": None, "$ne": ""}},
    ]})

    text = (
        "📊 <b>Статистика Kupidon AI</b>\n\n"
        f"👤 Всего пользователей: <b>{total}</b>\n"
        f"✅ Активных: <b>{active}</b>\n"
        f"🚫 Забанено: <b>{banned}</b>\n\n"
        f"📅 Новых сегодня: <b>{new_today}</b>\n"
        f"📆 Новых за неделю: <b>{new_week}</b>\n"
        f"🟢 Онлайн сейчас (5мин): <b>{online}</b>\n\n"
        f"⭐ Premium: <b>{premium}</b>\n"
        f"💎 VIP: <b>{vip}</b>\n\n"
        f"👨 Мужчин: <b>{male}</b>\n"
        f"👩 Женщин: <b>{female}</b>\n"
        f"📷 С фото: <b>{with_photo}</b> из {total}"
    )
    await cq.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")


# ─── Recent registrations ────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "adm:recent")
async def cb_recent(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    await cq.answer("⏳")
    db = _get_db()
    col = db[_config.mongodb_users_collection]
    cursor = col.find({}, {"telegram_id": 1, "name": 1, "username": 1, "gender": 1,
                           "created_at": 1, "premium_type": 1}).sort("created_at", -1).limit(10)
    docs = await cursor.to_list(10)
    if not docs:
        await cq.message.edit_text("Нет пользователей.", reply_markup=back_kb())
        return
    lines = ["🆕 <b>Последние 10 регистраций</b>\n"]
    kb_rows = []
    for d in docs:
        uid = d.get("telegram_id")
        name = d.get("name", "?")
        g = gender_icon(d.get("gender", ""))
        uname = f"@{d['username']}" if d.get("username") else "—"
        created = d.get("created_at")
        time_str = ""
        if created:
            try:
                if hasattr(created, "tzinfo") and created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - created
                if delta.days == 0:
                    time_str = f"{delta.seconds // 3600}ч назад"
                else:
                    time_str = f"{delta.days}д назад"
            except Exception:
                pass
        lines.append(f"{g} <b>{name}</b> | {uname} | {time_str}")
        kb_rows.append([InlineKeyboardButton(text=f"{g} {name} ({uid})", callback_data=f"adm:user:{uid}")])
    kb_rows.append([InlineKeyboardButton(text="◀️ Меню", callback_data="adm:main")])
    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="HTML",
    )


# ─── Online users ────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "adm:online")
async def cb_online(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    await cq.answer("⏳")
    db = _get_db()
    col = db[_config.mongodb_users_collection]
    now = datetime.now(timezone.utc)
    cursor = col.find(
        {"last_seen": {"$gte": now - timedelta(minutes=5)}},
        {"telegram_id": 1, "name": 1, "username": 1, "gender": 1, "last_seen": 1}
    ).limit(20)
    docs = await cursor.to_list(20)
    if not docs:
        await cq.message.edit_text("🟢 Нет пользователей онлайн.", reply_markup=back_kb())
        return
    lines = [f"🟢 <b>Онлайн прямо сейчас ({len(docs)})</b>\n"]
    kb_rows = []
    for d in docs:
        uid = d.get("telegram_id")
        name = d.get("name", "?")
        g = gender_icon(d.get("gender", ""))
        uname = f"@{d['username']}" if d.get("username") else "—"
        lines.append(f"{g} <b>{name}</b> | {uname}")
        kb_rows.append([InlineKeyboardButton(text=f"{g} {name} ({uid})", callback_data=f"adm:user:{uid}")])
    kb_rows.append([InlineKeyboardButton(text="◀️ Меню", callback_data="adm:main")])
    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="HTML",
    )


# ─── Banned users ────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "adm:banned")
async def cb_banned(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    await cq.answer("⏳")
    db = _get_db()
    col = db[_config.mongodb_users_collection]
    cursor = col.find(
        {"is_banned": True},
        {"telegram_id": 1, "name": 1, "username": 1, "gender": 1}
    ).limit(20)
    docs = await cursor.to_list(20)
    if not docs:
        await cq.message.edit_text("🚫 Забаненных пользователей нет.", reply_markup=back_kb())
        return
    lines = [f"🚫 <b>Забаненные ({len(docs)})</b>\n"]
    kb_rows = []
    for d in docs:
        uid = d.get("telegram_id")
        name = d.get("name", "?")
        g = gender_icon(d.get("gender", ""))
        uname = f"@{d['username']}" if d.get("username") else "—"
        lines.append(f"{g} <b>{name}</b> | {uname} | <code>{uid}</code>")
        kb_rows.append([InlineKeyboardButton(text=f"✅ Разбанить {name}", callback_data=f"adm:unban:{uid}")])
    kb_rows.append([InlineKeyboardButton(text="◀️ Меню", callback_data="adm:main")])
    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="HTML",
    )


# ─── Users list ───────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data.startswith("adm:users:"))
async def cb_users(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    page = int(cq.data.split(":")[-1])
    await cq.answer("⏳")
    db = _get_db()
    col = db[_config.mongodb_users_collection]
    limit = 8
    skip = (page - 1) * limit
    total = await col.count_documents({})
    pages = max(1, (total + limit - 1) // limit)
    cursor = col.find(
        {},
        {"telegram_id": 1, "name": 1, "username": 1, "gender": 1,
         "premium_type": 1, "premium_until": 1, "is_banned": 1, "last_seen": 1}
    ).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)

    lines = [f"👥 <b>Пользователи</b> (стр. {page}/{pages}, всего {total})\n"]
    kb_rows = []
    for d in docs:
        uid = d.get("telegram_id")
        name = d.get("name", "?")
        g = gender_icon(d.get("gender", ""))
        pt = fmt_premium(d.get("premium_type"), d.get("premium_until"))
        banned = " 🚫" if d.get("is_banned") else ""
        lines.append(f"{g} <b>{name}</b>{banned} — {pt}")
        kb_rows.append([InlineKeyboardButton(text=f"{g} {name} ({uid}){banned}", callback_data=f"adm:user:{uid}")])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"adm:users:{page-1}"))
    if page < pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"adm:users:{page+1}"))
    if nav:
        kb_rows.append(nav)
    kb_rows.append([InlineKeyboardButton(text="◀️ Меню", callback_data="adm:main")])
    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="HTML",
    )


# ─── User detail ──────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data.startswith("adm:user:"))
async def cb_user_detail(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    uid = int(cq.data.split(":")[-1])
    await cq.answer("⏳")
    db = _get_db()
    col = db[_config.mongodb_users_collection]
    doc = await col.find_one({"telegram_id": uid})
    if not doc:
        await cq.message.edit_text("❌ Пользователь не найден.", reply_markup=back_kb())
        return

    text = await _build_user_card(doc)
    is_banned = bool(doc.get("is_banned"))

    # Пробуем показать фото профиля
    photos = doc.get("photos", []) or []
    photo_key = photos[0] if photos else doc.get("photo", "")
    sent_with_photo = False

    if photo_key:
        from app.bot.utils.notificator import _resolve_photo
        try:
            raw = await _resolve_photo(photo_key, user_id=uid)
            if raw:
                kb = user_detail_kb(uid, is_banned)
                try:
                    await cq.message.delete()
                except Exception:
                    pass
                if isinstance(raw, bytes):
                    await cq.message.answer_photo(
                        photo=BufferedInputFile(raw, filename="photo.jpg"),
                        caption=text,
                        reply_markup=kb,
                        parse_mode="HTML",
                    )
                else:
                    await cq.message.answer_photo(
                        photo=raw,
                        caption=text,
                        reply_markup=kb,
                        parse_mode="HTML",
                    )
                sent_with_photo = True
        except Exception as e:
            logger.warning(f"Admin photo load error: {e}")

    if not sent_with_photo:
        try:
            await cq.message.edit_text(text, reply_markup=user_detail_kb(uid, is_banned), parse_mode="HTML")
        except Exception:
            await cq.message.answer(text, reply_markup=user_detail_kb(uid, is_banned), parse_mode="HTML")


# ─── Grant premium ────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data.startswith("adm:prem:"))
async def cb_set_premium(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    parts = cq.data.split(":")
    uid = int(parts[2])
    ptype = parts[3]
    days = int(parts[4])
    db = _get_db()
    col = db[_config.mongodb_users_collection]
    if ptype == "none":
        await col.update_one({"telegram_id": uid}, {"$set": {"premium_type": None, "premium_until": None}})
        await cq.answer("❌ Подписка снята!", show_alert=True)
    else:
        until = datetime.now(timezone.utc) + timedelta(days=days)
        await col.update_one({"telegram_id": uid}, {"$set": {"premium_type": ptype, "premium_until": until}})
        label = {"premium": "⭐ Premium", "vip": "💎 VIP"}.get(ptype, ptype)
        await cq.answer(f"✅ {label} на {days} дней выдан!", show_alert=True)
    # Уведомляем пользователя
    try:
        label_map = {"premium": "⭐ Premium", "vip": "💎 VIP", "none": None}
        if ptype != "none":
            await cq.bot.send_message(
                uid,
                f"🎉 Тебе выдана подписка <b>{label_map.get(ptype, ptype)}</b> на {days} дней!\n\nПриятного использования 💕",
                parse_mode="HTML",
            )
    except Exception:
        pass


# ─── Give credits (superlike / icebreaker) ───────────────────────────────────

@admin_router.callback_query(F.data.startswith("adm:give:"))
async def cb_give_credits(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    # adm:give:superlike:{uid}:{amount}  or  adm:give:icebreaker:{uid}:{amount}
    parts = cq.data.split(":")
    credit_type = parts[2]   # "superlike" | "icebreaker"
    uid = int(parts[3])
    amount = int(parts[4])

    db = _get_db()
    col = db[_config.mongodb_users_collection]

    if credit_type == "superlike":
        await col.update_one({"telegram_id": uid}, {"$inc": {"superlike_credits": amount}})
        label = f"💫 +{amount} суперлайков"
        notify = f"💫 Тебе выдано <b>{amount} суперлайков</b>!\n\nТы можешь использовать их при просмотре анкет. 💕"
    elif credit_type == "icebreaker":
        await col.update_one({"telegram_id": uid}, {"$inc": {"icebreaker_used": -amount}})
        label = f"💌 +{amount} Icebreakers"
        notify = f"💌 Тебе выдано <b>{amount} AI Icebreakers</b>!\n\nТы можешь написать первым — ИИ поможет составить сообщение. 💕"
    else:
        await cq.answer("❌ Неизвестный тип")
        return

    await cq.answer(f"✅ {label} выдан!", show_alert=True)
    try:
        await cq.bot.send_message(uid, notify, parse_mode="HTML")
    except Exception:
        pass


# ─── Ban ─────────────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data.startswith("adm:ban:"))
async def cb_ban(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    uid = int(cq.data.split(":")[-1])
    db = _get_db()
    await db[_config.mongodb_users_collection].update_one(
        {"telegram_id": uid},
        {"$set": {"is_banned": True, "is_active": False}}
    )
    await cq.answer("🚫 Пользователь забанен!", show_alert=True)
    try:
        await cq.bot.send_message(uid, "🚫 Ваш аккаунт заблокирован администрацией Kupidon AI.")
    except Exception:
        pass
    doc = await db[_config.mongodb_users_collection].find_one({"telegram_id": uid})
    if doc:
        text = await _build_user_card(doc)
        try:
            await cq.message.edit_text(text, reply_markup=user_detail_kb(uid, True), parse_mode="HTML")
        except Exception:
            await cq.message.answer(text, reply_markup=user_detail_kb(uid, True), parse_mode="HTML")


# ─── Unban ────────────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data.startswith("adm:unban:"))
async def cb_unban(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    uid = int(cq.data.split(":")[-1])
    db = _get_db()
    await db[_config.mongodb_users_collection].update_one(
        {"telegram_id": uid},
        {"$set": {"is_banned": False, "is_active": True}}
    )
    await cq.answer("✅ Пользователь разбанен!", show_alert=True)
    try:
        await cq.bot.send_message(uid, "✅ Ваш аккаунт разблокирован. Добро пожаловать обратно в Kupidon AI!")
    except Exception:
        pass
    doc = await db[_config.mongodb_users_collection].find_one({"telegram_id": uid})
    if doc:
        text = await _build_user_card(doc)
        try:
            await cq.message.edit_text(text, reply_markup=user_detail_kb(uid, False), parse_mode="HTML")
        except Exception:
            await cq.message.answer(text, reply_markup=user_detail_kb(uid, False), parse_mode="HTML")


# ─── Delete user ──────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data.startswith("adm:del:"))
async def cb_delete(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    uid = int(cq.data.split(":")[-1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"adm:delconf:{uid}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"adm:user:{uid}")],
    ])
    try:
        await cq.message.edit_text(
            f"⚠️ Удалить анкету пользователя <code>{uid}</code>?\nДействие необратимо.",
            reply_markup=kb, parse_mode="HTML",
        )
    except Exception:
        await cq.message.answer(
            f"⚠️ Удалить анкету <code>{uid}</code>?",
            reply_markup=kb, parse_mode="HTML",
        )
    await cq.answer()


@admin_router.callback_query(F.data.startswith("adm:delconf:"))
async def cb_delete_confirm(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    uid = int(cq.data.split(":")[-1])
    db = _get_db()
    await db[_config.mongodb_users_collection].delete_one({"telegram_id": uid})
    await db[_config.mongodb_likes_collection].delete_many(
        {"$or": [{"from_user": uid}, {"to_user": uid}]}
    )
    await cq.answer("🗑 Удалено!", show_alert=True)
    await cq.message.edit_text("🗑 Анкета удалена.", reply_markup=back_kb())


# ─── Search ───────────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "adm:search")
async def cb_search_prompt(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    await state.set_state(AdminStates.waiting_search)
    try:
        await cq.message.edit_text(
            "🔍 Введите <b>Telegram ID</b>, имя или @username:",
            reply_markup=back_kb(), parse_mode="HTML",
        )
    except Exception:
        await cq.message.answer(
            "🔍 Введите <b>Telegram ID</b>, имя или @username:",
            reply_markup=back_kb(), parse_mode="HTML",
        )
    await cq.answer()


@admin_router.message(AdminStates.waiting_search)
async def msg_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    q = message.text.strip().lstrip("@")
    db = _get_db()
    col = db[_config.mongodb_users_collection]
    try:
        qint = int(q)
        query = {"telegram_id": qint}
    except ValueError:
        query = {"$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"username": {"$regex": q, "$options": "i"}},
        ]}
    docs = await col.find(query, {"telegram_id": 1, "name": 1, "username": 1, "gender": 1,
                                   "premium_type": 1, "premium_until": 1, "is_banned": 1}).limit(10).to_list(10)
    if not docs:
        await message.answer("❌ Не найдено.", reply_markup=back_kb())
        return
    kb_rows = []
    lines = [f"🔍 Найдено: {len(docs)}\n"]
    for d in docs:
        uid = d.get("telegram_id")
        name = d.get("name", "?")
        g = gender_icon(d.get("gender", ""))
        uname = f"@{d['username']}" if d.get("username") else "—"
        banned = " 🚫" if d.get("is_banned") else ""
        lines.append(f"{g} <b>{name}</b> | {uname} | <code>{uid}</code>{banned}")
        kb_rows.append([InlineKeyboardButton(text=f"{g} {name} ({uid}){banned}", callback_data=f"adm:user:{uid}")])
    kb_rows.append([InlineKeyboardButton(text="◀️ Меню", callback_data="adm:main")])
    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="HTML",
    )


# ─── Broadcast ────────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "adm:broadcast_menu")
async def cb_broadcast_menu(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    try:
        await cq.message.edit_text(
            "📢 <b>Рассылка</b>\n\nВыберите аудиторию:",
            reply_markup=broadcast_menu_kb(), parse_mode="HTML",
        )
    except Exception:
        await cq.message.answer(
            "📢 <b>Рассылка</b>\n\nВыберите аудиторию:",
            reply_markup=broadcast_menu_kb(), parse_mode="HTML",
        )
    await cq.answer()


@admin_router.callback_query(F.data.startswith("adm:bc:"))
async def cb_broadcast_select(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    audience = cq.data.split(":")[-1]
    audience_map = {
        "all": "всем пользователям",
        "male": "мужчинам",
        "female": "женщинам",
        "premium": "Premium и VIP",
        "new": "новым (≤7 дней)",
    }
    await state.set_state(AdminStates.waiting_broadcast_text)
    await state.update_data(audience=audience)
    try:
        await cq.message.edit_text(
            f"📢 Рассылка <b>{audience_map.get(audience, audience)}</b>\n\n"
            f"Введите текст сообщения (поддерживается HTML разметка):",
            reply_markup=back_kb("adm:broadcast_menu"), parse_mode="HTML",
        )
    except Exception:
        await cq.message.answer(
            f"📢 Введите текст для рассылки <b>{audience_map.get(audience, audience)}</b>:",
            reply_markup=back_kb("adm:broadcast_menu"), parse_mode="HTML",
        )
    await cq.answer()


@admin_router.message(AdminStates.waiting_broadcast_text)
async def msg_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    audience = data.get("audience", "all")
    await state.clear()
    text = message.text or message.caption or ""
    if not text.strip():
        await message.answer("❌ Пустое сообщение. Рассылка отменена.", reply_markup=back_kb())
        return

    db = _get_db()
    col = db[_config.mongodb_users_collection]
    now = datetime.now(timezone.utc)

    query: dict = {"is_banned": {"$ne": True}, "is_active": True}
    if audience == "male":
        query["gender"] = {"$in": ["male", "мужской"]}
    elif audience == "female":
        query["gender"] = {"$in": ["female", "женский"]}
    elif audience == "premium":
        query["premium_type"] = {"$in": ["premium", "vip"]}
        query["premium_until"] = {"$gt": now}
    elif audience == "new":
        query["created_at"] = {"$gte": now - timedelta(days=7)}

    cursor = col.find(query, {"telegram_id": 1})
    uids = [d["telegram_id"] async for d in cursor]

    status_msg = await message.answer(f"⏳ Рассылка {len(uids)} пользователям...")
    sent = 0
    failed = 0
    for uid in uids:
        try:
            await message.bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}",
        reply_markup=back_kb(),
    )
