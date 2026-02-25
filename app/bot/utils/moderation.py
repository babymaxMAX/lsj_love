"""
Модерация контента: проверка фото на наличие 18+ материалов.
Использует OpenAI GPT-4o-mini Vision.
"""
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Максимальный размер изображения для проверки (в байтах) — 4 МБ
_MAX_CHECK_SIZE = 4 * 1024 * 1024


async def check_image_safe(image_bytes: bytes, api_key: Optional[str]) -> tuple[bool, str]:
    """
    Проверяет изображение на NSFW/18+ контент через OpenAI GPT-4o-mini Vision.

    Returns:
        (True, "ok")           — изображение безопасно, можно сохранять
        (False, "причина")     — изображение содержит неприемлемый контент
    """
    if not api_key:
        # OpenAI не настроен — пропускаем проверку
        logger.warning("NSFW check skipped: OPENAI_API_KEY not configured")
        return True, "ok"

    if not image_bytes:
        return False, "Пустой файл"

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)

        # Если изображение слишком большое — сжимаем перед отправкой
        check_bytes = image_bytes
        if len(check_bytes) > _MAX_CHECK_SIZE:
            # Берём первые 4 МБ — для грубой проверки достаточно
            check_bytes = check_bytes[:_MAX_CHECK_SIZE]

        b64 = base64.b64encode(check_bytes).decode("utf-8")

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "low",
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Ты — строгий модератор контента для сайта знакомств.\n"
                                "Проверь изображение. Ответь ТОЛЬКО одним словом:\n\n"
                                "SAFE — фото подходит для сайта знакомств: портрет, лицо, "
                                "человек в одежде, пейзаж, животные, еда и т.п.\n\n"
                                "UNSAFE — фото содержит ЛЮБОЕ из:\n"
                                "- обнажённые половые органы (мужские или женские)\n"
                                "- обнажённая грудь женщины\n"
                                "- откровенные сексуальные позы\n"
                                "- порнографический или эротический контент\n"
                                "- полная или частичная нагота в сексуальном контексте\n\n"
                                "При малейшем сомнении — пиши UNSAFE.\n"
                                "Ответ: только одно слово SAFE или UNSAFE."
                            ),
                        },
                    ],
                }
            ],
            max_tokens=10,
            temperature=0,
        )

        result = response.choices[0].message.content.strip().upper()
        logger.info(f"NSFW moderation result: '{result}' (bytes={len(image_bytes)})")

        if "UNSAFE" in result:
            return False, "Фото содержит недопустимый контент (18+). Загрузи другое фото."

        return True, "ok"

    except Exception as e:
        logger.warning(f"NSFW check error: {e}")
        # При ошибке API — разрешаем (не блокируем пользователей из-за сбоя API)
        return True, "ok"


def is_video_mime(media_type: str) -> bool:
    """Возвращает True если MIME-тип является видео."""
    return media_type.startswith("video/")
