"""Административная панель бота LSJ Love."""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

logger = logging.getLogger(__name__)

admin_router: Router = Router(name="Admin panel router")

ADMIN_IDS = {7741189969}
API_BASE = "http://localhost:8000/api/v1/users"
ADMIN_SECRET = "lsjlove_admin_2026"


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class AdminStates(StatesGroup):
    waiting_user_id = State()
    waiting_premium_days = State()
    waiting_ban_id = State()
    waiting_search = State()


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats")],
        [InlineKeyboardButton(text="👥 Список пользователей", callback_data="adm:users:1")],
        [InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="adm:search")],
        [InlineKeyboardButton(text="🚫 Забанить пользователя", callback_data="adm:ban_prompt")],
        [InlineKeyboardButton(text="✅ Разбанить пользователя", callback_data="adm:unban_prompt")],
    ])


def back_to_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="adm:main")]
    ])


async def fetch(endpoint: str, method: str = "GET", **kwargs) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"{API_BASE}{endpoint}"
            if method == "GET":
                resp = await client.get(url, params={"secret": ADMIN_SECRET, **kwargs})
            elif method == "POST":
                resp = await client.post(url, params={"secret": ADMIN_SECRET}, json=kwargs)
            elif method == "DELETE":
                resp = await client.delete(url, params={"secret": ADMIN_SECRET})
            else:
                return None
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error(f"Admin API error: {e}")
    return None


