import html
from datetime import date, datetime, timedelta
from math import ceil

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from reservations.models import DiningSpace, Reservation, ReservationAction, ReservationOccasion, SiteVisitDaily, StaffProfile
from reservations.services import AlreadyProcessedError, AvailabilityError, ReservationService
from telegram_bot.reports import REPORT_LIMIT, build_reservation_report


router = Router()


class ProposalState(StatesGroup):
    waiting_time = State()
    waiting_comment = State()
    confirmation = State()


class RejectState(StatesGroup):
    waiting_custom = State()
    confirmation = State()


class AdminAddState(StatesGroup):
    waiting_id = State()
    waiting_name = State()


class SpaceAddState(StatesGroup):
    waiting_name = State()
    waiting_capacity = State()


class HistoryDateState(StatesGroup):
    waiting_from = State()
    waiting_to = State()


STATUS_UZ = {
    Reservation.Status.PENDING: "Tasdiqlanishi kutilmoqda",
    Reservation.Status.ACCEPTED: "Tasdiqlandi",
    Reservation.Status.CHANGE_PROPOSED: "Boshqa vaqt taklif qilindi",
    Reservation.Status.REJECTED: "Rad etildi",
    Reservation.Status.CANCELLED: "Bekor qilindi",
    Reservation.Status.COMPLETED: "Yakunlandi",
    Reservation.Status.NO_SHOW: "Mehmon kelmadi",
}

HISTORY_PAGE_SIZE = 15
HISTORY_LABELS = {
    "today": "Bugungi arizalar",
    "accepted": "Qabul qilingan",
    "waiting": "Javob kutilayotgan",
    "rejected": "Rad etilgan",
    "cancelled": "Bekor qilingan",
    "all": "Barcha arizalar",
    "range": "Tanlangan sana oralig‘i",
}


def main_keyboard(profile=None):
    rows = [
        [InlineKeyboardButton(text="🆕 Yangi arizalar", callback_data="list:new")],
        [InlineKeyboardButton(text="📚 Arizalar tarixi", callback_data="history"), InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton(text="🏠 Zallar va xonalar", callback_data="spaces")],
    ]
    if profile and profile.role == StaffProfile.Role.OWNER:
        rows.append([InlineKeyboardButton(text="👥 Administratorlar", callback_data="admins")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_keyboard(profile=None):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="← Bosh menyu", callback_data="home")]])


@sync_to_async(thread_sensitive=True)
def authorized_profile(telegram_id):
    profile = StaffProfile.objects.select_related("user").filter(
        telegram_id=telegram_id,
        is_active=True,
        user__is_active=True,
        role__in=(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER),
    ).first()
    if profile:
        return profile

    primary_owner_id = str(settings.PRIMARY_OWNER_TELEGRAM_ID).strip()
    if not primary_owner_id.isdigit() or int(primary_owner_id) != telegram_id:
        return None

    with transaction.atomic():
        existing = StaffProfile.objects.select_for_update().select_related("user").filter(telegram_id=telegram_id).first()
        if existing:
            return None
        user, created = get_user_model().objects.get_or_create(
            username=f"telegram_owner_{telegram_id}",
            defaults={"first_name": "Asosiy", "last_name": "egasi", "is_staff": True, "is_active": True},
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=("password",))
        elif not user.is_active or not user.is_staff:
            user.is_active = True
            user.is_staff = True
            user.save(update_fields=("is_active", "is_staff"))
        return StaffProfile.objects.create(
            user=user, role=StaffProfile.Role.OWNER, telegram_id=telegram_id,
            telegram_notifications_enabled=True, is_active=True,
        )


async def require_profile(event, owner_only=False):
    profile = await authorized_profile(event.from_user.id)
    denied = not profile or (owner_only and profile.role != StaffProfile.Role.OWNER)
    if denied:
        text = "Bu bo‘limga kirish huquqingiz yo‘q."
        if isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
        else:
            await event.answer(text)
        return None
    return profile


@sync_to_async(thread_sensitive=True)
def get_reservation(pk):
    item = Reservation.objects.select_related("space", "handled_by_staff__user").get(pk=pk)
    item.occasion_uz = _occasion_labels([item]).get(item.occasion, "Ko‘rsatilmagan")
    return item


def _occasion_labels(items):
    codes = {item.occasion for item in items if item.occasion}
    labels = dict(ReservationOccasion.objects.filter(code__in=codes).values_list("code", "name_uz"))
    labels.update({
        code: label for code, label in {
            "REGULAR": "Oddiy tashrif", "BIRTHDAY": "Tug‘ilgan kun",
            "FAMILY": "Oilaviy tadbir", "BUSINESS": "Ish uchrashuvi", "OTHER": "Boshqa",
        }.items() if code not in labels
    })
    return labels


