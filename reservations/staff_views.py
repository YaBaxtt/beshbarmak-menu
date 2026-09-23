from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from menu.models import RestaurantSettings

from .forms import (
    ClosureForm, DiningSpaceForm, ProposalForm, RejectionForm, ReservationSettingsForm,
    RussianAuthenticationForm, StaffCreateForm, StaffUpdateForm, WorkingHoursForm,
)
from .models import DiningSpace, Reservation, ReservationAction, RestaurantClosure, SiteVisitDaily, StaffProfile, WorkingHours
from .services import AlreadyProcessedError, AvailabilityError, ReservationService


def _profile_for(user):
    if user.is_superuser:
        return None
    try:
        profile = user.staff_profile
    except StaffProfile.DoesNotExist:
        raise PermissionDenied("У вас нет доступа к панели ресторана.")
    if not profile.is_active or not user.is_active:
        raise PermissionDenied("Доступ сотрудника отключён.")
    return profile


def staff_access(*roles):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            profile = _profile_for(request.user)
            if roles and not request.user.is_superuser and profile.role not in roles:
                raise PermissionDenied("Для этого раздела недостаточно прав.")
            request.staff_profile = profile
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def staff_login(request):
    if request.user.is_authenticated:
        try:
            _profile_for(request.user)
        except PermissionDenied:
            logout(request)
        else:
            return redirect("staff:dashboard")
    form = RussianAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        try:
            _profile_for(user)
        except PermissionDenied:
            form.add_error(None, "У вас нет доступа к панели ресторана.")
        else:
            login(request, user)
            return redirect(request.GET.get("next") or "staff:dashboard")
    return render(request, "staff/login.html", {"form": form})


@require_POST
def staff_logout(request):
    logout(request)
    return redirect("staff:login")


@staff_access(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER, StaffProfile.Role.CONTENT_MANAGER)
def dashboard(request):
    if request.staff_profile and request.staff_profile.role == StaffProfile.Role.CONTENT_MANAGER:
        return render(request, "staff/content_dashboard.html")
    today = timezone.localdate()
    today_qs = Reservation.objects.filter(date=today)
    metrics = {
        "pending": Reservation.objects.filter(status=Reservation.Status.PENDING).count(),
        "accepted": today_qs.filter(status=Reservation.Status.ACCEPTED).count(),
        "guests": today_qs.filter(status=Reservation.Status.ACCEPTED).aggregate(total=Sum("guests_count"))["total"] or 0,
        "rejected": today_qs.filter(status=Reservation.Status.REJECTED).count(),
    }
    upcoming = Reservation.objects.select_related("space").filter(date=today).order_by("time")[:8]
    return render(request, "staff/dashboard.html", {"metrics": metrics, "reservations": upcoming})


@staff_access(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER)
def reservation_list(request):
    tab = request.GET.get("tab", "today")
    query = request.GET.get("q", "").strip()
    today = timezone.localdate()
    queryset = Reservation.objects.select_related("space", "handled_by_staff__user")
    filters = {
        "today": Q(date=today), "new": Q(status=Reservation.Status.PENDING),
        "accepted": Q(status=Reservation.Status.ACCEPTED),
        "waiting": Q(status=Reservation.Status.CHANGE_PROPOSED),
        "rejected": Q(status=Reservation.Status.REJECTED), "all": Q(),
    }
    queryset = queryset.filter(filters.get(tab, filters["today"]))
    if query:
        queryset = queryset.filter(Q(public_number__icontains=query) | Q(phone__icontains=query) | Q(customer_name__icontains=query))
    page = Paginator(queryset, 20).get_page(request.GET.get("page"))
    return render(request, "staff/reservation_list.html", {"page": page, "active_tab": tab, "query": query})


@staff_access(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER)
def reservation_detail(request, pk):
    reservation = get_object_or_404(Reservation.objects.select_related("space", "handled_by_staff__user").prefetch_related("actions__actor__user"), pk=pk)
    return render(request, "staff/reservation_detail.html", {"reservation": reservation})


@staff_access(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER)
def reservation_accept(request, pk):
    reservation = get_object_or_404(Reservation.objects.select_related("space"), pk=pk)
    if request.method == "POST":
        try:
            ReservationService.accept(pk, request.staff_profile)
        except (AvailabilityError, AlreadyProcessedError) as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Бронирование подтверждено.")
        return redirect("staff:reservation_detail", pk=pk)
    return render(request, "staff/confirm_accept.html", {"reservation": reservation})


@staff_access(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER)
def reservation_propose(request, pk):
    reservation = get_object_or_404(Reservation.objects.select_related("space"), pk=pk)
    initial = {"proposed_date": reservation.date}
    form = ProposalForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            ReservationService.propose(pk, actor=request.staff_profile, **form.cleaned_data)
        except (AvailabilityError, AlreadyProcessedError) as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Новое время отправлено гостю.")
            return redirect("staff:reservation_detail", pk=pk)
    return render(request, "staff/action_form.html", {"reservation": reservation, "form": form, "title": "Предложить другое время", "submit_label": "Отправить предложение"})