def fmt_premium(pt: Optional[str], until: Optional[str]) -> str:
    if not pt:
        return "Нет"
    label = {"premium": "Premium", "vip": "VIP"}.get(pt, pt)
    if until and until != "None":
        try:
            dt = datetime.fromisoformat(until.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            days_left = (dt - datetime.now(timezone.utc)).days
            return f"{label} ({days_left}д.)"
        except Exception:
            pass
    return label


def user_detail_kb(uid: int, is_banned: bool) -> InlineKeyboardMarkup:
    ban_btn = (
        InlineKeyboardButton(text="✅ Разбанить", callback_data=f"adm:unban:{uid}")
        if is_banned
        else InlineKeyboardButton(text="🚫 Забанить", callback_data=f"adm:ban:{uid}")
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Выдать Premium 30д", callback_data=f"adm:prem:{uid}:premium:30")],
        [InlineKeyboardButton(text="💎 Выдать VIP 30д", callback_data=f"adm:prem:{uid}:vip:30")],
        [InlineKeyboardButton(text="❌ Снять подписку", callback_data=f"adm:prem:{uid}:none:0")],
        [ban_btn, InlineKeyboardButton(text="🗑 Удалить анкету", callback_data=f"adm:del:{uid}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="adm:main")],
    ])


# ─── /admin command ───────────────────────────────────────────────

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа.")
        return
    await message.answer(
        "🛠 <b>Панель администратора LSJ Love</b>\n\nВыберите раздел:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


# ─── Main menu callback ───────────────────────────────────────────

@admin_router.callback_query(F.data == "adm:main")
async def cb_admin_main(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    await cq.message.edit_text(
        "🛠 <b>Панель администратора LSJ Love</b>\n\nВыберите раздел:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await cq.answer()


# ─── Stats ───────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "adm:stats")
async def cb_stats(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    await cq.answer("Загружаю...")
    data = await fetch("/admin/stats")
    if not data:
        await cq.message.edit_text("❌ Ошибка загрузки статистики.", reply_markup=back_to_admin_kb())
        return
    text = (
        "📊 <b>Статистика LSJ Love</b>\n\n"
        f"👤 Всего пользователей: <b>{data.get('total', 0)}</b>\n"
        f"✅ Активных: <b>{data.get('active', 0)}</b>\n"
        f"🚫 Забанено: <b>{data.get('banned', 0)}</b>\n"
        f"🆕 Зарегистрировались сегодня: <b>{data.get('new_today', 0)}</b>\n"
        f"🟢 Онлайн (5 мин): <b>{data.get('online_5min', 0)}</b>\n\n"
        f"⭐ Premium: <b>{data.get('premium', 0)}</b>\n"
        f"💎 VIP: <b>{data.get('vip', 0)}</b>\n\n"
        f"👨 Мужчин: <b>{data.get('male', 0)}</b>\n"
        f"👩 Женщин: <b>{data.get('female', 0)}</b>\n"
    )
    await cq.message.edit_text(text, reply_markup=back_to_admin_kb(), parse_mode="HTML")


# ─── Users list ──────────────────────────────────────────────────

@admin_router.callback_query(F.data.startswith("adm:users:"))
async def cb_users_list(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    page = int(cq.data.split(":")[-1])
    await cq.answer("Загружаю...")
    data = await fetch("/admin/users/list", page=page, limit=10)
    if not data:
        await cq.message.edit_text("❌ Ошибка.", reply_markup=back_to_admin_kb())
        return
    items = data.get("items", [])
    total = data.get("total", 0)
    pages = max(1, (total + 9) // 10)

    lines = [f"👥 <b>Пользователи</b> (стр. {page}/{pages}, всего {total})\n"]
    for u in items:
        name = u.get("name", "?")
        uid = u.get("telegram_id", "?")
        uname = f"@{u['username']}" if u.get("username") else "—"
        gender_icon = "👩" if str(u.get("gender", "")).lower() in ("female", "женский") else "👨"
        banned = " 🚫" if u.get("is_banned") else ""
        pt = fmt_premium(u.get("premium_type"), u.get("premium_until"))
        lines.append(f"{gender_icon} <b>{name}</b> | {uname} | {uid}{banned}\n  └ {pt}")

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"adm:users:{page-1}"))
    if page < pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"adm:users:{page+1}"))

    kb_rows = []
    for u in items:
        uid = u.get("telegram_id")
        name = u.get("name", "?")
        kb_rows.append([InlineKeyboardButton(text=f"🔍 {name} ({uid})", callback_data=f"adm:user:{uid}")])
    if nav_buttons:
        kb_rows.append(nav_buttons)
    kb_rows.append([InlineKeyboardButton(text="◀️ Меню", callback_data="adm:main")])

    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="HTML",
    )


# ─── User detail ─────────────────────────────────────────────────

@admin_router.callback_query(F.data.startswith("adm:user:"))
async def cb_user_detail(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    uid = int(cq.data.split(":")[-1])
    await cq.answer("Загружаю...")
    data = await fetch(f"/admin/users/{uid}")
    if not data:
        await cq.message.edit_text("❌ Пользователь не найден.", reply_markup=back_to_admin_kb())
        return
    pt = fmt_premium(data.get("premium_type"), data.get("premium_until"))
    gender_icon = "👩" if str(data.get("gender", "")).lower() in ("female", "женский") else "👨"
    banned_str = " 🚫 ЗАБАНЕН" if data.get("is_banned") else ""
    text = (
        f"{gender_icon} <b>{data.get('name', '?')}</b>{banned_str}\n"
        f"ID: <code>{data.get('telegram_id')}</code>\n"
        f"Username: @{data.get('username') or '—'}\n"
        f"Возраст: {data.get('age', '—')} | Город: {data.get('city', '—')}\n"
        f"Подписка: {pt}\n"
        f"Баланс реф.: {data.get('referral_balance', 0):.1f} ₽\n"
        f"Суперлайки: {data.get('superlike_credits', 0)}\n"
        f"Фото: {len(data.get('photos', []))} шт.\n"
        f"Последний визит: {(data.get('last_seen') or '—')[:19]}\n"
        f"Зарегистрирован: {(data.get('created_at') or '—')[:19]}\n\n"
        f"📝 О себе: {(data.get('about') or '—')[:200]}"
    )
    await cq.message.edit_text(
        text,
        reply_markup=user_detail_kb(uid, bool(data.get("is_banned"))),
        parse_mode="HTML",
    )


# ─── Grant premium ───────────────────────────────────────────────

@admin_router.callback_query(F.data.startswith("adm:prem:"))
async def cb_set_premium(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    _, _, uid_str, ptype, days_str = cq.data.split(":")
    uid = int(uid_str)
    days = int(days_str)
    pt = None if ptype == "none" else ptype
    result = await fetch(
        f"/admin/users/{uid}/set-premium",
        method="POST",
        premium_type=pt,
        days=days,
    )
    if result and result.get("ok"):
        label = {"premium": "Premium", "vip": "VIP"}.get(pt, "снята")
        await cq.answer(f"✅ Подписка {label} {'выдана' if pt else 'снята'}!", show_alert=True)
    else:
        await cq.answer("❌ Ошибка!", show_alert=True)
    # Refresh user detail
    data = await fetch(f"/admin/users/{uid}")
    if data:
        pt2 = fmt_premium(data.get("premium_type"), data.get("premium_until"))
        gender_icon = "👩" if str(data.get("gender", "")).lower() in ("female", "женский") else "👨"
        banned_str = " 🚫 ЗАБАНЕН" if data.get("is_banned") else ""
        text = (
            f"{gender_icon} <b>{data.get('name', '?')}</b>{banned_str}\n"
            f"ID: <code>{data.get('telegram_id')}</code>\n"
            f"Подписка: {pt2}\n"
        )
        await cq.message.edit_text(
            text,
            reply_markup=user_detail_kb(uid, bool(data.get("is_banned"))),
            parse_mode="HTML",
        )


# ─── Ban / Unban ─────────────────────────────────────────────────

@admin_router.callback_query(F.data.startswith("adm:ban:"))
async def cb_ban(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    uid = int(cq.data.split(":")[-1])
    result = await fetch(f"/admin/users/{uid}/ban", method="POST")
    if result and result.get("ok"):
        await cq.answer("🚫 Пользователь забанен!", show_alert=True)
    else:
        await cq.answer("❌ Ошибка!", show_alert=True)
    data = await fetch(f"/admin/users/{uid}")
    if data:
        gender_icon = "👩" if str(data.get("gender", "")).lower() in ("female", "женский") else "👨"
        await cq.message.edit_text(
            f"{gender_icon} <b>{data.get('name', '?')}</b> 🚫 ЗАБАНЕН",
            reply_markup=user_detail_kb(uid, True),
            parse_mode="HTML",
        )


@admin_router.callback_query(F.data.startswith("adm:unban:"))
async def cb_unban(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    uid = int(cq.data.split(":")[-1])
    result = await fetch(f"/admin/users/{uid}/unban", method="POST")
    if result and result.get("ok"):
        await cq.answer("✅ Пользователь разбанен!", show_alert=True)
    else:
        await cq.answer("❌ Ошибка!", show_alert=True)
    data = await fetch(f"/admin/users/{uid}")
    if data:
        gender_icon = "👩" if str(data.get("gender", "")).lower() in ("female", "женский") else "👨"
        await cq.message.edit_text(
            f"{gender_icon} <b>{data.get('name', '?')}</b> ✅ Разбанен",
            reply_markup=user_detail_kb(uid, False),
            parse_mode="HTML",
        )


# ─── Delete user ─────────────────────────────────────────────────

@admin_router.callback_query(F.data.startswith("adm:del:"))
async def cb_delete_user(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    uid = int(cq.data.split(":")[-1])
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"adm:delconf:{uid}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"adm:user:{uid}")],
    ])
    await cq.message.edit_text(
        f"⚠️ Удалить анкету пользователя <code>{uid}</code>? Это действие необратимо.",
        reply_markup=confirm_kb,
        parse_mode="HTML",
    )
    await cq.answer()


@admin_router.callback_query(F.data.startswith("adm:delconf:"))
async def cb_delete_confirm(cq: CallbackQuery):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    uid = int(cq.data.split(":")[-1])
    result = await fetch(f"/admin/users/{uid}", method="DELETE")
    if result and result.get("ok"):
        await cq.answer("🗑 Анкета удалена!", show_alert=True)
        await cq.message.edit_text("🗑 Анкета удалена.", reply_markup=back_to_admin_kb())
    else:
        await cq.answer("❌ Ошибка!", show_alert=True)


# ─── Search prompt ───────────────────────────────────────────────

@admin_router.callback_query(F.data == "adm:search")
async def cb_search_prompt(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    await state.set_state(AdminStates.waiting_search)
    await cq.message.edit_text(
        "🔍 Введите <b>ID</b>, имя или username пользователя:",
        reply_markup=back_to_admin_kb(),
        parse_mode="HTML",
    )
    await cq.answer()


@admin_router.message(AdminStates.waiting_search)
async def msg_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    search = message.text.strip()
    data = await fetch("/admin/users/list", page=1, limit=5, search=search)
    if not data or not data.get("items"):
        await message.answer("❌ Пользователи не найдены.", reply_markup=back_to_admin_kb())
        return
    items = data["items"]
    kb_rows = []
    for u in items:
        uid = u.get("telegram_id")
        name = u.get("name", "?")
        kb_rows.append([InlineKeyboardButton(text=f"🔍 {name} ({uid})", callback_data=f"adm:user:{uid}")])
    kb_rows.append([InlineKeyboardButton(text="◀️ Меню", callback_data="adm:main")])
    lines = [f"🔍 Найдено: {data['total']}\n"]
    for u in items:
        name = u.get("name", "?")
        uid = u.get("telegram_id", "?")
        uname = f"@{u['username']}" if u.get("username") else "—"
        lines.append(f"• <b>{name}</b> | {uname} | <code>{uid}</code>")
    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="HTML",
    )


# ─── Ban / Unban by ID prompt ────────────────────────────────────

@admin_router.callback_query(F.data == "adm:ban_prompt")
async def cb_ban_prompt(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    await state.set_state(AdminStates.waiting_ban_id)
    await state.update_data(action="ban")
    await cq.message.edit_text(
        "🚫 Введите <b>Telegram ID</b> пользователя для бана:",
        reply_markup=back_to_admin_kb(),
        parse_mode="HTML",
    )
    await cq.answer()


@admin_router.callback_query(F.data == "adm:unban_prompt")
async def cb_unban_prompt(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id):
        await cq.answer("⛔")
        return
    await state.set_state(AdminStates.waiting_ban_id)
    await state.update_data(action="unban")
    await cq.message.edit_text(
        "✅ Введите <b>Telegram ID</b> пользователя для разбана:",
        reply_markup=back_to_admin_kb(),
        parse_mode="HTML",
    )
    await cq.answer()


@admin_router.message(AdminStates.waiting_ban_id)
async def msg_ban_by_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    action = data.get("action", "ban")
    await state.clear()
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный ID.", reply_markup=back_to_admin_kb())
        return
    endpoint = f"/admin/users/{uid}/ban" if action == "ban" else f"/admin/users/{uid}/unban"
    result = await fetch(endpoint, method="POST")
    if result and result.get("ok"):
        label = "забанен 🚫" if action == "ban" else "разбанен ✅"
        await message.answer(f"Пользователь <code>{uid}</code> {label}", parse_mode="HTML", reply_markup=back_to_admin_kb())
    else:
        await message.answer("❌ Ошибка. Проверьте ID.", reply_markup=back_to_admin_kb())