def detail_text(item):
    return (
        f"<b>{html.escape(item.public_number)} · {STATUS_UZ.get(item.status, item.status)}</b>\n\n"
        f"📅 {item.date:%d.%m.%Y} · 🕐 {item.time:%H:%M}\n"
        f"👥 {item.guests_count} mehmon · 🏠 {html.escape(item.space.localized_name('uz'))}\n"
        f"🎉 {html.escape(getattr(item, 'occasion_uz', None) or 'Ko‘rsatilmagan')}\n\n"
        f"👤 {html.escape(item.customer_name)}\n"
        f"📞 {html.escape(item.phone)}\n"
        f"💬 {html.escape(item.customer_comment or 'Izoh yo‘q')}"
    )


def action_keyboard(pk):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"accept:{pk}"), InlineKeyboardButton(text="🕐 Boshqa vaqt", callback_data=f"propose:{pk}")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject:{pk}"), InlineKeyboardButton(text="← Bosh menyu", callback_data="home")],
    ])


@router.message(CommandStart())
async def start(message: Message):
    profile = await require_profile(message)
    if profile:
        await message.answer("🍽 <b>Beshbarmak boshqaruvi</b>\n\nKerakli bo‘limni tanlang:", parse_mode="HTML", reply_markup=main_keyboard(profile))


@router.callback_query(F.data == "home")
async def home(callback: CallbackQuery, state: FSMContext):
    profile = await require_profile(callback)
    if not profile:
        return
    await state.clear()
    await callback.message.answer("🍽 <b>Bosh menyu</b>", parse_mode="HTML", reply_markup=main_keyboard(profile))
    await callback.answer()


@router.callback_query(F.data.startswith("detail:"))
async def detail(callback: CallbackQuery):
    if not await require_profile(callback):
        return
    item = await get_reservation(int(callback.data.split(":")[1]))
    keyboard = action_keyboard(item.pk) if item.status == Reservation.Status.PENDING else back_keyboard()
    await callback.message.answer(detail_text(item), parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("accept:"))
