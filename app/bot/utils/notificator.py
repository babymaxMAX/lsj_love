from app.bot.keyboards.inline import liked_by_keyboard, match_keyboard, icebreaker_keyboard
from app.bot.main import bot


async def send_liked_message(to_user_id: int):
    try:
        await bot.send_message(
            to_user_id,
            text="<b>Кто-то поставил тебе лайк 💗</b>\nХочешь узнать кто?",
            reply_markup=liked_by_keyboard(),
        )
    except Exception:
        pass


async def send_icebreaker_message(target_id: int, message: str, sender):
    """Отправляет icebreaker-сообщение целевому пользователю через бот."""
    try:
        sender_name = getattr(sender, "name", "Кто-то")
        sender_photo = getattr(sender, "photo", None)

        text = (
            f"💌 <b>{sender_name}</b> хочет познакомиться и написал(а) тебе:\n\n"
            f"<i>«{message}»</i>\n\n"
            f"Хочешь ответить?"
        )
        kb = icebreaker_keyboard(sender_id=sender.telegram_id)

        if sender_photo:
            try:
                await bot.send_photo(
                    chat_id=target_id,
                    photo=sender_photo,
                    caption=text,
                    reply_markup=kb,
                )
                return
            except Exception:
                pass

        await bot.send_message(
            chat_id=target_id,
            text=text,
            reply_markup=kb,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"send_icebreaker_message failed: {e}")


async def send_match_message(to_user_id: int, matched_user):
    try:
        name = getattr(matched_user, "name", "")
        username = getattr(matched_user, "username", None)
        age = getattr(matched_user, "age", "")
        city = getattr(matched_user, "city", "")

        text = (
            f"💕 <b>Взаимная симпатия!</b>\n\n"
            f"<b>{name}</b>, {age}, {city}\n"
        )
        if username:
            text += f"👉 <a href='https://t.me/{username}'>Написать {name}</a>"

        photo = getattr(matched_user, "photo", None)
        if photo:
            try:
                await bot.send_photo(
                    chat_id=to_user_id,
                    photo=photo,
                    caption=text,
                    reply_markup=match_keyboard(username),
                )
                return
            except Exception:
                pass

        await bot.send_message(
            chat_id=to_user_id,
            text=text,
            reply_markup=match_keyboard(username),
        )
    except Exception:
        pass
