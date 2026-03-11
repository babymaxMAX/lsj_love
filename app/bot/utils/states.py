from aiogram.fsm.state import (
    State,
    StatesGroup,
)


class UserForm(StatesGroup):
    name = State()
    age = State()
    gender = State()
    city = State()
    looking_for = State()
    about = State()
    photo = State()


class UserAboutUpdate(StatesGroup):
    about = State()


class UserPhotoUpdate(StatesGroup):
    photo = State()


class MessageCompose(StatesGroup):
    """FSM для кнопки Message на карточке (отправка первого сообщения = лайк)."""
    text = State()


class ReportForm(StatesGroup):
    """FSM для репорта профиля."""
    category = State()
    text = State()