async def accept_prompt(callback: CallbackQuery):
    if not await require_profile(callback):
        return
    item = await get_reservation(int(callback.data.split(":")[1]))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha, tasdiqlash", callback_data=f"confirm_accept:{item.pk}"),
        InlineKeyboardButton(text="Bekor qilish", callback_data="cancel_action"),
    ]])
    await callback.message.answer(f"Bronni tasdiqlaysizmi?\n\n{detail_text(item)}", parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_accept:"))
async def accept_confirm(callback: CallbackQuery):
    profile = await require_profile(callback)
    if not profile:
        return
    pk = int(callback.data.split(":")[1])
    try:
        item = await sync_to_async(ReservationService.accept, thread_sensitive=True)(pk, profile)
    except (AvailabilityError, AlreadyProcessedError):
        await callback.answer("Ariza qayta ishlangan yoki bu vaqt endi bo‘sh emas.", show_alert=True)
        return
    await callback.message.edit_text(f"✅ <b>{item.public_number} tasdiqlandi</b>\nMas’ul: {html.escape(str(profile))}", parse_mode="HTML")
    await callback.answer("Tasdiqlandi")


@router.callback_query(F.data.startswith("propose:"))
async def propose_start(callback: CallbackQuery, state: FSMContext):
    if not await require_profile(callback):
        return
    await state.set_state(ProposalState.waiting_time)
    await state.update_data(reservation_id=int(callback.data.split(":")[1]))
    await callback.message.answer("Yangi vaqtni <b>20:30</b> shaklida yuboring:", parse_mode="HTML")
    await callback.answer()


@router.message(ProposalState.waiting_time)
async def propose_time(message: Message, state: FSMContext):
    if not await require_profile(message):
        return
    try:
        value = datetime.strptime(message.text.strip(), "%H:%M").time()
    except (ValueError, AttributeError):
        await message.answer("Vaqt tushunilmadi. Masalan: 20:30")
        return
    await state.update_data(proposed_time=value.strftime("%H:%M"))
    await state.set_state(ProposalState.waiting_comment)
    await message.answer("Mehmon uchun izoh yozing. Izoh kerak bo‘lmasa «-» yuboring:")


@router.message(ProposalState.waiting_comment)
async def propose_comment(message: Message, state: FSMContext):
    if not await require_profile(message):
        return
    data = await state.get_data()
    comment = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(comment=comment)
    await state.set_state(ProposalState.confirmation)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Yuborish", callback_data="confirm_proposal"),
        InlineKeyboardButton(text="Bekor qilish", callback_data="cancel_action"),
    ]])
    await message.answer(f"<b>{data['proposed_time']}</b> vaqtini taklif qilamizmi?\n{html.escape(comment)}", parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(ProposalState.confirmation, F.data == "confirm_proposal")
async def propose_confirm(callback: CallbackQuery, state: FSMContext):
    profile = await require_profile(callback)
    if not profile:
        return
    data = await state.get_data()
    item = await get_reservation(data["reservation_id"])
    try:
        await sync_to_async(ReservationService.propose, thread_sensitive=True)(
            item.pk, proposed_date=item.date,
            proposed_time=datetime.strptime(data["proposed_time"], "%H:%M").time(),
            comment=data["comment"], actor=profile,
        )
    except (AvailabilityError, AlreadyProcessedError):
        await callback.answer("Bu vaqtni taklif qilib bo‘lmaydi. Arizani qayta tekshiring.", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(f"🕐 Mehmonga {data['proposed_time']} vaqti taklif qilindi.")
    await callback.answer()


REJECTION_REASONS = ["Bo‘sh joy qolmagan", "Tanlangan xona vaqtincha mavjud emas", "Bu vaqtda restoran yopiq", "Mehmonlar soni juda katta"]


@router.callback_query(F.data.startswith("reject:"))
async def reject_start(callback: CallbackQuery, state: FSMContext):
    if not await require_profile(callback):
        return
    await state.update_data(reservation_id=int(callback.data.split(":")[1]))
    rows = [[InlineKeyboardButton(text=reason, callback_data=f"reason:{index}")] for index, reason in enumerate(REJECTION_REASONS)]
    rows.append([InlineKeyboardButton(text="✍️ Boshqa sabab", callback_data="reason:custom")])
    await callback.message.answer("Rad etish sababini tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("reason:"))
async def reject_reason(callback: CallbackQuery, state: FSMContext):
    if not await require_profile(callback):
        return
    key = callback.data.split(":")[1]
    if key == "custom":
        await state.set_state(RejectState.waiting_custom)
        await callback.message.answer("Mehmon uchun sababni yozing:")
        await callback.answer()
        return
    await state.update_data(reason=REJECTION_REASONS[int(key)])
    await show_reject_preview(callback.message, state)
    await callback.answer()


@router.message(RejectState.waiting_custom)
async def reject_custom(message: Message, state: FSMContext):
    if await require_profile(message):
        await state.update_data(reason=message.text.strip())
        await show_reject_preview(message, state)


async def show_reject_preview(message, state):
    data = await state.get_data()
    await state.set_state(RejectState.confirmation)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Rad etishni tasdiqlash", callback_data="confirm_reject"),
        InlineKeyboardButton(text="Bekor qilish", callback_data="cancel_action"),
    ]])
    await message.answer(f"Mehmonga ko‘rinadigan sabab:\n<b>{html.escape(data['reason'])}</b>", parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(RejectState.confirmation, F.data == "confirm_reject")
async def reject_confirm(callback: CallbackQuery, state: FSMContext):
    profile = await require_profile(callback)
    if not profile:
        return
    data = await state.get_data()
    try:
        item = await sync_to_async(ReservationService.reject, thread_sensitive=True)(data["reservation_id"], reason=data["reason"], actor=profile)
    except AlreadyProcessedError:
        await callback.answer("Bu ariza allaqachon qayta ishlangan.", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(f"❌ {item.public_number} rad etildi.\nSabab: {html.escape(data['reason'])}")
    await callback.answer()


@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    if await require_profile(callback):
        await state.clear()
        await callback.message.edit_text("Amal bekor qilindi.")
        await callback.answer()


@sync_to_async(thread_sensitive=True)
def list_items(kind):
    queryset = Reservation.objects.select_related("space")
    today = timezone.localdate()
    if kind == "new":
        queryset = queryset.filter(status=Reservation.Status.PENDING)
    elif kind == "today":
        queryset = queryset.filter(date=today)
    elif kind == "accepted":
        queryset = queryset.filter(status=Reservation.Status.ACCEPTED)
    elif kind == "waiting":
        queryset = queryset.filter(status=Reservation.Status.CHANGE_PROPOSED)
    items = list(queryset.order_by("-created_at", "-pk")[:HISTORY_PAGE_SIZE])
    labels = _occasion_labels(items)
    for item in items:
        item.occasion_uz = labels.get(item.occasion, item.occasion or "Ko‘rsatilmagan")
    return items


@router.callback_query(F.data.startswith("list:"))
async def listing(callback: CallbackQuery):
    if not await require_profile(callback):
        return
    items = await list_items(callback.data.split(":")[1])
    if not items:
        await callback.message.answer("Bu bo‘limda hozircha bronlar yo‘q.", reply_markup=back_keyboard())
    for item in items:
        keyboard = action_keyboard(item.pk) if item.status == Reservation.Status.PENDING else back_keyboard()
        await callback.message.answer(detail_text(item), parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


def history_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Bugungi arizalar", callback_data="hist:today:1")],
        [
            InlineKeyboardButton(text="✅ Qabul qilingan", callback_data="hist:accepted:1"),
            InlineKeyboardButton(text="🕐 Javob kutilayotgan", callback_data="hist:waiting:1"),
        ],
        [
            InlineKeyboardButton(text="❌ Rad etilgan", callback_data="hist:rejected:1"),
            InlineKeyboardButton(text="🚫 Bekor qilingan", callback_data="hist:cancelled:1"),
        ],
        [InlineKeyboardButton(text="📚 Barcha arizalar", callback_data="hist:all:1")],
        [InlineKeyboardButton(text="📆 Sana oralig‘ini tanlash", callback_data="history_dates")],
        [InlineKeyboardButton(text="🆕 Yangi arizalar", callback_data="list:new")],
        [InlineKeyboardButton(text="← Bosh menyu", callback_data="home")],
    ])


@router.callback_query(F.data == "history")
async def history_menu(callback: CallbackQuery, state: FSMContext):
    if not await require_profile(callback):
        return
    await state.clear()
    text = "📚 <b>Arizalar tarixi</b>\n\nKo‘rmoqchi bo‘lgan bo‘limni tanlang. Har bir sahifada 15 ta ariza ko‘rsatiladi."
    if callback.message.text:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=history_keyboard())
    else:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=history_keyboard())
    await callback.answer()


