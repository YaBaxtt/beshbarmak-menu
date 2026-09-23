import html
import logging

from asgiref.sync import async_to_sync
from django.conf import settings

from reservations.models import Reservation, ReservationOccasion, StaffProfile


logger = logging.getLogger(__name__)


def reservation_text(reservation, occasion=None):
    occasion = occasion or reservation.get_occasion_label("uz")
    comment = reservation.customer_comment or "Izoh yo‘q"
    return (
        f"🆕 <b>Yangi bron {html.escape(reservation.public_number)}</b>\n\n"
        f"📅 {reservation.date:%d.%m.%Y}\n"
        f"🕐 {reservation.time:%H:%M}\n\n"
        f"👥 Mehmonlar: {reservation.guests_count}\n"
        f"🏠 {html.escape(reservation.space.localized_name('uz'))}\n\n"
        f"👤 {html.escape(reservation.customer_name)}\n"
        f"📞 {html.escape(reservation.phone)}\n\n"
        f"🎉 Tashrif sababi: {html.escape(occasion)}\n"
        f"💬 Izoh: {html.escape(comment)}"
    )


async def _notify(reservation_id):
    from aiogram import Bot
    from aiogram.enums import ParseMode
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    reservation = await Reservation.objects.select_related("space").aget(pk=reservation_id)
    occasion = "Ko‘rsatilmagan"
    if reservation.occasion:
        option = await ReservationOccasion.objects.filter(code=reservation.occasion).afirst()
        occasion = option.name_uz if option else {
            "REGULAR": "Oddiy tashrif",
            "BIRTHDAY": "Tug‘ilgan kun",
            "FAMILY": "Oilaviy tadbir",
            "BUSINESS": "Ish uchrashuvi",
            "OTHER": "Boshqa",
        }.get(reservation.occasion, reservation.occasion)
    recipients = StaffProfile.objects.filter(
        is_active=True, user__is_active=True, telegram_notifications_enabled=True,
        telegram_id__isnull=False, role__in=(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER),
    )
    bot = Bot(settings.BOT_TOKEN)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"accept:{reservation.pk}"), InlineKeyboardButton(text="🕐 Boshqa vaqt", callback_data=f"propose:{reservation.pk}")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject:{reservation.pk}"), InlineKeyboardButton(text="📋 Batafsil", callback_data=f"detail:{reservation.pk}")],
    ])
    try:
        async for profile in recipients:
            try:
                await bot.send_message(profile.telegram_id, reservation_text(reservation, occasion), parse_mode=ParseMode.HTML, reply_markup=keyboard)
            except Exception:
                logger.exception("Не удалось отправить Telegram-уведомление сотруднику %s", profile.pk)
    finally:
        await bot.session.close()


def notify_new_reservation(reservation_id):
    if not settings.BOT_TOKEN:
        logger.info("BOT_TOKEN не задан; уведомление для брони %s пропущено", reservation_id)
        return
    async_to_sync(_notify)(reservation_id)
