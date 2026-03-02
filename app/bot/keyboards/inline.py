from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from punq import Container

from app.logic.init import init_container
from app.settings.config import Config


container: Container = init_container()
config: Config = container.resolve(Config)


def profile_inline_kb(
    user_id,
    liked_by,
    is_vip: bool = False,
    boosts_left: int = 0,
    is_active: bool = True,
    gender: str = "",
    allow_girls_write_first: bool = False,
):
    builder = InlineKeyboardBuilder()
    if liked_by:
        builder.row(
            InlineKeyboardButton(
                text="💌 Тебя лайкнули!",
                callback_data="see_who_liked",
            ),
        )
    builder.row(
        InlineKeyboardButton(
            text="💗 Смотреть анкеты",
            web_app=WebAppInfo(url=f"{config.front_end_url}/users/{user_id}"),
        ),
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Редактировать профиль", callback_data="profile_edit"),
    )
    if is_vip and boosts_left > 0:
        builder.row(
            InlineKeyboardButton(
                text=f"🚀 Буст профиля ({boosts_left} ост.)",
                callback_data="boost_profile",
            ),
        )
    builder.row(
        InlineKeyboardButton(
            text="👀 Показать анкету" if not is_active else "👻 Скрыть анкету",
            callback_data="toggle_visibility",
        ),
    )
    # Тоггл для мужчин — девушки пишут первыми
    if str(gender).lower() in ("male", "мужской"):
        icon = "✅" if allow_girls_write_first else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{icon} Девушки пишут первыми",
                callback_data="toggle_girls_write_first",
            ),
        )
    builder.row(
        InlineKeyboardButton(text="🔗 Реферальная программа", callback_data="referral_info"),
    )
    builder.row(
        InlineKeyboardButton(text="⭐ Premium", callback_data="premium_info"),
    )
    return builder.as_markup()


def profile_edit_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="1️⃣ Данные",
                    callback_data="profile_page",
                    one_time=True,
                ),
                InlineKeyboardButton(
                    text="2️⃣ Анкета",
                    callback_data="form",
                    one_time=True,
                ),
                InlineKeyboardButton(
                    text="3️⃣ Фото",
                    callback_data="photo_edit",
                    one_time=True,
                ),
                InlineKeyboardButton(
                    text="4️⃣ О себе",
                    callback_data="about_edit",
                    one_time=True,
                ),
            ],
        ],
    )
    return keyboard


def re_registration_confirm_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да ✅",
                    callback_data="form_confirm",
                    one_time=True,
                ),
                InlineKeyboardButton(
                    text="Нет ❌",
                    callback_data="profile_edit",
                    one_time=True,
                ),
            ],
        ],
    )
    return keyboard


def photo_confirm_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да ✅",
                    callback_data="photo_confirm",
                    one_time=True,
                ),
                InlineKeyboardButton(
                    text="Нет ❌",
                    callback_data="profile_edit",
                    one_time=True,
                ),
            ],
        ],
    )
    return keyboard


def about_confirm_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да ✅",
                    callback_data="about_confirm",
                    one_time=True,
                ),
                InlineKeyboardButton(
                    text="Нет ❌",
                    callback_data="profile_edit",
                    one_time=True,
                ),
            ],
        ],
    )
    return keyboard


def liked_by_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да ✅",
                    callback_data="see_who_liked",
                ),
                InlineKeyboardButton(
                    text="Нет ❌",
                    callback_data="profile_page",
                ),
            ],
        ],
    )
    return keyboard


def icebreaker_keyboard(sender_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❤️ Ответить",
                    callback_data=f"icebreaker_reply_{sender_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Пропустить",
                    callback_data=f"icebreaker_skip_{sender_id}",
                ),
            ],
        ]
    )


def match_keyboard(username: str | None = None, to_user_id: int | None = None, matched_user_id: int | None = None):
    buttons = []
    if username and username.strip():
        buttons.append([
            InlineKeyboardButton(
                text="💬 Написать",
                url=f"https://t.me/{username.strip()}",
            ),
        ])
    # Кнопка просмотра профиля в Mini App
    if to_user_id and matched_user_id:
        buttons.append([
            InlineKeyboardButton(
                text="👤 Посмотреть профиль",
                web_app=WebAppInfo(
                    url=f"{config.front_end_url}/users/{to_user_id}/view-profile/{matched_user_id}",
                ),
            ),
        ])
    buttons.append([
        InlineKeyboardButton(
            text="💗 Смотреть анкеты",
            callback_data="profile_page",
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def like_dislike_keyboard(user_id: int):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❤️ Нравится",
                    callback_data=f"like_{user_id}",
                    one_time=True,
                ),
                InlineKeyboardButton(
                    text="👎 Пропустить",
                    callback_data=f"dislike_{user_id}",
                    one_time=True,
                ),
            ],
        ],
    )
    return keyboard


def premium_keyboard(stars_premium: int, stars_vip: int):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⭐ Premium — {stars_premium} Stars/мес",
                    callback_data="buy_premium",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"💎 VIP — {stars_vip} Stars/мес",
                    callback_data="buy_vip",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="profile_page",
                ),
            ],
        ],
    )
    return keyboard


def superlike_keyboard(stars_superlike: int):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⭐ Суперлайк — {stars_superlike} Stars",
                    callback_data="buy_superlike",
                ),
            ],
        ],
    )
    return keyboard