def _history_queryset(kind, date_from=None, date_to=None):
    queryset = Reservation.objects.select_related("space", "handled_by_staff__user")
    today = timezone.localdate()
    if kind == "today":
        queryset = queryset.filter(date=today)
    elif kind == "accepted":
        queryset = queryset.filter(status=Reservation.Status.ACCEPTED)
    elif kind == "waiting":
        queryset = queryset.filter(status=Reservation.Status.CHANGE_PROPOSED)
    elif kind == "rejected":
        queryset = queryset.filter(status=Reservation.Status.REJECTED)
    elif kind == "cancelled":
        queryset = queryset.filter(status=Reservation.Status.CANCELLED)
    elif kind == "range":
        queryset = queryset.filter(date__range=(date_from, date_to))
    elif kind != "all":
        raise ValueError("Noma’lum tarix filtri")
    return queryset.order_by("-created_at", "-pk")


def _history_page_data(kind, page=1, date_from=None, date_to=None):
    queryset = _history_queryset(kind, date_from, date_to)
    total = queryset.count()
    pages = max(1, ceil(total / HISTORY_PAGE_SIZE))
    page = min(max(int(page), 1), pages)
    start = (page - 1) * HISTORY_PAGE_SIZE
    items = list(queryset[start:start + HISTORY_PAGE_SIZE])
    labels = _occasion_labels(items)
    for item in items:
        item.occasion_uz = labels.get(item.occasion, item.occasion or "Ko‘rsatilmagan")
    return items, total, page, pages


get_history_page_data = sync_to_async(_history_page_data, thread_sensitive=True)


def _short(value, limit):
    value = " ".join(str(value or "").split())
    return value if len(value) <= limit else f"{value[:limit - 1]}…"


def history_page_text(kind, items, total, page, pages, *, start_index, date_from=None, date_to=None):
    title = HISTORY_LABELS[kind]
    if kind == "range":
        title = f"{date_from:%d.%m.%Y} - {date_to:%d.%m.%Y}"
    lines = [f"📚 <b>{html.escape(title)}</b>", f"Jami: <b>{total}</b> · Sahifa: <b>{page}/{pages}</b>", ""]
    if not items:
        lines.append("Bu bo‘limda hozircha arizalar yo‘q.")
    for position, item in enumerate(items, start=start_index):
        lines.extend([
            f"<b>{position}. {html.escape(item.public_number)} · {html.escape(STATUS_UZ.get(item.status, item.status))}</b>",
            f"📅 {item.date:%d.%m.%Y} {item.time:%H:%M} · 👥 {item.guests_count} · {html.escape(_short(item.space.localized_name('uz'), 28))}",
            f"👤 {html.escape(_short(item.customer_name, 30))} · 📞 {html.escape(item.phone)}",
        ])
        if item.rejection_reason:
            lines.append(f"Sabab: {html.escape(_short(item.rejection_reason, 90))}")
        lines.append("")
    return "\n".join(lines).strip()


