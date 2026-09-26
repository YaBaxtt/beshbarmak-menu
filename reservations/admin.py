from django.contrib import admin

from .models import (
    Complaint, DiningSpace, Reservation, ReservationAction, ReservationOccasion,
    RestaurantClosure, SiteVisitDaily, StaffProfile, WorkingHours,
)


class ReservationActionInline(admin.TabularInline):
    model = ReservationAction
    extra = 0
    readonly_fields = ("action", "actor", "comment", "created_at")
    can_delete = False


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("public_number", "date", "time", "customer_name", "phone", "guests_count", "space", "status", "handled_by_staff")
    list_filter = ("status", "date", "space", "occasion")
    search_fields = ("public_number", "customer_name", "phone")
    autocomplete_fields = ("space", "handled_by_staff")
    readonly_fields = ("public_number", "public_token", "created_at", "updated_at", "accepted_at", "rejected_at", "cancelled_at", "completed_at")
    date_hierarchy = "date"
    ordering = ("-date", "-time")
    list_per_page = 30
    inlines = (ReservationActionInline,)
    fieldsets = (
        ("Bron ma’lumotlari", {"fields": ("public_number", "public_token", "status", "date", "time", "guests_count", "space", "occasion")}),
        ("Mehmon", {"fields": ("customer_name", "phone", "customer_comment")}),
        ("Administrator ishi", {"fields": ("handled_by_staff", "manager_comment", "proposed_date", "proposed_time", "rejection_reason")}),
        ("Xizmat vaqtlari", {"fields": ("created_at", "updated_at", "accepted_at", "rejected_at", "cancelled_at", "completed_at"), "classes": ("collapse",)}),
    )


@admin.register(ReservationOccasion)
class ReservationOccasionAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "name_uz", "code", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name_ru", "name_uz", "code")
    ordering = ("sort_order", "id")


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("public_number", "created_at", "reason", "space", "place_details", "status", "handled_by_staff")
    list_filter = ("status", "reason", "space", "created_at")
    search_fields = ("public_number", "place_details", "description", "staff_comment")
    autocomplete_fields = ("space", "handled_by_staff")
    readonly_fields = ("public_number", "submission_token", "created_at", "updated_at", "reviewed_at", "resolved_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-pk")
    list_per_page = 30
    fieldsets = (
        ("Shikoyat", {"fields": ("public_number", "reason", "space", "place_details", "description", "status")}),
        ("Ko‘rib chiqish", {"fields": ("handled_by_staff", "staff_comment", "reviewed_at", "resolved_at")}),
        ("Xizmat ma’lumotlari", {"fields": ("submission_token", "created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(DiningSpace)
class DiningSpaceAdmin(admin.ModelAdmin):
    list_display = ("name", "space_type", "capacity_min", "capacity_max", "is_exclusive", "is_active", "is_bookable", "is_temporarily_unavailable", "sort_order")
    list_filter = ("space_type", "is_active", "is_bookable", "is_temporarily_unavailable", "is_exclusive")
    search_fields = ("name", "name_uz", "description", "description_uz", "unavailable_reason", "unavailable_reason_uz")
    list_editable = ("is_active", "is_bookable", "sort_order")
    ordering = ("sort_order", "id")


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "role", "telegram_id", "telegram_notifications_enabled", "is_active")
    list_filter = ("role", "telegram_notifications_enabled", "is_active")
    search_fields = ("user__username", "user__first_name", "user__last_name", "telegram_username", "telegram_id")
    autocomplete_fields = ("user",)

    @admin.display(description="Xodim", ordering="user__first_name")
    def display_name(self, obj):
        return str(obj)


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ("day_of_week", "open_time", "close_time", "is_closed")
    list_editable = ("open_time", "close_time", "is_closed")
    ordering = ("day_of_week",)


@admin.register(RestaurantClosure)
class RestaurantClosureAdmin(admin.ModelAdmin):
    list_display = ("date", "reason", "full_day", "from_time", "to_time")
    list_filter = ("full_day", "date")
    search_fields = ("reason",)
    ordering = ("date",)


@admin.register(ReservationAction)
class ReservationActionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "reservation", "space", "action", "actor")
    list_filter = ("action", "created_at")
    search_fields = ("reservation__public_number", "comment", "actor__user__username")
    readonly_fields = ("reservation", "space", "action", "actor", "comment", "created_at")


@admin.register(SiteVisitDaily)
class SiteVisitDailyAdmin(admin.ModelAdmin):
    list_display = ("date", "views", "unique_visitors", "updated_at")
    date_hierarchy = "date"
    readonly_fields = ("date", "views", "unique_visitors", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
