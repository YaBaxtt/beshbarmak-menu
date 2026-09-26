from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils.html import format_html

from .models import Category, Dish, DishImage, DishLike, Promotion, RestaurantSettings, Review


admin.site.site_header = "Beshbarmak House boshqaruvi"
admin.site.site_title = "Beshbarmak Admin"
admin.site.index_title = "Restoran boshqaruv markazi"

# Django'ning ichki nomlari ayrim tarjimalarda inglizcha qoladi.
get_user_model()._meta.verbose_name = "Foydalanuvchi"
get_user_model()._meta.verbose_name_plural = "Foydalanuvchilar"
Group._meta.verbose_name = "Huquqlar guruhi"
Group._meta.verbose_name_plural = "Huquqlar guruhlari"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("icon", "name_uz", "name_ru", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name_uz", "name_ru")
    prepopulated_fields = {"slug": ("name_uz",)}
    ordering = ("sort_order",)


class DishImageInline(admin.TabularInline):
    model = DishImage
    extra = 1
    fields = ("preview", "image", "sort_order")
    readonly_fields = ("preview",)

    @admin.display(description="Ko‘rinishi")
    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" width="96" height="72" style="object-fit:cover;border-radius:10px">',
                obj.image.url,
            )
        return "—"


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = (
        "cover_preview",
        "name_uz",
        "category",
        "price_display",
        "likes_display",
        "is_available",
        "is_popular",
        "is_recommended",
        "sort_order",
    )
    list_editable = ("is_available", "is_popular", "is_recommended", "sort_order")
    list_filter = ("category", "is_available", "is_popular", "is_recommended")
    search_fields = ("name_uz", "name_ru", "description_uz", "description_ru")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("category",)
    inlines = (DishImageInline,)
    actions = ("make_available", "make_unavailable")
    list_per_page = 30
    fieldsets = (
        ("Asosiy ma’lumotlar", {"fields": ("category", "name_uz", "name_ru", "price", "weight")}),
        ("Taom tavsifi", {"fields": ("description_uz", "description_ru")}),
        ("Saytda ko‘rsatish", {"fields": ("is_available", "is_popular", "is_recommended", "sort_order")}),
        ("Xizmat ma’lumotlari", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Rasm")
    def cover_preview(self, obj):
        cover = obj.images.first()
        if cover:
            return format_html(
                '<img src="{}" width="72" height="54" style="object-fit:cover;border-radius:9px">',
                cover.image.url,
            )
        return "—"

    @admin.display(description="Narx", ordering="price")
    def price_display(self, obj):
        if obj.price is None:
            return "—"
        return f"{obj.price:,}".replace(",", " ") + " so‘m"

    @admin.display(description="Yoqtirishlar")
    def likes_display(self, obj):
        return obj.likes.count()

    @admin.action(description="✅ Mavjud deb belgilash")
    def make_available(self, request, queryset):
        self.message_user(request, f"Yangilangan taomlar: {queryset.update(is_available=True)}")

    @admin.action(description="❌ Mavjud emas deb belgilash")
    def make_unavailable(self, request, queryset):
        self.message_user(request, f"Yangilangan taomlar: {queryset.update(is_available=False)}")


@admin.register(RestaurantSettings)
class RestaurantSettingsAdmin(admin.ModelAdmin):
    list_display = ("restaurant_name", "phone", "working_hours_uz", "reservation_enabled")
    search_fields = ("restaurant_name", "phone", "location_text_ru", "location_text_uz")
    readonly_fields = ()
    fieldsets = (
        ("Brend va tashqi ko‘rinish", {"fields": ("restaurant_name", "logo", "hero_image")}),
        ("Saytdagi matnlar", {"fields": ("subtitle_uz", "subtitle_ru", "about_uz", "about_ru")}),
        ("Aloqa va manzil", {"fields": ("phone", "working_hours_uz", "working_hours_ru", "location_text_uz", "location_text_ru", "location_url")}),
        ("Ijtimoiy tarmoqlar", {"fields": ("telegram_url", "instagram_url", "youtube_url"), "description": "Havolani to‘liq kiriting. Masalan: https://youtube.com/@kanal"}),
        ("Bron qilish sozlamalari", {"fields": ("reservation_enabled", "minimum_advance_minutes", "maximum_days_ahead", "default_reservation_duration_minutes", "slot_interval_minutes", "minimum_guests", "maximum_guests", "cancellation_limit_hours", "manager_confirmation_required")}),
    )

    def has_add_permission(self, request):
        return not RestaurantSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("title_uz", "title_ru", "is_active", "starts_at", "ends_at", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("title_uz", "title_ru", "description_uz", "description_ru")
    fieldsets = (
        ("Aksiya matni", {"fields": ("title_uz", "title_ru", "description_uz", "description_ru", "badge_uz", "badge_ru")}),
        ("Rasm va ko‘rsatish vaqti", {"fields": ("image", "link_url", "starts_at", "ends_at", "is_active", "sort_order")}),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("guest_display", "rating_display", "short_text", "language", "is_published", "created_at")
    list_editable = ("is_published",)
    list_filter = ("is_published", "rating", "language", "created_at")
    search_fields = ("guest_name", "text", "admin_note")
    readonly_fields = ("submission_token", "created_at")
    actions = ("publish_reviews", "hide_reviews")
    date_hierarchy = "created_at"
    list_per_page = 30
    fieldsets = (
        ("Mehmon fikri", {"fields": ("guest_name", "rating", "text", "language")}),
        ("Saytda ko‘rsatish", {"fields": ("is_published", "admin_note")}),
        ("Xizmat ma’lumotlari", {"fields": ("submission_token", "created_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Mehmon", ordering="guest_name")
    def guest_display(self, obj):
        return obj.guest_name or "Anonim mehmon"

    @admin.display(description="Baho", ordering="rating")
    def rating_display(self, obj):
        return "★" * obj.rating + "☆" * (5 - obj.rating)

    @admin.display(description="Fikr")
    def short_text(self, obj):
        return obj.text if len(obj.text) <= 80 else obj.text[:77] + "…"

    @admin.action(description="✅ Tanlangan fikrlarni saytda ko‘rsatish")
    def publish_reviews(self, request, queryset):
        self.message_user(request, f"Saytda ko‘rsatiladigan fikrlar: {queryset.update(is_published=True)}")

    @admin.action(description="⛔ Tanlangan fikrlarni saytdan yashirish")
    def hide_reviews(self, request, queryset):
        self.message_user(request, f"Saytdan yashirilgan fikrlar: {queryset.update(is_published=False)}")


@admin.register(DishLike)
class DishLikeAdmin(admin.ModelAdmin):
    list_display = ("dish", "created_at")
    list_filter = ("dish__category", "created_at")
    search_fields = ("dish__name_uz", "dish__name_ru")
    readonly_fields = ("dish", "session_key", "created_at")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