def history_page_keyboard(kind, items, page, pages):
    rows = []
    detail_buttons = [InlineKeyboardButton(text=f"🔎 {item.public_number}", callback_data=f"detail:{item.pk}") for item in items]
    for index in range(0, len(detail_buttons), 3):
        rows.append(detail_buttons[index:index + 3])
    navigation = []
    if page > 1:
        navigation.append(InlineKeyboardButton(text="← Oldingi", callback_data=f"hist:{kind}:{page - 1}"))
    if page < pages:
        navigation.append(InlineKeyboardButton(text="Keyingi →", callback_data=f"hist:{kind}:{page + 1}"))
    if navigation:
        rows.append(navigation)
    if items:
        rows.append([InlineKeyboardButton(text="📄 Word hisobot", callback_data=f"report:{kind}")])
    rows.extend([
        [InlineKeyboardButton(text="🆕 Yangi arizalar", callback_data="list:new")],
        [InlineKeyboardButton(text="← Tarix bo‘limlari", callback_data="history")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _range_from_state(state):
    data = await state.get_data()
    try:
        return date.fromisoformat(data["history_from"]), date.fromisoformat(data["history_to"])
    except (KeyError, TypeError, ValueError):
        return None, None


@router.callback_query(F.data.startswith("hist:"))
async def history_page(callback: CallbackQuery, state: FSMContext):
    if not await require_profile(callback):
        return
    _, kind, raw_page = callback.data.split(":", 2)
    if kind not in HISTORY_LABELS:
        await callback.answer("Noma’lum bo‘lim.", show_alert=True)
        return
    date_from = date_to = None
    if kind == "range":
        date_from, date_to = await _range_from_state(state)
        if not date_from or not date_to:
            await callback.answer("Avval sana oralig‘ini tanlang.", show_alert=True)
            return
    items, total, page, pages = await get_history_page_data(kind, raw_page, date_from, date_to)
    text = history_page_text(
        kind, items, total, page, pages,
        start_index=(page - 1) * HISTORY_PAGE_SIZE + 1,
        date_from=date_from, date_to=date_to,
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=history_page_keyboard(kind, items, page, pages),
    )
    await callback.answer()


def parse_history_date(value):
    value = (value or "").strip()
    for date_format in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    return None


@router.callback_query(F.data == "history_dates")
async def history_dates_start(callback: CallbackQuery, state: FSMContext):
    if not await require_profile(callback):
        return
    await state.clear()
    await state.set_state(HistoryDateState.waiting_from)
    await callback.message.answer(
        "📆 Boshlanish sanasini yuboring.\nMasalan: <b>01.09.2026</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Bekor qilish", callback_data="history"),
        ]]),
    )
    await callback.answer()


@router.message(HistoryDateState.waiting_from)
async def history_date_from(message: Message, state: FSMContext):
    if not await require_profile(message):
        return
    selected = parse_history_date(message.text)
    if not selected:
        await message.answer("Sana tushunilmadi. 01.09.2026 shaklida yuboring:")
        return
    await state.update_data(history_from=selected.isoformat())
    await state.set_state(HistoryDateState.waiting_to)
    await message.answer("Tugash sanasini yuboring. Masalan: <b>30.09.2026</b>", parse_mode="HTML")


@router.message(HistoryDateState.waiting_to)
async def history_date_to(message: Message, state: FSMContext):
    if not await require_profile(message):
        return
    date_to = parse_history_date(message.text)
    data = await state.get_data()
    date_from = date.fromisoformat(data["history_from"])
    if not date_to:
        await message.answer("Sana tushunilmadi. 30.09.2026 shaklida yuboring:")
        return
    if date_to < date_from:
        await message.answer("Tugash sanasi boshlanish sanasidan oldin bo‘lishi mumkin emas.")
        return
    await state.update_data(history_to=date_to.isoformat())
    await state.set_state(None)
    items, total, page, pages = await get_history_page_data("range", 1, date_from, date_to)
    await message.answer(
        history_page_text("range", items, total, page, pages, start_index=1, date_from=date_from, date_to=date_to),
        parse_mode="HTML",
        reply_markup=history_page_keyboard("range", items, page, pages),
    )


def _history_report_data(kind, date_from=None, date_to=None):
    queryset = _history_queryset(kind, date_from, date_to)
    total = queryset.count()
    items = list(queryset[:REPORT_LIMIT + 1])
    truncated = len(items) > REPORT_LIMIT
    items = items[:REPORT_LIMIT]
    labels = _occasion_labels(items)
    rows = []
    for item in items:
        created_at = timezone.localtime(item.created_at)
        manager = str(item.handled_by_staff) if item.handled_by_staff else "Mas’ul belgilanmagan"
        notes = item.rejection_reason or item.manager_comment or item.customer_comment or "Izoh yo‘q"
        rows.append({
            "public_number": item.public_number,
            "created_at": created_at.strftime("%d.%m.%Y %H:%M"),
            "customer_name": item.customer_name,
            "phone": item.phone,
            "visit_at": f"{item.date:%d.%m.%Y} {item.time:%H:%M}",
            "guests_count": item.guests_count,
            "space": item.space.localized_name("uz"),
            "occasion": labels.get(item.occasion, item.occasion or "Ko‘rsatilmagan"),
            "status": STATUS_UZ.get(item.status, item.status),
            "manager": manager,
            "notes": notes,
        })
    return rows, total, truncated


get_history_report_data = sync_to_async(_history_report_data, thread_sensitive=True)