@staff_access(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER)
def reservation_reject(request, pk):
    reservation = get_object_or_404(Reservation.objects.select_related("space"), pk=pk)
    form = RejectionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            ReservationService.reject(pk, reason=form.final_reason(), actor=request.staff_profile)
        except AlreadyProcessedError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Заявка отклонена. Причина сохранена.")
            return redirect("staff:reservation_detail", pk=pk)
    return render(request, "staff/action_form.html", {"reservation": reservation, "form": form, "title": "Отклонить заявку", "submit_label": "Подтвердить отказ", "danger": True})


@staff_access(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER)
def space_list(request):
    return render(request, "staff/space_list.html", {"spaces": DiningSpace.objects.all()})


@staff_access(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER)
def space_edit(request, pk=None):
    space = get_object_or_404(DiningSpace, pk=pk) if pk else DiningSpace()
    old_available = space.is_active and space.is_bookable and not space.is_temporarily_unavailable if pk else False
    form = DiningSpaceForm(request.POST or None, request.FILES or None, instance=space)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        new_available = saved.is_active and saved.is_bookable and not saved.is_temporarily_unavailable
        if old_available != new_available:
            ReservationAction.objects.create(
                space=saved, actor=request.staff_profile,
                action=ReservationAction.Action.SPACE_ENABLED if new_available else ReservationAction.Action.SPACE_DISABLED,
                comment=saved.unavailable_reason,
            )
        messages.success(request, "Изменения сохранены.")
        return redirect("staff:spaces")
    return render(request, "staff/generic_form.html", {"form": form, "title": "Изменить помещение" if pk else "Добавить помещение", "multipart": True})


@require_POST
@staff_access(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER)
def space_deactivate(request, pk):
    space = get_object_or_404(DiningSpace, pk=pk)
    space.is_active = False
    space.save(update_fields=("is_active", "updated_at"))
    ReservationAction.objects.create(space=space, actor=request.staff_profile, action=ReservationAction.Action.SPACE_DISABLED, comment="Скрыто сотрудником")
    messages.success(request, "Помещение скрыто. История бронирований сохранена.")
    return redirect("staff:spaces")


@staff_access(StaffProfile.Role.OWNER)
def reservation_settings(request):
    restaurant = RestaurantSettings.load()
    for day in range(7):
        WorkingHours.objects.get_or_create(day_of_week=day)
    hours = list(WorkingHours.objects.all())
    settings_form = ReservationSettingsForm(request.POST or None, instance=restaurant, prefix="settings")
    hour_forms = [WorkingHoursForm(request.POST or None, instance=item, prefix=f"day-{item.day_of_week}") for item in hours]
    if request.method == "POST" and settings_form.is_valid() and all(form.is_valid() for form in hour_forms):
        restaurant = settings_form.save()
        for form in hour_forms:
            form.save()
        saved_hours = list(WorkingHours.objects.order_by("day_of_week"))
        open_hours = [item for item in saved_hours if not item.is_closed]
        if len(open_hours) == 7 and len({(item.open_time, item.close_time) for item in open_hours}) == 1:
            first = open_hours[0]
            restaurant.working_hours_ru = f"Ежедневно, {first.open_time:%H:%M}–{first.close_time:%H:%M}"
            restaurant.working_hours_uz = f"Har kuni, {first.open_time:%H:%M}–{first.close_time:%H:%M}"
        else:
            restaurant.working_hours_ru = "График по дням — в разделе «Контакты»"
            restaurant.working_hours_uz = "Kunlik jadval — «Kontaktlar» bo‘limida"
        restaurant.save(update_fields=("working_hours_ru", "working_hours_uz"))
        messages.success(request, "Настройки бронирования сохранены.")
        return redirect("staff:settings")
    closures = RestaurantClosure.objects.filter(date__gte=timezone.localdate())[:30]
    return render(request, "staff/settings.html", {"settings_form": settings_form, "hour_forms": hour_forms, "closures": closures})


@staff_access(StaffProfile.Role.OWNER)
def closure_add(request):
    form = ClosureForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Закрытая дата добавлена.")
        return redirect("staff:settings")
    return render(request, "staff/generic_form.html", {"form": form, "title": "Добавить закрытую дату"})


@require_POST
@staff_access(StaffProfile.Role.OWNER)
def closure_delete(request, pk):
    get_object_or_404(RestaurantClosure, pk=pk).delete()
    messages.success(request, "Закрытая дата удалена.")
    return redirect("staff:settings")


@staff_access(StaffProfile.Role.OWNER)
def staff_list(request):
    return render(request, "staff/staff_list.html", {"staff_members": StaffProfile.objects.select_related("user")})


