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


def profile_inline_kb(user_id, liked_by):
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
