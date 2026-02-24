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
    gender = GENDER_RU.get(str(user.gender), str(user.gender) if user.gender else "—")
    looking = LOOKING_FOR_RU.get(str(user.looking_for), str(user.looking_for) if user.looking_for else "—")

    profile_text = (
        f"<b>✨ Твоя анкета:</b>\n\n"
        f"<b>👋 Имя:</b> {user.name} | @{user.username}\n"
        f"<b>🎂 Возраст:</b> {user.age}\n"
        f"<b>🌆 Город:</b> {user.city}\n"
        f"<b>👫 Пол:</b> {gender}\n"
        f"<b>🔍 Ищу:</b> {looking}\n"
    )

    if user.about:
        profile_text += f"<b>✍️ О себе:</b>\n<i>{user.about}</i>"

    return profile_text


def profile_text_message(user: UserEntity) -> str:
    gender = GENDER_RU.get(str(user.gender), str(user.gender) if user.gender else "—")

    profile_text = (
        f"\n<b>👋 Имя:</b> {user.name}\n"
        f"<b>🎂 Возраст:</b> {user.age}\n"
        f"<b>🌆 Город:</b> {user.city}\n"
        f"<b>👫 Пол:</b> {gender}\n"
    )

    if user.about:
        profile_text += f"<b>✍️ О пользователе:</b>\n<i>{user.about}</i>"

    return profile_text


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
        "├ 🚀 Буст профиля ×3 в неделю\n"
        "└ 🏆 Твоя анкета показывается выше\n\n"

        "💌 <b>Пак Icebreaker ×5</b> — разовая покупка\n"
        "└ Без подписки, используй когда удобно\n\n"

        "Оплата: ⭐ Stars · 📱 СБП · ₿ USDT"
    )


def daily_streak_message(days: int) -> str:
    return (
        f"🔥 <b>Ты в приложении {days} {'день' if days == 1 else 'дней' if days < 5 else 'дней'} подряд!</b>\n"
        f"Продолжай — и получи бонусные лайки!"
    )
