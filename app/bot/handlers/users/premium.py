from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from punq import Container

from app.bot.keyboards.inline import premium_keyboard
from app.bot.utils.constants import premium_info_message
from app.logic.init import init_container
from app.settings.config import Config


premium_router = Router(name="Premium router")


@premium_router.message(Command("premium"))
async def premium_command(message: Message, container: Container = init_container()):
    config: Config = container.resolve(Config)
    await message.answer(
        text=premium_info_message(),
        parse_mode="HTML",
        reply_markup=premium_keyboard(
            stars_premium=config.stars_premium_monthly,
            stars_vip=config.stars_vip_monthly,
        ),
    )


@premium_router.callback_query(lambda c: c.data == "premium_info")
async def premium_info_callback(callback: CallbackQuery, container: Container = init_container()):
    config: Config = container.resolve(Config)
    await callback.message.answer(
        text=premium_info_message(),
        parse_mode="HTML",
        reply_markup=premium_keyboard(
            stars_premium=config.stars_premium_monthly,
            stars_vip=config.stars_vip_monthly,
        ),
    )
    await callback.answer()


@premium_router.callback_query(lambda c: c.data == "buy_premium")
async def buy_premium_callback(callback: CallbackQuery, container: Container = init_container()):
    config: Config = container.resolve(Config)
    await callback.message.answer_invoice(
        title="LSJLove Premium",
        description="Безлимитные лайки, просмотр кто лайкнул, откат свайпа, 1 суперлайк/день",
        payload="premium_monthly",
        currency="XTR",
        prices=[LabeledPrice(label="Premium на месяц", amount=config.stars_premium_monthly)],
    )
    await callback.answer()


@premium_router.callback_query(lambda c: c.data == "buy_vip")
async def buy_vip_callback(callback: CallbackQuery, container: Container = init_container()):
    config: Config = container.resolve(Config)
    await callback.message.answer_invoice(
        title="LSJLove VIP",
        description="AI Icebreaker x10/день, буст профиля, приоритет в выдаче + всё из Premium",
        payload="vip_monthly",
        currency="XTR",
        prices=[LabeledPrice(label="VIP на месяц", amount=config.stars_vip_monthly)],
    )
    await callback.answer()


@premium_router.callback_query(lambda c: c.data == "buy_superlike")
async def buy_superlike_callback(callback: CallbackQuery, container: Container = init_container()):
    config: Config = container.resolve(Config)
    await callback.message.answer_invoice(
        title="Суперлайк",
        description="Твой профиль будет показан первым этому пользователю",
        payload="superlike_single",
        currency="XTR",
        prices=[LabeledPrice(label="Суперлайк", amount=config.stars_superlike)],
    )
    await callback.answer()


@premium_router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@premium_router.message(lambda m: m.successful_payment is not None)
async def successful_payment(message: Message, container: Container = init_container()):
    payment = message.successful_payment
    payload = payment.invoice_payload

    if payload == "premium_monthly":
        subscription = "premium"
        label = "Premium"
    elif payload == "vip_monthly":
        subscription = "vip"
        label = "VIP"
    else:
        subscription = "premium"
        label = "Premium"

    await message.answer(
        f"✅ Оплата прошла успешно!\n\n"
        f"🎉 Тебе активирован <b>LSJLove {label}</b>!\n"
        f"Используй команду /profile чтобы увидеть свой обновлённый профиль.",
        parse_mode="HTML",
    )
