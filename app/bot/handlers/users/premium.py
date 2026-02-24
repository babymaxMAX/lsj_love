"""
Premium handler: поддерживает Telegram Stars и Platega (карта, СБП, крипто).
"""
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


premium_router = Router(name="Premium router")

PLATEGA_BASE_URL = "https://app.platega.io"


def payment_method_keyboard(product: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора способа оплаты."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ Telegram Stars",
                    callback_data=f"stars_{product}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💳 Карта (RUB)",
                    callback_data=f"platega_{product}_card",
                ),
                InlineKeyboardButton(
                    text="📱 СБП",
                    callback_data=f"platega_{product}_sbp",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="₿ Крипто",
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
                    text=f"⭐ Premium — {config.stars_premium_monthly} Stars / {int(config.platega_premium_price)}₽",
                    callback_data="choose_premium",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"💎 VIP — {config.stars_vip_monthly} Stars / {int(config.platega_vip_price)}₽",
                    callback_data="choose_vip",
                ),
            ],
        ]
    )


async def create_platega_link(
    config: Config,
    telegram_id: int,
    product: str,
    method: str,
) -> str | None:
    """Создаёт платёж в Platega и возвращает payment URL."""
    method_map = {"card": 10, "sbp": 2, "crypto": 13}
    prices = {
        "premium": config.platega_premium_price,
        "vip": config.platega_vip_price,
        "superlike": config.platega_superlike_price,
    }
    names = {
        "premium": "Premium подписка (1 месяц)",
        "vip": "VIP подписка (1 месяц)",
        "superlike": "Суперлайк LSJLove",
    }

    body = {
        "paymentMethod": method_map[method],
        "paymentDetails": {"amount": prices[product], "currency": "RUB"},
        "description": names[product],
        "return": f"https://lsjlove.duckdns.org/users/{telegram_id}/premium?status=success",
        "failedUrl": f"https://lsjlove.duckdns.org/users/{telegram_id}/premium?status=failed",
        "payload": f"{telegram_id}:{product}",
    }
    headers = {
        "X-MerchantId": config.platega_merchant_id,
        "X-Secret": config.platega_secret,
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{PLATEGA_BASE_URL}/api/transaction/create",
                json=body,
                headers=headers,
            ) as resp:
                data = await resp.json()
                return data.get("paymentUrl")
    except Exception:
        return None


# ─── /premium команда ────────────────────────────────────────────────────────

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
    await callback.message.edit_text(
        text=premium_info_message(),
        parse_mode="HTML",
        reply_markup=premium_main_keyboard(config),
    )
    await callback.answer()


# ─── Выбор продукта → показ способов оплаты ──────────────────────────────────

@premium_router.callback_query(lambda c: c.data == "choose_premium")
async def choose_premium(callback: CallbackQuery, container: Container = init_container()):
    config: Config = container.resolve(Config)
    await callback.message.edit_text(
        text=(
            "⭐ <b>Premium — 1 месяц</b>\n\n"
            f"• Telegram Stars: <b>{config.stars_premium_monthly} Stars</b>\n"
            f"• Картой / СБП / Крипто: <b>{int(config.platega_premium_price)} ₽</b>\n\n"
            "Выбери способ оплаты:"
        ),
        parse_mode="HTML",
        reply_markup=payment_method_keyboard("premium"),
    )
    await callback.answer()


@premium_router.callback_query(lambda c: c.data == "choose_vip")
async def choose_vip(callback: CallbackQuery, container: Container = init_container()):
    config: Config = container.resolve(Config)
    await callback.message.edit_text(
        text=(
            "💎 <b>VIP — 1 месяц</b>\n\n"
            f"• Telegram Stars: <b>{config.stars_vip_monthly} Stars</b>\n"
            f"• Картой / СБП / Крипто: <b>{int(config.platega_vip_price)} ₽</b>\n\n"
            "Выбери способ оплаты:"
        ),
        parse_mode="HTML",
        reply_markup=payment_method_keyboard("vip"),
    )
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
        description="AI Icebreaker x10/день, буст профиля, приоритет в выдаче + всё из Premium",
        payload="vip_monthly",
        currency="XTR",
        prices=[LabeledPrice(label="VIP на месяц", amount=config.stars_vip_monthly)],
    )
    await callback.answer()


# ─── Platega (карта / СБП / крипто) ──────────────────────────────────────────

@premium_router.callback_query(lambda c: c.data and c.data.startswith("platega_"))
async def platega_payment(callback: CallbackQuery, container: Container = init_container()):
    """Обрабатывает platega_{product}_{method}"""
    parts = callback.data.split("_")  # ["platega", product, method]
    if len(parts) != 3:
        await callback.answer("Ошибка", show_alert=True)
        return

    _, product, method = parts
    config: Config = container.resolve(Config)

    await callback.answer("⏳ Создаём ссылку для оплаты...")

    payment_url = await create_platega_link(
        config=config,
        telegram_id=callback.from_user.id,
        product=product,
        method=method,
    )

    if not payment_url:
        await callback.message.answer(
            "❌ Не удалось создать платёж. Попробуй позже или выбери другой способ.",
        )
        return

    method_labels = {"card": "💳 Картой", "sbp": "📱 СБП", "crypto": "₿ Крипто"}
    product_labels = {"premium": "Premium", "vip": "VIP", "superlike": "Суперлайк"}

    await callback.message.answer(
        text=(
            f"✅ Ссылка для оплаты готова!\n\n"
            f"Продукт: <b>{product_labels.get(product, product)}</b>\n"
            f"Способ: <b>{method_labels.get(method, method)}</b>\n\n"
            f"Нажми кнопку ниже для оплаты 👇"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Перейти к оплате", url=payment_url)],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="premium_info")],
            ]
        ),
    )


# ─── Telegram Stars: обработка успешной оплаты ───────────────────────────────

@premium_router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@premium_router.message(lambda m: m.successful_payment is not None)
async def successful_payment(message: Message, container: Container = init_container()):
    payment = message.successful_payment
    payload = payment.invoice_payload
    service: BaseUsersService = container.resolve(BaseUsersService)

    if payload == "premium_monthly":
        premium_type, label = "premium", "Premium"
    elif payload == "vip_monthly":
        premium_type, label = "vip", "VIP"
    else:
        await message.answer("✅ Оплата получена!")
        return

    until = datetime.utcnow() + timedelta(days=30)
    try:
        await service.update_user_info_after_reg(
            telegram_id=message.from_user.id,
            data={"premium_type": premium_type, "premium_until": until},
        )
    except Exception:
        pass

    await message.answer(
        f"✅ Оплата прошла успешно!\n\n"
        f"🎉 Активирован <b>LSJLove {label}</b> на 30 дней!\n"
        f"Открой профиль чтобы убедиться.",
        parse_mode="HTML",
    )
