import hashlib
import logging
import threading
from datetime import datetime, timedelta

from django.db import close_old_connections, connection, transaction
from django.db.models import Q
from django.utils import timezone

from menu.models import RestaurantSettings

from .models import DiningSpace, Reservation, ReservationAction, RestaurantClosure, WorkingHours


logger = logging.getLogger(__name__)


def _notify_in_background(reservation_id):
    """Do not keep the guest waiting for the Telegram API response."""
    try:
        from .telegram.notifications import notify_new_reservation
    except Exception:
        logger.exception("Не удалось подготовить уведомление о бронировании")
        return

    def worker():
        close_old_connections()
        try:
            notify_new_reservation(reservation_id)
        except Exception:
            logger.exception("Не удалось отправить уведомление о бронировании")
        finally:
            close_old_connections()

    threading.Thread(target=worker, name=f"reservation-notify-{reservation_id}", daemon=True).start()


class ReservationError(Exception):
    """A safe, user-facing reservation error."""


class AvailabilityError(ReservationError):
    pass


class AlreadyProcessedError(ReservationError):
    pass


class AccessError(ReservationError):
    pass


class AvailabilityService:
    @staticmethod
    def settings():
        return RestaurantSettings.load()

    @staticmethod
    def local_datetime(date_value, time_value):
        naive = datetime.combine(date_value, time_value)
        return timezone.make_aware(naive, timezone.get_current_timezone())

    @classmethod
    def booking_interval(cls, date_value, time_value):
        start = cls.local_datetime(date_value, time_value)
        duration = cls.settings().default_reservation_duration_minutes
        return start, start + timedelta(minutes=duration)

    @classmethod
    def validate_booking_window(cls, date_value, time_value):
        restaurant = cls.settings()
        if not restaurant.reservation_enabled:
            raise AvailabilityError("Онлайн-бронирование сейчас приостановлено. Позвоните в ресторан.")
        now = timezone.localtime()
        start = cls.local_datetime(date_value, time_value)
        if start < now + timedelta(minutes=restaurant.minimum_advance_minutes):
            raise AvailabilityError(f"Бронь нужно оформить минимум за {restaurant.minimum_advance_minutes} минут.")
        if date_value > now.date() + timedelta(days=restaurant.maximum_days_ahead):
            raise AvailabilityError(f"Можно выбрать дату не дальше чем на {restaurant.maximum_days_ahead} дней вперёд.")

    @classmethod
    def validate_open(cls, date_value, time_value):
        hours = WorkingHours.objects.filter(day_of_week=date_value.weekday()).first()
        if not hours or hours.is_closed:
            raise AvailabilityError("В этот день бронирование недоступно.")
        if hours.open_time <= hours.close_time:
            if not (hours.open_time <= time_value < hours.close_time):
                raise AvailabilityError("На это время ресторан закрыт.")
        elif not (time_value >= hours.open_time or time_value < hours.close_time):
            raise AvailabilityError("На это время ресторан закрыт.")

        start, end = cls.booking_interval(date_value, time_value)
        for closure in RestaurantClosure.objects.filter(date=date_value):
            if closure.full_day:
                raise AvailabilityError("В этот день бронирование недоступно.")
            closure_start = cls.local_datetime(date_value, closure.from_time)
            closure_end = cls.local_datetime(date_value, closure.to_time)
            if start < closure_end and end > closure_start:
                raise AvailabilityError(f"На это время ресторан закрыт: {closure.reason}.")

    @classmethod
    def validate_guests(cls, guests_count):
        restaurant = cls.settings()
        if guests_count < restaurant.minimum_guests:
            raise AvailabilityError(f"Минимальное количество гостей: {restaurant.minimum_guests}.")
        if guests_count > restaurant.maximum_guests:
            raise AvailabilityError("Для большой группы свяжитесь с рестораном по телефону.")

    @classmethod
    def has_conflict(cls, space, date_value, time_value, exclude_reservation_id=None):
        if not space.is_exclusive:
            return False
        requested_start, requested_end = cls.booking_interval(date_value, time_value)
        candidates = Reservation.objects.filter(
            space=space,
            status=Reservation.Status.ACCEPTED,
            date__range=(date_value - timedelta(days=1), date_value + timedelta(days=1)),
        )
        if exclude_reservation_id:
            candidates = candidates.exclude(pk=exclude_reservation_id)
        for existing in candidates.only("id", "date", "time"):
            existing_start, existing_end = cls.booking_interval(existing.date, existing.time)
            if requested_start < existing_end and requested_end > existing_start:
                return True
        return False

    @classmethod
    def ensure_space_available(cls, space, date_value, time_value, guests_count, exclude_reservation_id=None):
        cls.validate_booking_window(date_value, time_value)
        cls.validate_open(date_value, time_value)
        cls.validate_guests(guests_count)
        if not space.is_active or not space.is_bookable:
            raise AvailabilityError("Это помещение сейчас нельзя забронировать.")
        if space.is_temporarily_unavailable:
            raise AvailabilityError(space.unavailable_reason or "Это помещение временно недоступно.")
        if space.capacity_min and guests_count < space.capacity_min:
            raise AvailabilityError(f"Это помещение рассчитано минимум на {space.capacity_min} гостей.")
        if guests_count > space.capacity_max:
            raise AvailabilityError(f"Это помещение рассчитано максимум на {space.capacity_max} гостей.")
        if cls.has_conflict(space, date_value, time_value, exclude_reservation_id):
            raise AvailabilityError("Это время уже занято. Выберите другой вариант.")

    @classmethod
    def slots_for_date(cls, date_value):
        restaurant = cls.settings()
        if not restaurant.reservation_enabled:
            return []
        hours = WorkingHours.objects.filter(day_of_week=date_value.weekday()).first()
        if not hours or hours.is_closed or RestaurantClosure.objects.filter(date=date_value, full_day=True).exists():
            return []
        today = timezone.localdate()
        if date_value < today or date_value > today + timedelta(days=restaurant.maximum_days_ahead):
            return []
        cursor = cls.local_datetime(date_value, hours.open_time)
        close_date = date_value if hours.close_time > hours.open_time else date_value + timedelta(days=1)
        closes = cls.local_datetime(close_date, hours.close_time)
        slots = []
        while cursor < closes:
            try:
                cls.validate_booking_window(cursor.date(), cursor.time().replace(tzinfo=None))
                cls.validate_open(cursor.date(), cursor.time().replace(tzinfo=None))
            except AvailabilityError:
                pass
            else:
                slots.append(cursor.strftime("%H:%M"))
            cursor += timedelta(minutes=restaurant.slot_interval_minutes)
        return slots

    @classmethod
    def spaces_for(cls, date_value, time_value, guests_count):
        spaces = DiningSpace.objects.filter(is_active=True, capacity_max__gte=guests_count).filter(
            Q(capacity_min__isnull=True) | Q(capacity_min__lte=guests_count)
        )
        result = []
        for space in spaces:
            if space.is_temporarily_unavailable and space.hide_when_unavailable:
                continue
            selectable = True
            reason = ""
            try:
                cls.ensure_space_available(space, date_value, time_value, guests_count)
            except AvailabilityError as exc:
                selectable = False
                reason = str(exc)
            result.append((space, selectable, reason))
        return result