@router.callback_query(F.data.startswith("report:"))
async def history_report(callback: CallbackQuery, state: FSMContext):
    if not await require_profile(callback):
        return
    kind = callback.data.split(":", 1)[1]
    if kind not in HISTORY_LABELS:
        await callback.answer("Noma’lum hisobot.", show_alert=True)
        return
    date_from = date_to = None
    if kind == "range":
        date_from, date_to = await _range_from_state(state)
        if not date_from or not date_to:
            await callback.answer("Avval sana oralig‘ini tanlang.", show_alert=True)
            return
    await callback.answer("Word hisobot tayyorlanmoqda...")
    rows, total, truncated = await get_history_report_data(kind, date_from, date_to)
    if not rows:
        await callback.message.answer("Bu bo‘limda hisobot uchun arizalar yo‘q.", reply_markup=history_keyboard())
        return

    if kind == "range":
        section_title = f"{date_from:%d.%m.%Y} - {date_to:%d.%m.%Y}"
        period_text = f"Tashrif sanasi {section_title}"
    elif kind == "today":
        section_title = HISTORY_LABELS[kind]
        period_text = timezone.localdate().strftime("%d.%m.%Y")
    else:
        section_title = HISTORY_LABELS[kind]
        period_text = "Barcha mavjud sanalar"

    generated_at = timezone.localtime().strftime("%d.%m.%Y %H:%M")
    document = await sync_to_async(build_reservation_report, thread_sensitive=False)(
        rows,
        section_title=section_title,
        period_text=period_text,
        generated_at=generated_at,
        total_count=total,
        truncated=truncated,
    )
    stamp = timezone.localtime().strftime("%Y%m%d_%H%M")
    filename = f"arizalar_{kind}_{stamp}.docx"
    caption = f"📄 <b>{html.escape(section_title)}</b>\nJami: {total} · Faylda: {len(rows)}"
    if truncated:
        caption += "\nEng yangi 500 ta ariza kiritildi."
    await callback.message.answer_document(
        BufferedInputFile(document, filename=filename),
        caption=caption,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆕 Yangi arizalar", callback_data="list:new")],
            [InlineKeyboardButton(text="← Tarix bo‘limlari", callback_data="history")],
        ]),
    )


@sync_to_async(thread_sensitive=True)
def statistics_data():
    today = timezone.localdate()
    week_start = today - timedelta(days=6)
    today_reservations = Reservation.objects.filter(date=today)
    week_reservations = Reservation.objects.filter(date__range=(week_start, today))
    today_visits = SiteVisitDaily.objects.filter(date=today).first()
    week_visits = SiteVisitDaily.objects.filter(date__range=(week_start, today)).aggregate(views=Sum("views"), visitors=Sum("unique_visitors"))
    today_views = today_visits.views if today_visits else 0
    week_views_count = week_visits["views"] or 0
    today_total = today_reservations.count()
    week_total = week_reservations.count()
    return {
        "today_total": today_total,
        "today_accepted": today_reservations.filter(status=Reservation.Status.ACCEPTED).count(),
        "today_rejected": today_reservations.filter(status=Reservation.Status.REJECTED).count(),
        "today_guests": today_reservations.filter(status=Reservation.Status.ACCEPTED).aggregate(total=Sum("guests_count"))["total"] or 0,
        "today_views": today_views,
        "today_visitors": today_visits.unique_visitors if today_visits else 0,
        "today_conversion": round(today_total / today_views * 100, 1) if today_views else 0,
        "week_total": week_total,
        "week_views": week_views_count,
        "week_visitors": week_visits["visitors"] or 0,
        "week_conversion": round(week_total / week_views_count * 100, 1) if week_views_count else 0,
    }


@router.callback_query(F.data == "stats")
async def stats(callback: CallbackQuery):
    profile = await require_profile(callback)
    if not profile:
        return
    data = await statistics_data()
    text = (
        "📊 <b>Restoran statistikasi</b>\n\n<b>Bugun</b>\n"
        f"Sayt ko‘rishlari: {data['today_views']}\nNoyob tashrifchilar: {data['today_visitors']}\n"
        f"Bron arizalari: {data['today_total']}\nKo‘rishdan arizaga: {data['today_conversion']}%\nTasdiqlandi: {data['today_accepted']}\n"
        f"Rad etildi: {data['today_rejected']}\nKutilayotgan mehmonlar: {data['today_guests']}\n\n"
        f"<b>Oxirgi 7 kun</b>\nSayt ko‘rishlari: {data['week_views']}\n"
        f"Noyob tashrifchilar: {data['week_visitors']}\nBron arizalari: {data['week_total']}\n"
        f"Ko‘rishdan arizaga: {data['week_conversion']}%"
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=back_keyboard(profile))
    await callback.answer()


@sync_to_async(thread_sensitive=True)
def admin_list_data():
    return list(StaffProfile.objects.select_related("user").filter(
        is_active=True, user__is_active=True,
        role__in=(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER),
    ).order_by("role", "user__first_name", "pk"))