@staff_access(StaffProfile.Role.OWNER)
def staff_create(request):
    form = StaffCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Сотрудник добавлен.")
        return redirect("staff:members")
    return render(request, "staff/generic_form.html", {"form": form, "title": "Добавить сотрудника"})


@staff_access(StaffProfile.Role.OWNER)
def staff_edit(request, pk):
    profile = get_object_or_404(StaffProfile.objects.select_related("user"), pk=pk)
    form = StaffUpdateForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Данные сотрудника сохранены.")
        return redirect("staff:members")
    return render(request, "staff/generic_form.html", {"form": form, "title": "Изменить сотрудника"})


@staff_access(StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER)
def analytics(request):
    try:
        days = int(request.GET.get("days", "7"))
    except ValueError:
        days = 7
    days = days if days in {1, 7, 30, 90} else 7
    end = timezone.localdate()
    start = end - timedelta(days=days - 1)
    queryset = Reservation.objects.filter(date__range=(start, end))
    visit_queryset = SiteVisitDaily.objects.filter(date__range=(start, end))
    visit_totals = visit_queryset.aggregate(views=Sum("views"), visitors=Sum("unique_visitors"))
    status_counts = {row["status"]: row["count"] for row in queryset.values("status").annotate(count=Count("id"))}
    processed = sum(status_counts.get(status, 0) for status in (Reservation.Status.ACCEPTED, Reservation.Status.REJECTED, Reservation.Status.COMPLETED, Reservation.Status.NO_SHOW))
    accepted_count = status_counts.get(Reservation.Status.ACCEPTED, 0) + status_counts.get(Reservation.Status.COMPLETED, 0) + status_counts.get(Reservation.Status.NO_SHOW, 0)
    daily_raw = {row["date"]: row for row in queryset.values("date").annotate(reservations=Count("id"), guests=Sum("guests_count"))}
    visit_raw = {row["date"]: row for row in visit_queryset.values("date", "views", "unique_visitors")}
    daily = []
    max_reservations = max([item["reservations"] for item in daily_raw.values()] or [1])
    max_guests = max([item["guests"] or 0 for item in daily_raw.values()] or [1])
    max_views = max([item["views"] for item in visit_raw.values()] or [1])
    for offset in range(days):
        day = start + timedelta(days=offset)
        row = daily_raw.get(day, {"reservations": 0, "guests": 0})
        visits = visit_raw.get(day, {"views": 0, "unique_visitors": 0})
        daily.append({"date": day, "reservations": row["reservations"], "guests": row["guests"] or 0,
                      "views": visits["views"], "visitors": visits["unique_visitors"],
                      "reservations_pct": round(row["reservations"] / max_reservations * 100),
                      "guests_pct": round((row["guests"] or 0) / max_guests * 100),
                      "views_pct": round(visits["views"] / max_views * 100)})
    weekday_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    popular_days = sorted(((weekday_names[index], queryset.filter(date__week_day=((index + 1) % 7) + 1).count()) for index in range(7)), key=lambda x: x[1], reverse=True)[:3]
    context = {
        "days": days, "total": queryset.count(), "accepted": accepted_count,
        "site_views": visit_totals["views"] or 0,
        "unique_visitors": visit_totals["visitors"] or 0,
        "pending": status_counts.get(Reservation.Status.PENDING, 0),
        "processed": processed,
        "response_rate": round(processed / queryset.count() * 100) if queryset.count() else 0,
        "view_to_request_rate": round(queryset.count() / (visit_totals["views"] or 0) * 100, 1) if visit_totals["views"] else 0,
        "rejected": status_counts.get(Reservation.Status.REJECTED, 0),
        "guests": queryset.filter(status__in=(Reservation.Status.ACCEPTED, Reservation.Status.COMPLETED)).aggregate(total=Sum("guests_count"))["total"] or 0,
        "acceptance_rate": round(accepted_count / processed * 100) if processed else 0,
        "average_group": queryset.filter(status__in=(Reservation.Status.ACCEPTED, Reservation.Status.COMPLETED)).aggregate(value=Avg("guests_count"))["value"] or 0,
        "no_show_rate": round(status_counts.get(Reservation.Status.NO_SHOW, 0) / accepted_count * 100) if accepted_count else 0,
        "status_counts": [(Reservation.Status(value).label, status_counts.get(value, 0)) for value in Reservation.Status.values],
        "daily": daily,
        "popular_times": list(queryset.values("time").annotate(count=Count("id")).order_by("-count", "time")[:5]),
        "popular_days": popular_days,
        "popular_spaces": list(queryset.values("space__name").annotate(count=Count("id")).order_by("-count")[:5]),
        "rejection_reasons": list(queryset.filter(status=Reservation.Status.REJECTED).exclude(rejection_reason="").values("rejection_reason").annotate(count=Count("id")).order_by("-count")[:5]),
    }
    return render(request, "staff/analytics.html", context)
