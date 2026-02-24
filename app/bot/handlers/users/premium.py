"""
Premium handler: Telegram Stars + Platega (СБП, Крипто).
"""
import logging
import aiohttp
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from punq import Container

from app.bot.utils.constants import premium_info_message
from app.logic.init import init_container
from app.logic.services.base import BaseUsersService
from app.settings.config import Config


logger = logging.getLogger(__name__)
premium_router = Router(name="Premium router")

BACKEND_URL = "https://lsjlove.duckdns.org"


def payment_method_keyboard(
    product: str,
    config: Config,
    usdt_per_rub: float | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура выбора способа оплаты (СБП и Крипто)."""
    prices = {
        "premium":   int(config.platega_premium_price),
        "vip":       int(config.platega_vip_price),
        "superlike": int(config.platega_superlike_price),
    }
    stars = {
        "premium":   config.stars_premium_monthly,
        "vip":       config.stars_vip_monthly,
        "superlike": config.stars_superlike,
    }
    rub = prices.get(product, 0)
    st  = stars.get(product, 0)
    usdt_label = rub_to_usdt(rub, usdt_per_rub)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⭐ Telegram Stars — {st} Stars",
                    callback_data=f"stars_{product}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"📱 СБП — {rub} ₽",
                    callback_data=f"platega_{product}_sbp",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"₿ Крипто — {usdt_label}",
                    callback_data=f"platega_{product}_crypto",
                ),
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="premium_info"),
            ],
        ]
    )


def premium_main_keyboard(config: Config) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⭐ Premium — {int(config.platega_premium_price)} ₽ / мес",
                    callback_data="choose_premium",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"💎 VIP — {int(config.platega_vip_price)} ₽ / мес",
                    callback_data="choose_vip",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"💌 Пак Icebreaker ×5 — {config.stars_icebreaker_pack} Stars",
                    callback_data="buy_icebreaker_pack",
                ),
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="profile_page"),
            ],
        ]
    )


async def get_usdt_rate() -> float | None:
    """Получает курс USDT из нашего backend. Возвращает USDT за 1 RUB."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BACKEND_URL}/api/v1/payments/platega/usdt-rate",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                data = await resp.json()
                return data.get("usdt_per_rub")
    except Exception as e:
        logger.warning(f"Failed to get USDT rate: {e}")
        return None


def rub_to_usdt(rub: float, usdt_per_rub: float | None) -> str:
    """Конвертирует рубли в USDT строку. Например: '3.89 USDT'"""
    if not usdt_per_rub or usdt_per_rub <= 0:
        return "≈ ? USDT"
    return f"≈ {rub * usdt_per_rub:.2f} USDT"


async def create_payment_via_backend(
    telegram_id: int,
    product: str,
    method: str,
) -> tuple[str | None, float | None, float | None, str | None]:
    """
    Создаёт платёж через наш Backend API.
    Возвращает (redirect_url, usdt_amount, rub_per_usdt, error_message).
    """
    url = f"{BACKEND_URL}/api/v1/payments/platega/create"
    body = {
        "telegram_id": telegram_id,
        "product": product,
        "method": method,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
                logger.info(f"Backend payment response ({resp.status}): {data}")

                if resp.status != 200:
                    err = data.get("detail", str(data))
                    logger.error(f"Backend error {resp.status}: {err}")
                    return None, None, None, err

                redirect = data.get("redirect_url")
                if not redirect:
                    logger.error(f"No redirect_url in response: {data}")
                    return None, None, None, "Сервис оплаты не вернул ссылку"

                return redirect, data.get("usdt_amount"), data.get("usdt_rate"), None

    except aiohttp.ClientError as e:
        logger.error(f"Network error calling backend: {e}")
        return None, None, None, f"Ошибка сети: {e}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None, None, None, str(e)


# ─── Команда /premium ────────────────────────────────────────────────────────

@premium_router.message(Command("premium"))
async def premium_command(message: Message, container: Container = init_container()):
    config: Config = container.resolve(Config)
    await message.answer(
        text=premium_info_message(),
        parse_mode="HTML",
        reply_markup=premium_main_keyboard(config),
    )


@premium_router.callback_query(lambda c: c.data == "premium_info")
async def premium_info_callback(callback: CallbackQuery, container: Container = init_container()):
    config: Config = container.resolve(Config)
    text = premium_info_message()
    kb = premium_main_keyboard(config)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


# ─── Выбор тарифа → выбор метода оплаты ─────────────────────────────────────

def _plan_text(label: str, stars: int, rub: int) -> str:
    return (
        f"{label}\n\n"
        f"📌 <b>Что входит:</b>\n"
        f"{'❤️ Безлимитные лайки\n👁 Кто тебя лайкнул\n↩️ Откат свайпа\n💫 1 суперлайк/день' if 'Premium' in label else '✅ Всё из Premium\n🤖 AI Icebreaker ×10/день\n🚀 Буст профиля ×3/нед\n🏆 Приоритет в поиске'}\n\n"
        f"💰 <b>Стоимость:</b>\n"
        f"• Telegram Stars: <b>{stars} ⭐</b>\n"
        f"• СБП / Крипто: <b>{rub} ₽</b>\n\n"
        f"Выбери способ оплаты 👇"
    )


@premium_router.callback_query(lambda c: c.data == "choose_premium")
async def choose_premium(callback: CallbackQuery, container: Container = init_container()):
    config: Config = container.resolve(Config)
    usdt_rate = await get_usdt_rate()
    rub = int(config.platega_premium_price)
    usdt_str = rub_to_usdt(rub, usdt_rate)
    text = (
        "⭐ <b>Premium — 1 месяц</b>\n\n"
        f"📌 <b>Что входит:</b>\n"
        f"❤️ Безлимитные лайки\n"
        f"👁 Кто тебя лайкнул\n"
        f"↩️ Откат свайпа\n"
        f"💫 1 суперлайк/день\n\n"
        f"💰 <b>Стоимость:</b>\n"
        f"• Telegram Stars: <b>{config.stars_premium_monthly} ⭐</b>\n"
        f"• СБП: <b>{rub} ₽</b>\n"
        f"• Крипто: <b>{usdt_str}</b>\n\n"
        f"Выбери способ оплаты 👇"
    )
    kb = payment_method_keyboard("premium", config, usdt_rate)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@premium_router.callback_query(lambda c: c.data == "choose_vip")
async def choose_vip(callback: CallbackQuery, container: Container = init_container()):
    config: Config = container.resolve(Config)
    usdt_rate = await get_usdt_rate()
    rub = int(config.platega_vip_price)
    usdt_str = rub_to_usdt(rub, usdt_rate)
    text = (
        "💎 <b>VIP — 1 месяц</b>\n\n"
        f"📌 <b>Что входит:</b>\n"
        f"✅ Всё из Premium\n"
        f"🤖 AI Icebreaker ×10/день\n"
        f"   <i>(ИИ пишет первое сообщение за тебя)</i>\n"
        f"🚀 Буст профиля ×3/нед\n"
        f"🏆 Приоритет в поиске\n\n"
        f"💰 <b>Стоимость:</b>\n"
        f"• Telegram Stars: <b>{config.stars_vip_monthly} ⭐</b>\n"
        f"• СБП: <b>{rub} ₽</b>\n"
        f"• Крипто: <b>{usdt_str}</b>\n\n"
        f"Выбери способ оплаты 👇"
    )
    kb = payment_method_keyboard("vip", config, usdt_rate)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


# ─── Telegram Stars ───────────────────────────────────────────────────────────

@premium_router.callback_query(lambda c: c.data == "stars_premium")
async def stars_premium(callback: CallbackQuery, container: Container = init_container()):
    config: Config = container.resolve(Config)
    await callback.message.answer_invoice(
        title="LSJLove Premium",
        description="Безлимитные лайки, просмотр кто лайкнул, откат свайпа, 1 суперлайк/день",
        payload="premium_monthly",
        currency="XTR",
        prices=[LabeledPrice(label="Premium на месяц", amount=config.stars_premium_monthly)],
    )
    await callback.answer()


@premium_router.callback_query(lambda c: c.data == "stars_vip")
async def stars_vip(callback: CallbackQuery, container: Container = init_container()):
    config: Config = container.resolve(Config)
    await callback.message.answer_invoice(
        title="LSJLove VIP",
        description="AI Icebreaker ×10/день, буст профиля, приоритет в выдаче + всё из Premium",
        payload="vip_monthly",
        currency="XTR",
        prices=[LabeledPrice(label="VIP на месяц", amount=config.stars_vip_monthly)],
    )
    await callback.answer()


@premium_router.callback_query(lambda c: c.data == "buy_icebreaker_pack")
async def buy_icebreaker_pack(callback: CallbackQuery, container: Container = init_container()):
    config: Config = container.resolve(Config)
    text = (
        "💌 <b>Пак AI Icebreaker ×5</b>\n\n"
        "Получи 5 дополнительных попыток отправить первое\n"
        "сообщение с помощью ИИ — без подписки.\n\n"
        "ИИ анализирует фото и профиль, ты выбираешь тему\n"
        "и один из 3 вариантов сообщения.\n\n"
        f"Стоимость: <b>{config.stars_icebreaker_pack} ⭐ Stars</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"⭐ Купить за {config.stars_icebreaker_pack} Stars",
            callback_data="stars_icebreaker_pack",
        )],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="premium_info")],
    ])
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@premium_router.callback_query(lambda c: c.data == "stars_icebreaker_pack")
async def stars_icebreaker_pack(callback: CallbackQuery, container: Container = init_container()):
    config: Config = container.resolve(Config)
    await callback.message.answer_invoice(
        title="AI Icebreaker ×5",
        description="5 дополнительных AI-сообщений: ИИ анализирует фото и профиль, предлагает 3 варианта.",
        payload="icebreaker_pack_5",
        currency="XTR",
        prices=[LabeledPrice(label="Пак Icebreaker ×5", amount=config.stars_icebreaker_pack)],
    )
    await callback.answer()