@router.callback_query(F.data == "admins")
async def admins(callback: CallbackQuery):
    profile = await require_profile(callback, owner_only=True)
    if not profile:
        return
    members = await admin_list_data()
    rows = []
    lines = ["👥 <b>Administratorlar</b>", ""]
    for member in members:
        role = "Egasi" if member.role == StaffProfile.Role.OWNER else "Administrator"
        lines.append(f"• {html.escape(str(member))} — {role}\n  ID: <code>{member.telegram_id or '—'}</code>")
        if member.role == StaffProfile.Role.MANAGER:
            rows.append([InlineKeyboardButton(text=f"🗑 {str(member)[:28]}", callback_data=f"admin_remove:{member.pk}")])
    rows.extend([
        [InlineKeyboardButton(text="➕ Administrator qo‘shish", callback_data="admin_add")],
        [InlineKeyboardButton(text="← Bosh menyu", callback_data="home")],
    ])
    await callback.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data == "admin_add")
async def admin_add_start(callback: CallbackQuery, state: FSMContext):
    if not await require_profile(callback, owner_only=True):
        return
    await state.set_state(AdminAddState.waiting_id)
    await callback.message.answer(
        "Yangi administratorning Telegram raqamli ID sini yuboring.\n\n"
        "Uni @userinfobot orqali bilish mumkin. Misol: <code>123456789</code>", parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminAddState.waiting_id)
async def admin_add_id(message: Message, state: FSMContext):
    if not await require_profile(message, owner_only=True):
        return
    value = (message.text or "").strip()
    if not value.isdigit():
        await message.answer("Faqat raqamli Telegram ID yuboring.")
        return
    await state.update_data(telegram_id=int(value))
    await state.set_state(AdminAddState.waiting_name)
    await message.answer("Administratorning ismini yuboring:")


@sync_to_async(thread_sensitive=True)
def create_or_restore_admin(telegram_id, name):
    with transaction.atomic():
        existing = StaffProfile.objects.select_for_update().select_related("user").filter(telegram_id=telegram_id).first()
        if existing:
            if existing.role == StaffProfile.Role.OWNER:
                return existing, False, "Bu foydalanuvchi allaqachon egasi."
            existing.role = StaffProfile.Role.MANAGER
            existing.is_active = True
            existing.telegram_notifications_enabled = True
            existing.user.is_active = True
            existing.user.is_staff = True
            existing.user.first_name = name
            existing.user.save(update_fields=("is_active", "is_staff", "first_name"))
            existing.save(update_fields=("role", "is_active", "telegram_notifications_enabled", "updated_at"))
            return existing, True, "Administrator qayta faollashtirildi."
        user = get_user_model().objects.create(username=f"telegram_admin_{telegram_id}", first_name=name, is_active=True, is_staff=True)
        user.set_unusable_password()
        user.save(update_fields=("password",))
        profile = StaffProfile.objects.create(
            user=user, role=StaffProfile.Role.MANAGER, telegram_id=telegram_id,
            telegram_notifications_enabled=True, is_active=True,
        )
        return profile, True, "Administrator qo‘shildi."


@router.message(AdminAddState.waiting_name)
async def admin_add_name(message: Message, state: FSMContext):
    if not await require_profile(message, owner_only=True):
        return
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Ism kamida 2 ta belgidan iborat bo‘lsin.")
        return
    data = await state.get_data()
    member, success, result_text = await create_or_restore_admin(data["telegram_id"], name[:150])
    await state.clear()
    await message.answer(f"{'✅' if success else 'ℹ️'} {result_text}\n{name}: <code>{member.telegram_id}</code>", parse_mode="HTML", reply_markup=back_keyboard())


@router.callback_query(F.data.startswith("admin_remove:"))
async def admin_remove_prompt(callback: CallbackQuery):
    if not await require_profile(callback, owner_only=True):
        return
    pk = int(callback.data.split(":")[1])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗑 Ha, o‘chirish", callback_data=f"admin_remove_confirm:{pk}"),
        InlineKeyboardButton(text="Bekor qilish", callback_data="admins"),
    ]])
    await callback.message.answer("Administrator kirishini o‘chirasizmi? Bronlar tarixi saqlanadi.", reply_markup=keyboard)
    await callback.answer()


@sync_to_async(thread_sensitive=True)
def deactivate_admin(pk):
    profile = StaffProfile.objects.select_related("user").get(pk=pk, role=StaffProfile.Role.MANAGER)
    profile.is_active = False
    profile.telegram_notifications_enabled = False
    profile.user.is_active = False
    profile.user.save(update_fields=("is_active",))
    profile.save(update_fields=("is_active", "telegram_notifications_enabled", "updated_at"))
    return str(profile)


@router.callback_query(F.data.startswith("admin_remove_confirm:"))
async def admin_remove_confirm(callback: CallbackQuery):
    if not await require_profile(callback, owner_only=True):
        return
    name = await deactivate_admin(int(callback.data.split(":")[1]))
    await callback.message.edit_text(f"✅ {html.escape(name)} administratorlar ro‘yxatidan olib tashlandi.", parse_mode="HTML")
    await callback.answer()


@sync_to_async(thread_sensitive=True)
def spaces_data():
    return list(DiningSpace.objects.order_by("sort_order", "id"))


