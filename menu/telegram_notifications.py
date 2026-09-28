import html
import logging
import threading

from asgiref.sync import async_to_sync
from django.conf import settings
from django.db import close_old_connections


logger = logging.getLogger(__name__)


async def _recipients():
    from reservations.models import StaffProfile

    queryset = StaffProfile.objects.filter(
        is_active=True,
        user__is_active=True,
        telegram_notifications_enabled=True,
        telegram_id__isnull=False,
        role__in=(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER),
    ).values_list("telegram_id", flat=True)
    return [telegram_id async for telegram_id in queryset]


async def _notify_complaint(complaint_id):
    from aiogram import Bot
    from aiogram.enums import ParseMode
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from reservations.models import Complaint

    complaint = await Complaint.objects.select_related("space").aget(pk=complaint_id)
    place = complaint.space.localized_name("uz") if complaint.space else "Ko‘rsatilmagan"
    if complaint.place_details:
        place = f"{place} · {complaint.place_details}"
    text = (
        f"⚠️ <b>Yangi shikoyat {html.escape(complaint.public_number or '')}</b>\n\n"
        f"📌 <b>Sabab:</b> {html.escape(complaint.localized_reason('uz'))}\n"
        f"🏠 <b>Joy:</b> {html.escape(place)}\n\n"
        f"📝 {html.escape(complaint.description)}\n\n"
        "🔒 Shikoyat anonim yuborilgan."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👀 Ko‘rib chiqishga olish", callback_data=f"complaint_review:{complaint.pk}:new:1")],
        [InlineKeyboardButton(text="📋 Barcha shikoyatlar", callback_data="complaints:new:1")],
    ])
    bot = Bot(settings.BOT_TOKEN)
    try:
        for telegram_id in await _recipients():
            try:
                await bot.send_message(telegram_id, text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            except Exception:
                logger.exception("Telegram shikoyat xabari yuborilmadi: %s", telegram_id)
    finally:
        await bot.session.close()


async def _notify_review(review_id):
    from aiogram import Bot
    from aiogram.enums import ParseMode
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from menu.models import Review

    review = await Review.objects.aget(pk=review_id)
    guest = review.guest_name or "Anonim mehmon"
    text = (
        "⭐ <b>Yangi mehmon fikri</b>\n\n"
        f"👤 {html.escape(guest)}\n"
        f"⭐ {'★' * review.rating}{'☆' * (5 - review.rating)}\n"
        f"🌐 Til: {html.escape(review.get_language_display())}\n\n"
        f"💬 {html.escape(review.text)}\n\n"
        "Fikr saytda ko‘rinishi uchun uni tasdiqlang."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Saytda ko‘rsatish", callback_data=f"review_publish:{review.pk}"),
        InlineKeyboardButton(text="⛔ Yashirish", callback_data=f"review_hide:{review.pk}"),
    ]])
    bot = Bot(settings.BOT_TOKEN)
    try:
        for telegram_id in await _recipients():
            try:
                await bot.send_message(telegram_id, text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            except Exception:
                logger.exception("Telegram fikr xabari yuborilmadi: %s", telegram_id)
    finally:
        await bot.session.close()


def _in_background(kind, object_id):
    if not settings.BOT_TOKEN or settings.BOT_TOKEN.startswith("replace-"):
        logger.info("BOT_TOKEN sozlanmagan; %s #%s xabari yuborilmadi", kind, object_id)
        return

    target = _notify_complaint if kind == "complaint" else _notify_review

    def worker():
        close_old_connections()
        try:
            async_to_sync(target)(object_id)
        except Exception:
            logger.exception("Telegram %s bildirishnomasi yuborilmadi", kind)
        finally:
            close_old_connections()

    threading.Thread(target=worker, name=f"{kind}-notify-{object_id}", daemon=True).start()


def notify_new_complaint_in_background(complaint_id):
    _in_background("complaint", complaint_id)


def notify_new_review_in_background(review_id):
    _in_background("review", review_id)
