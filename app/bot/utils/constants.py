from aiogram.types import User

from app.domain.entities.users import UserEntity


GENDER_RU = {
    "Man": "Мужской",
    "Female": "Женский",
    "man": "Мужской",
    "female": "Женский",
}

LOOKING_FOR_RU = {
    "Man": "Мужчину",
    "Female": "Девушку",
    "man": "Мужчину",
    "female": "Девушку",
}


def first_welcome_message(user: User) -> str:
    message: str = (
        f"Добро пожаловать в <b>LSJLove</b> 💕\n\n"
        f"Привет, <b>{user.first_name}</b>! Здесь ты найдёшь свою вторую половинку."
    )
    return message


def second_welcome_message(user: User):
    message: str = (
        f"С возвращением, <b>{user.first_name}</b>! 💫\n\n"
        f"Продолжим заполнение анкеты."
    )
    return message


def user_profile_text_message(user: UserEntity) -> str:
    from datetime import datetime, timezone

    gender = GENDER_RU.get(str(user.gender), str(user.gender) if user.gender else "—")
    looking = LOOKING_FOR_RU.get(str(user.looking_for), str(user.looking_for) if user.looking_for else "—")

    name_line = str(user.name) if user.name else "—"
    age_str = f", {user.age}" if user.age else ""
    username_str = f"  ·  @{user.username}" if user.username else ""

    lines = [
        "✨ <b>LSJLove — Моя анкета</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👤  <b>{name_line}{age_str}</b>{username_str}",
        f"📍  {user.city or '—'}",
        f"🔍  Ищу: {looking}",
        f"👫  Пол: {gender}",
    ]

    if user.about:
        lines.append("")
        lines.append(f"💬  <i>{user.about}</i>")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")

    # Статус подписки
    pt = getattr(user, "premium_type", None)
    until = getattr(user, "premium_until", None)
    now = datetime.now(timezone.utc)

    if pt and until:
        if hasattr(until, "tzinfo") and until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        if until > now:
            days_left = (until - now).days
            if pt == "vip":
                badge = f"💎 VIP  ·  ещё {days_left} д."
            else:
                badge = f"⭐ Premium  ·  ещё {days_left} д."
        else:
            badge = "🔓 Без подписки"
    else:
        badge = "🔓 Без подписки"

    # Суперлайки
    sl_credits = getattr(user, "superlike_credits", 0) or 0
    sl_str = f"  ·  ⭐ Суперлайки: {sl_credits}" if sl_credits > 0 else ""
    lines.append(f"{badge}{sl_str}")

    # Реферальный баланс (только если > 0)
    ref_balance = float(getattr(user, "referral_balance", 0) or 0)
    if ref_balance > 0:
        lines.append(f"💰  Реф. баланс: <b>{ref_balance:.2f} ₽</b>")

    return "\n".join(lines)


def profile_text_message(user: UserEntity) -> str:
    gender = GENDER_RU.get(str(user.gender), str(user.gender) if user.gender else "—")

    name_line = str(user.name) if user.name else "—"
    age_str = f", {user.age}" if user.age else ""

    lines = [
        f"<b>{name_line}{age_str}</b>",
        f"📍  {user.city or '—'}",
        f"👫  {gender}",
    ]
    if user.about:
        lines.append("")
        lines.append(f"💬  <i>{user.about}</i>")

    return "\n".join(lines)


def match_text_message(user: UserEntity) -> str:
    formatted_text = (
        f"<b>Взаимная симпатия!</b> 💕\n"
        f"Начни общение прямо сейчас 👇\n\n"
        f"<b>{user.name}</b> | @{user.username}, {user.age} лет, {user.city}"
    )

    if user.about:
        formatted_text += f"\n<b>✍️ О себе:</b>\n<i>{user.about}</i>"

    return formatted_text


def premium_info_message() -> str:
    return (
        "💎 <b>LSJLove Premium</b>\n\n"
        "Выбери тариф:\n\n"

        "⭐ <b>Premium — 299 ₽ / 500 Stars в месяц</b>\n"
        "├ ❤️ Лайкай всех без ограничений\n"
        "├ 👁 Видишь кто тебя лайкнул\n"
        "├ ↩️ Вернись к тому кого пропустил\n"
        "├ 💫 1 Суперлайк в день\n"
        "└ 🤖 AI Icebreaker ×5/день\n\n"

        "💎 <b>VIP — 799 ₽ / 1500 Stars в месяц</b>\n"
        "├ ✅ Всё из Premium\n"
        "├ 🤖 <b>AI Icebreaker ×10/день</b>\n"
        "│     ИИ анализирует фото и профиль, пишет\n"
        "│     персональное первое сообщение.\n"
        "│     Выбираешь тему — получаешь 3 варианта.\n"
        "├ 🧠 <b>AI Советник диалога — безлимит</b>\n"
        "│     Пришли скрин переписки или опиши ситуацию.\n"
        "│     ИИ даст конкретные варианты что написать.\n"
        "├ 🚀 Буст профиля ×3 в неделю\n"
        "└ 🏆 Твоя анкета показывается выше\n\n"

        "💌 <b>Пак Icebreaker ×5</b> — разовая покупка\n"
        "└ Без подписки, используй когда удобно\n\n"

        "Оплата: ⭐ Stars · 📱 СБП · ₿ USDT\n\n"
        "🔗 <b>Реферальная программа:</b> приглашай друзей — получай 50% с каждой их покупки!"
    )


def daily_streak_message(days: int) -> str:
    return (
        f"🔥 <b>Ты в приложении {days} {'день' if days == 1 else 'дней' if days < 5 else 'дней'} подряд!</b>\n"
        f"Продолжай — и получи бонусные лайки!"
    )
