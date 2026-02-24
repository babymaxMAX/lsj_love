import logging
import re

import aiohttp
from aiogram.types import BufferedInputFile

# Все импорты из app.bot.* делаются ЛЕНИВО внутри функций,
# чтобы избежать циклического импорта через bot.main

logger = logging.getLogger(__name__)

# S3 ключ выглядит как: {digits}_{digit}.{ext}
_S3_KEY_RE = re.compile(r"^\d+_\d+\.\w+$")


def _is_s3_key(photo: str) -> bool:
    """Определяет, является ли photo S3-ключом (не file_id и не URL)."""
    if not photo:
        return False
    if photo.startswith("http"):
        return False
    return bool(_S3_KEY_RE.match(photo))


async def _resolve_photo(photo: str, user_id: int | None = None) -> str | bytes | None:
    """
    Возвращает корректное значение для send_photo:
    - HTTP URL (для Telegram file_id или http-ссылки)
    - bytes (если пришёл S3 ключ — скачиваем через наш API и возвращаем байты)
    - None если фото недоступно
    """
    if not photo:
        return None
    if not _is_s3_key(photo):
        return photo  # Telegram file_id или http — отдаём как есть

    # S3 ключ: скачиваем через наш публичный API
    from app.logic.init import init_container
    from app.settings.config import Config
    try:
        container = init_container()
        config: Config = container.resolve(Config)
        api_base = config.front_end_url.rstrip("/")
        # Извлекаем user_id из ключа, если не передан
        if user_id is None:
            user_id = int(photo.split("_")[0])
        # Индекс из ключа (7741189969_0.jpg → 0)
        idx = int(photo.split("_")[1].split(".")[0])
        url = f"{api_base}/api/v1/users/{user_id}/photo/{idx}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status == 200:
                    return await resp.read()
    except Exception as e:
        logger.warning(f"_resolve_photo failed for key={photo}: {e}")
    return None


async def _send_photo_or_text(chat_id: int, photo_raw, text: str, reply_markup, user_id: int | None = None):
    """Отправляет фото с caption или текст, правильно обрабатывая S3-ключи."""
    from app.bot.main import bot  # ленивый импорт во избежание цикла
    if photo_raw:
        resolved = await _resolve_photo(photo_raw, user_id)
        if resolved:
            try:
                if isinstance(resolved, bytes):
                    photo_input = BufferedInputFile(resolved, filename="photo.jpg")
                else:
                    photo_input = resolved
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_input,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
                return
            except Exception as e:
                logger.warning(f"send_photo failed: {e}")

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode="HTML",
    )


async def send_liked_message(to_user_id: int):
    from app.bot.main import bot  # ленивый импорт
    from app.bot.keyboards.inline import liked_by_keyboard
    try:
        await bot.send_message(
            to_user_id,
            text="<b>Кто-то поставил тебе лайк 💗</b>\nХочешь узнать кто?",
            reply_markup=liked_by_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        pass


async def send_icebreaker_message(target_id: int, message: str, sender):
    """Отправляет icebreaker-сообщение целевому пользователю через бот."""
    from app.bot.keyboards.inline import icebreaker_keyboard
    try:
        sender_name = str(getattr(sender, "name", "Кто-то") or "Кто-то")
        sender_photo = getattr(sender, "photo", None)
        sender_id = getattr(sender, "telegram_id", None)

        text = (
            f"💌 <b>{sender_name}</b> хочет познакомиться и написал(а) тебе:\n\n"
            f"<i>«{message}»</i>\n\n"
            f"Хочешь ответить?"
        )
        kb = icebreaker_keyboard(sender_id=sender_id)
        await _send_photo_or_text(target_id, sender_photo, text, kb, user_id=sender_id)
    except Exception as e:
        logger.error(f"send_icebreaker_message failed: {e}")


async def send_superlike_message(target_id: int, sender):
    """Отправляет уведомление о суперлайке."""
    from app.bot.keyboards.inline import liked_by_keyboard
    try:
        sender_name = str(getattr(sender, "name", "Кто-то") or "Кто-то")
        sender_photo = getattr(sender, "photo", None)
        sender_id = getattr(sender, "telegram_id", None)

        text = (
            f"⭐ <b>{sender_name} отправил(а) тебе Суперлайк!</b>\n\n"
            f"Ты очень понравился(ась) — он(а) специально выделил(а) тебя.\n"
            f"Ответить взаимностью?"
        )
        kb = liked_by_keyboard()
        await _send_photo_or_text(target_id, sender_photo, text, kb, user_id=sender_id)
    except Exception as e:
        logger.error(f"send_superlike_message failed: {e}")


async def send_photo_liked_notification(owner_id: int, liker_name: str, photo_idx: int, owner_is_premium: bool):
    """Уведомляет владельца фото о лайке. Если Premium — показывает имя, иначе анонимно."""
    from app.bot.main import bot
    try:
        if owner_is_premium:
            text = (
                f"❤️ <b>{liker_name}</b> лайкнул(а) твоё фото {photo_idx + 1}!\n\n"
                f"Загляни в профиль — возможно, стоит ответить взаимностью 😊"
            )
        else:
            text = (
                f"❤️ <b>Кто-то лайкнул твоё фото!</b>\n\n"
                f"Получи подписку <b>Premium</b>, чтобы узнать кто."
            )
        await bot.send_message(chat_id=owner_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"send_photo_liked_notification failed: {e}")


async def send_photo_commented_notification(owner_id: int, commenter_name: str, comment_text: str, photo_idx: int, owner_is_premium: bool):
    """Уведомляет владельца фото о новом комментарии."""
    from app.bot.main import bot
    try:
        short_comment = comment_text[:80] + ("..." if len(comment_text) > 80 else "")
        if owner_is_premium:
            text = (
                f"💬 <b>{commenter_name}</b> прокомментировал(а) твоё фото {photo_idx + 1}:\n\n"
                f"<i>«{short_comment}»</i>"
            )
        else:
            text = (
                f"💬 <b>Новый комментарий к твоему фото!</b>\n\n"
                f"<i>«{short_comment}»</i>\n\n"
                f"Получи <b>Premium</b>, чтобы узнать кто написал."
            )
        await bot.send_message(chat_id=owner_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"send_photo_commented_notification failed: {e}")


async def send_match_message(to_user_id: int, matched_user, recipient_id: int | None = None):
    """
    to_user_id — кому отправляем уведомление
    matched_user — пользователь, с которым произошёл матч (чьё фото/имя показываем)
    recipient_id — telegram_id получателя (для кнопки "Посмотреть профиль")
    """
    from app.bot.keyboards.inline import match_keyboard
    try:
        name = str(getattr(matched_user, "name", "") or "")
        username = getattr(matched_user, "username", None) or None
        age = str(getattr(matched_user, "age", "") or "")
        city = str(getattr(matched_user, "city", "") or "")
        matched_id = getattr(matched_user, "telegram_id", None)
        if username == "":
            username = None

        text = (
            f"💕 <b>Взаимная симпатия!</b>\n\n"
            f"<b>{name}</b>{(', ' + age) if age else ''}{(', ' + city) if city else ''}\n"
        )
        if username and username.strip():
            text += f"👉 <a href='https://t.me/{username}'>Написать {name}</a>"

        kb = match_keyboard(
            username=username,
            to_user_id=recipient_id or to_user_id,
            matched_user_id=matched_id,
        )

        photo = getattr(matched_user, "photo", None)
        await _send_photo_or_text(to_user_id, photo, text, kb, user_id=matched_id)
    except Exception as e:
        logger.error(f"send_match_message failed: {e}")