# ─── Platega (СБП / Крипто) ────────────────────────────────────────────────

@premium_router.callback_query(lambda c: c.data and c.data.startswith("platega_"))
async def platega_payment(callback: CallbackQuery, container: Container = init_container()):
    """Обрабатывает platega_{product}_{method}"""
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer("Ошибка", show_alert=True)
        return

    _, product, method = parts
    product_labels = {"premium": "⭐ Premium", "vip": "💎 VIP", "superlike": "💫 Суперлайк"}

    await callback.answer("⏳ Создаём ссылку...")

    redirect_url, usdt_amount, rub_per_usdt, error = await create_payment_via_backend(
        telegram_id=callback.from_user.id,
        product=product,
        method=method,
    )

    if error or not redirect_url:
        logger.error(f"Payment creation failed: {error}")
        err_text = (
            f"❌ <b>Не удалось создать платёж</b>\n\n"
            f"Попробуй позже или выбери другой способ.\n"
            f"<code>{error or 'нет ссылки'}</code>"
        )
        err_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="premium_info")],
        ])
        try:
            await callback.message.edit_text(err_text, parse_mode="HTML", reply_markup=err_kb)
        except Exception:
            await callback.message.answer(err_text, parse_mode="HTML", reply_markup=err_kb)
        return

    p_label = product_labels.get(product, product)

    if method == "sbp":
        text = (
            f"✅ <b>Платёж создан!</b>\n\n"
            f"Тариф: <b>{p_label}</b>\n"
            f"Способ: <b>📱 СБП</b>\n\n"
            f"<b>Как оплатить:</b>\n"
            f"1. Нажми «Открыть СБП» ниже\n"
            f"2. Выбери свой банк на странице\n"
            f"3. Подтверди перевод в приложении банка"
        )
        btn_text = "📱 Открыть СБП"
    else:
        usdt_line = f"\nСумма: <b>≈ {usdt_amount} USDT</b>" if usdt_amount else ""
        rate_line = f"\nКурс: 1 USDT ≈ {rub_per_usdt} ₽" if rub_per_usdt else ""
        text = (
            f"✅ <b>Платёж создан!</b>\n\n"
            f"Тариф: <b>{p_label}</b>\n"
            f"Способ: <b>₿ Крипто</b>"
            f"{usdt_line}{rate_line}\n\n"
            f"<b>Как оплатить:</b>\n"
            f"1. Нажми «Открыть страницу оплаты»\n"
            f"2. Выбери <b>Валюта → USDT</b>, Сеть → <b>TRC-20</b>\n"
            f"3. Нажми «Перейти к оплате» — получишь адрес кошелька\n"
            f"4. Переведи ровно <b>{usdt_amount} USDT</b> на этот адрес\n"
            f"5. Перевод подтвердится автоматически (~5 мин)\n\n"
            f"⏱ На оплату: <b>1 час</b>"
        )
        btn_text = "₿ Открыть страницу оплаты"

    pay_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, url=redirect_url)],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="premium_info")],
        ]
    )
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=pay_kb)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, parse_mode="HTML", reply_markup=pay_kb)


