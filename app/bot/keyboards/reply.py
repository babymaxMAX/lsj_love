from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


def user_name_keyboard(text: str | list) -> ReplyKeyboardMarkup:
    if isinstance(text, str):
        text = [text]

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=txt) for txt in text],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


gender_select_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👨 Мужской"),
            KeyboardButton(text="👧 Женский"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="👇 Нажми кнопку",
    selective=True,
)

about_skip_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🪪 Пропустить"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="👇 Или напиши о себе",
    selective=True,
)

remove_keyboard = ReplyKeyboardRemove()