class ReservationService:
    @staticmethod
    def _audit(reservation, action, actor=None, comment=""):
        ReservationAction.objects.create(reservation=reservation, actor=actor, action=action, comment=comment)

    @staticmethod
    def _lock_space_date(space_id, date_value):
        if connection.vendor == "postgresql":
            digest = hashlib.blake2b(f"{space_id}:{date_value.isoformat()}".encode(), digest_size=8).digest()
            key = int.from_bytes(digest, byteorder="big", signed=True)
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [key])

    @classmethod
    def create(cls, *, customer_name, phone, date, time, guests_count, space, occasion="", customer_comment="", submission_token=None):
        if submission_token:
            existing = Reservation.objects.filter(submission_token=submission_token).first()
            if existing:
                return existing
        AvailabilityService.ensure_space_available(space, date, time, guests_count)
        values = {
            "customer_name": customer_name.strip(),
            "phone": phone.strip(),
            "date": date,
            "time": time,
            "guests_count": guests_count,
            "space": space,
            "occasion": occasion,
            "customer_comment": customer_comment.strip(),
        }
        with transaction.atomic():
            if submission_token:
                reservation, created = Reservation.objects.get_or_create(
                    submission_token=submission_token,
                    defaults=values,
                )
                if not created:
                    return reservation
            else:
                reservation = Reservation.objects.create(**values)
            cls._audit(reservation, ReservationAction.Action.CREATED)
            transaction.on_commit(lambda: _notify_in_background(reservation.pk))
        return reservation

    @classmethod
    def accept(cls, reservation_id, actor=None):
        with transaction.atomic():
            reservation = Reservation.objects.select_for_update().select_related("space").get(pk=reservation_id)
            if reservation.status != Reservation.Status.PENDING:
                raise AlreadyProcessedError("Заявка уже обработана.")
            cls._lock_space_date(reservation.space_id, reservation.date)
            AvailabilityService.ensure_space_available(
                reservation.space, reservation.date, reservation.time, reservation.guests_count, reservation.pk
            )
            reservation.status = Reservation.Status.ACCEPTED
            reservation.accepted_at = timezone.now()
            reservation.handled_by_staff = actor
            reservation.save(update_fields=("status", "accepted_at", "handled_by_staff", "updated_at"))
            cls._audit(reservation, ReservationAction.Action.ACCEPTED, actor)
            return reservation

    @classmethod
    def propose(cls, reservation_id, *, proposed_date, proposed_time, comment, actor=None):
        with transaction.atomic():
            reservation = Reservation.objects.select_for_update().select_related("space").get(pk=reservation_id)
            if reservation.status != Reservation.Status.PENDING:
                raise AlreadyProcessedError("Заявка уже обработана.")
            AvailabilityService.ensure_space_available(
                reservation.space, proposed_date, proposed_time, reservation.guests_count, reservation.pk
            )
            reservation.status = Reservation.Status.CHANGE_PROPOSED
            reservation.proposed_date = proposed_date
            reservation.proposed_time = proposed_time
            reservation.manager_comment = comment.strip()
            reservation.handled_by_staff = actor
            reservation.save(update_fields=("status", "proposed_date", "proposed_time", "manager_comment", "handled_by_staff", "updated_at"))
            cls._audit(reservation, ReservationAction.Action.TIME_PROPOSED, actor, comment)
            return reservation

    @classmethod
    def reject(cls, reservation_id, *, reason, actor=None):
        with transaction.atomic():
            reservation = Reservation.objects.select_for_update().get(pk=reservation_id)
            if reservation.status not in {Reservation.Status.PENDING, Reservation.Status.CHANGE_PROPOSED}:
                raise AlreadyProcessedError("Заявка уже обработана.")
            reservation.status = Reservation.Status.REJECTED
            reservation.rejection_reason = reason.strip()
            reservation.rejected_at = timezone.now()
            reservation.handled_by_staff = actor
            reservation.save(update_fields=("status", "rejection_reason", "rejected_at", "handled_by_staff", "updated_at"))
            cls._audit(reservation, ReservationAction.Action.REJECTED, actor, reason)
            return reservation

    @classmethod
    def accept_proposal(cls, reservation):
        with transaction.atomic():
            locked = Reservation.objects.select_for_update().select_related("space").get(pk=reservation.pk)
            if locked.status != Reservation.Status.CHANGE_PROPOSED or not locked.proposed_date or not locked.proposed_time:
                raise AlreadyProcessedError("Это предложение уже недоступно.")
            cls._lock_space_date(locked.space_id, locked.proposed_date)
            AvailabilityService.ensure_space_available(
                locked.space, locked.proposed_date, locked.proposed_time, locked.guests_count, locked.pk
            )
            locked.date = locked.proposed_date
            locked.time = locked.proposed_time
            locked.status = Reservation.Status.ACCEPTED
            locked.accepted_at = timezone.now()
            locked.save(update_fields=("date", "time", "status", "accepted_at", "updated_at"))
            cls._audit(locked, ReservationAction.Action.PROPOSAL_ACCEPTED)
            return locked

    @classmethod
    def decline_proposal(cls, reservation):
        with transaction.atomic():
            locked = Reservation.objects.select_for_update().get(pk=reservation.pk)
            if locked.status != Reservation.Status.CHANGE_PROPOSED:
                raise AlreadyProcessedError("Это предложение уже недоступно.")
            locked.status = Reservation.Status.CANCELLED
            locked.cancelled_at = timezone.now()
            locked.save(update_fields=("status", "cancelled_at", "updated_at"))
            cls._audit(locked, ReservationAction.Action.PROPOSAL_DECLINED)
            return locked

    @classmethod
    def cancel_by_customer(cls, reservation):
        with transaction.atomic():
            locked = Reservation.objects.select_for_update().get(pk=reservation.pk)
            if locked.status != Reservation.Status.ACCEPTED:
                raise AlreadyProcessedError("Эту бронь уже нельзя отменить.")
            start = AvailabilityService.local_datetime(locked.date, locked.time)
            limit = AvailabilityService.settings().cancellation_limit_hours
            if timezone.localtime() > start - timedelta(hours=limit):
                raise AvailabilityError(f"Онлайн-отмена доступна не позднее чем за {limit} ч. Позвоните в ресторан.")
            locked.status = Reservation.Status.CANCELLED
            locked.cancelled_at = timezone.now()
            locked.save(update_fields=("status", "cancelled_at", "updated_at"))
            cls._audit(locked, ReservationAction.Action.CANCELLED, comment="Отменено гостем")
            return locked