@router.callback_query(F.data == "spaces")
async def spaces(callback: CallbackQuery):
    profile = await require_profile(callback)
    if not profile:
        return
    items = await spaces_data()
    rows = []
    lines = ["🏠 <b>Zallar va xonalar</b>", ""]
    for item in items:
        available = item.is_active and item.is_bookable and not item.is_temporarily_unavailable
        lines.append(f"{'🟢' if available else '🔴'} {html.escape(item.localized_name('uz'))} · {item.capacity_max} kishigacha")
        rows.append([InlineKeyboardButton(
            text=f"{'⛔ Yopish' if available else '✅ Ochish'} · {item.localized_name('uz')[:24]}",
            callback_data=f"space_toggle:{item.pk}",
        )])
    if profile.role == StaffProfile.Role.OWNER:
        rows.append([InlineKeyboardButton(text="➕ Yangi joy qo‘shish", callback_data="space_add")])
    rows.append([InlineKeyboardButton(text="← Bosh menyu", callback_data="home")])
    await callback.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@sync_to_async(thread_sensitive=True)
def toggle_space(pk, actor):
    with transaction.atomic():
        space = DiningSpace.objects.select_for_update().get(pk=pk)
        currently_available = space.is_active and space.is_bookable and not space.is_temporarily_unavailable
        if currently_available:
            space.is_temporarily_unavailable = True
            space.unavailable_reason = "Временно закрыто администратором"
            space.unavailable_reason_uz = "Administrator tomonidan vaqtincha yopildi"
            action = ReservationAction.Action.SPACE_DISABLED
        else:
            space.is_active = True
            space.is_bookable = True
            space.is_temporarily_unavailable = False
            space.unavailable_reason = ""
            space.unavailable_reason_uz = ""
            action = ReservationAction.Action.SPACE_ENABLED
        space.save()
        ReservationAction.objects.create(space=space, actor=actor, action=action, comment="Telegram bot")
        return space, not currently_available


@router.callback_query(F.data.startswith("space_toggle:"))
async def space_toggle(callback: CallbackQuery):
    profile = await require_profile(callback)
    if not profile:
        return
    space, available = await toggle_space(int(callback.data.split(":")[1]), profile)
    await callback.message.answer(
        f"{'✅' if available else '⛔'} {html.escape(space.localized_name('uz'))}: {'bron uchun ochildi' if available else 'vaqtincha yopildi'}.",
        parse_mode="HTML", reply_markup=back_keyboard(profile),
    )
    await callback.answer()


@router.callback_query(F.data == "space_add")
async def space_add_start(callback: CallbackQuery, state: FSMContext):
    if not await require_profile(callback, owner_only=True):
        return
    await state.set_state(SpaceAddState.waiting_name)
    await callback.message.answer("Joy nomlarini <b>O‘zbekcha | Ruscha</b> shaklida yuboring.\nMasalan: <code>VIP xona | VIP-комната</code>", parse_mode="HTML")
    await callback.answer()


@router.message(SpaceAddState.waiting_name)
async def space_add_name(message: Message, state: FSMContext):
    if not await require_profile(message, owner_only=True):
        return
    parts = [part.strip() for part in (message.text or "").split("|", 1)]
    if not parts[0]:
        await message.answer("Joy nomini kiriting.")
        return
    await state.update_data(name_uz=parts[0][:160], name_ru=(parts[1] if len(parts) > 1 and parts[1] else parts[0])[:160])
    await state.set_state(SpaceAddState.waiting_capacity)
    await message.answer("Bu joyga sig‘adigan eng ko‘p mehmonlar sonini yuboring:")


@sync_to_async(thread_sensitive=True)
def create_space(name_uz, name_ru, capacity):
    return DiningSpace.objects.create(
        name=name_ru, name_uz=name_uz,
        description="Telegram bot orqali qo‘shilgan xona.",
        description_uz="Telegram bot orqali qo‘shilgan xona.",
        space_type=DiningSpace.SpaceType.PRIVATE_ROOM,
        capacity_min=1, capacity_max=capacity, is_exclusive=True,
        is_active=True, is_bookable=True,
        sort_order=(DiningSpace.objects.order_by("-sort_order").values_list("sort_order", flat=True).first() or 0) + 10,
    )


@router.message(SpaceAddState.waiting_capacity)
async def space_add_capacity(message: Message, state: FSMContext):
    if not await require_profile(message, owner_only=True):
        return
    try:
        capacity = int((message.text or "").strip())
    except ValueError:
        capacity = 0
    if not 1 <= capacity <= 500:
        await message.answer("1 dan 500 gacha bo‘lgan son yuboring.")
        return
    data = await state.get_data()
    space = await create_space(data["name_uz"], data["name_ru"], capacity)
    await state.clear()
    await message.answer(f"✅ {html.escape(space.localized_name('uz'))} qo‘shildi. Sig‘imi: {capacity} kishi.", parse_mode="HTML", reply_markup=back_keyboard())