# ─── Stars: успешная оплата ────────────────────────────────────────────────

@premium_router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@premium_router.message(lambda m: m.successful_payment is not None)
async def successful_payment(message: Message, container: Container = init_container()):
    payment = message.successful_payment
    payload = payment.invoice_payload
    service: BaseUsersService = container.resolve(BaseUsersService)

    if payload == "premium_monthly":
        premium_type, label = "premium", "⭐ Premium"
    elif payload == "vip_monthly":
        premium_type, label = "vip", "💎 VIP"
    elif payload == "icebreaker_pack_5":
        # Добавляем 5 Icebreaker-ов пользователю (сбрасываем счётчик на N назад)
        try:
            current = await service.get_icebreaker_count(telegram_id=message.from_user.id)
            new_count = max(0, current - 5)
            await service.update_user_info_after_reg(
                telegram_id=message.from_user.id,
                data={"icebreaker_used": new_count},
            )
        except Exception as e:
            logger.error(f"Icebreaker pack activation failed: {e}")
        await message.answer(
            "🎉 <b>Пак AI Icebreaker ×5 активирован!</b>\n\n"
            "Открой приложение и свайпай анкеты — "
            "кнопка ✨ AI Icebreaker теперь снова доступна.",
            parse_mode="HTML",
        )
        return
    else:
        await message.answer("✅ Оплата получена!")
        return

    until = datetime.utcnow() + timedelta(days=30)
    try:
        await service.update_user_info_after_reg(
            telegram_id=message.from_user.id,
            data={"premium_type": premium_type, "premium_until": until},
        )
    except Exception as e:
        logger.error(f"Stars premium activation failed: {e}")

    await message.answer(
        f"🎉 <b>Оплата прошла успешно!</b>\n\n"
        f"Активирован <b>LSJLove {label}</b> на 30 дней.\n\n"
        f"Открой приложение и наслаждайся! ✨",
        parse_mode="HTML",
    )
