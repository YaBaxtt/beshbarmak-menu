import uuid
from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from menu.models import RestaurantSettings

from .forms import ReservationForm
from .i18n import (
    SPACE_TYPES_UZ, STATUS_LABELS, add_language, language_from_request,
    localize_error, text_for,
)
from .models import Reservation
from .services import AlreadyProcessedError, AvailabilityError, AvailabilityService, ReservationService


def reservation_start(request):
    restaurant = RestaurantSettings.load()
    language = language_from_request(request)
    raw_submission_token = request.POST.get("submission_token", "") if request.method == "POST" else ""
    try:
        submission_token = uuid.UUID(raw_submission_token) if raw_submission_token else uuid.uuid4()
    except (ValueError, AttributeError):
        submission_token = uuid.uuid4()
    form = ReservationForm(request.POST or None, language=language)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            reservation = ReservationService.create(
                customer_name=data["customer_name"], phone=data["phone"], date=data["date"], time=data["time"],
                guests_count=data["guests_count"], space=data["space"], occasion=data["occasion"],
                customer_comment=data["customer_comment"], submission_token=submission_token,
            )
        except AvailabilityError as exc:
            form.add_error(None, localize_error(str(exc), language))
        else:
            response = redirect(add_language(reverse("reservations:status", kwargs={"token": reservation.public_token}), language))
            response.set_cookie("site_language", language, max_age=31536000, samesite="Lax")
            return response
    response = render(request, "reservations/start.html", {
        "form": form, "restaurant": restaurant, "language": language,
        "t": text_for(language), "submission_token": submission_token,
    })
    response.set_cookie("site_language", language, max_age=31536000, samesite="Lax")
    return response


@require_GET
def available_slots(request):
    language = language_from_request(request)
    try:
        date_value = datetime.strptime(request.GET.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        error = "To‘g‘ri sanani tanlang." if language == "uz" else "Выберите корректную дату."
        return JsonResponse({"error": error, "slots": []}, status=400)
    slots = AvailabilityService.slots_for_date(date_value)
    unavailable = "Bu kunda bron qilish imkoni yo‘q." if language == "uz" else "В этот день бронирование недоступно."
    return JsonResponse({"slots": slots, "message": "" if slots else unavailable})


@require_GET
def available_spaces(request):
    language = language_from_request(request)
    try:
        date_value = datetime.strptime(request.GET.get("date", ""), "%Y-%m-%d").date()
        time_value = datetime.strptime(request.GET.get("time", ""), "%H:%M").time()
        guests = int(request.GET.get("guests", "0"))
        AvailabilityService.validate_booking_window(date_value, time_value)
        AvailabilityService.validate_open(date_value, time_value)
        AvailabilityService.validate_guests(guests)
    except (ValueError, AvailabilityError) as exc:
        fallback = "Sana, vaqt va mehmonlar sonini tekshiring." if language == "uz" else "Проверьте дату, время и количество гостей."
        return JsonResponse({"error": localize_error(str(exc), language) if str(exc) else fallback, "spaces": []}, status=400)
    spaces = [
        {
            "id": space.pk,
            "name": space.localized_name(language),
            "type": SPACE_TYPES_UZ.get(space.space_type, space.get_space_type_display()) if language == "uz" else space.get_space_type_display(),
            "description": space.localized_description(language),
            "capacity_min": space.capacity_min,
            "capacity_max": space.capacity_max,
            "image": space.image.url if space.image else "",
            "selectable": selectable,
            "reason": space.localized_unavailable_reason(language) if reason == space.unavailable_reason else localize_error(reason, language),
        }
        for space, selectable, reason in AvailabilityService.spaces_for(date_value, time_value, guests)
    ]
    no_spaces = "Bu vaqtga mos joy topilmadi." if language == "uz" else "На это время подходящих мест не найдено."
    return JsonResponse({"spaces": spaces, "message": "" if any(item["selectable"] for item in spaces) else no_spaces})


def reservation_status(request, token):
    reservation = get_object_or_404(Reservation.objects.select_related("space"), public_token=token)
    restaurant = RestaurantSettings.load()
    language = language_from_request(request)
    response = render(request, "reservations/status.html", {
        "reservation": reservation, "restaurant": restaurant, "language": language,
        "t": text_for(language), "status_label": STATUS_LABELS[language].get(reservation.status, reservation.get_status_display()),
    })
    response.set_cookie("site_language", language, max_age=31536000, samesite="Lax")
    return response


@require_GET
def reservation_status_data(request, token):
    reservation = get_object_or_404(Reservation.objects.select_related("space"), public_token=token)
    language = language_from_request(request)
    return JsonResponse({
        "status": reservation.status,
        "status_label": STATUS_LABELS[language].get(reservation.status, reservation.get_status_display()),
        "date": reservation.date.strftime("%d.%m.%Y"),
        "time": reservation.time.strftime("%H:%M"),
        "proposed_date": reservation.proposed_date.strftime("%d.%m.%Y") if reservation.proposed_date else "",
        "proposed_time": reservation.proposed_time.strftime("%H:%M") if reservation.proposed_time else "",
        "manager_comment": reservation.manager_comment,
        "rejection_reason": reservation.rejection_reason,
        "updated_at": reservation.updated_at.isoformat(),
        "html_url": reverse("reservations:status", kwargs={"token": token}),
    })


@require_POST
def accept_proposal(request, token):
    language = language_from_request(request)
    reservation = get_object_or_404(Reservation, public_token=token)
    try:
        ReservationService.accept_proposal(reservation)
    except (AvailabilityError, AlreadyProcessedError) as exc:
        url = add_language(reverse("reservations:status", kwargs={"token": token}), language)
        return redirect(f"{url}&error={localize_error(str(exc), language)}")
    return redirect(add_language(reverse("reservations:status", kwargs={"token": token}), language))


@require_POST
def decline_proposal(request, token):
    language = language_from_request(request)
    reservation = get_object_or_404(Reservation, public_token=token)
    try:
        ReservationService.decline_proposal(reservation)
    except AlreadyProcessedError as exc:
        url = add_language(reverse("reservations:status", kwargs={"token": token}), language)
        return redirect(f"{url}&error={localize_error(str(exc), language)}")
    return redirect(add_language(reverse("reservations:status", kwargs={"token": token}), language))


@require_POST
def cancel_reservation(request, token):
    language = language_from_request(request)
    reservation = get_object_or_404(Reservation, public_token=token)
    try:
        ReservationService.cancel_by_customer(reservation)
    except (AvailabilityError, AlreadyProcessedError) as exc:
        url = add_language(reverse("reservations:status", kwargs={"token": token}), language)
        return redirect(f"{url}&error={localize_error(str(exc), language)}")
    return redirect(add_language(reverse("reservations:status", kwargs={"token": token}), language))
