from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Dish, DishImage, RestaurantSettings


admin.site.site_header = "Beshbarmak House boshqaruvi"
admin.site.site_title = "Beshbarmak Admin"
admin.site.index_title = "Raqamli menyu / Цифровое меню"


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

    @admin.display(description="Ko‘rish / превью")
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
        ("Asosiy / основное", {"fields": ("category", "name_uz", "name_ru", "price", "weight")}),
        ("Tavsif / описание", {"fields": ("description_uz", "description_ru")}),
        ("Holat / статус", {"fields": ("is_available", "is_popular", "is_recommended", "sort_order")}),
        ("Sana / даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Rasm / фото")
    def cover_preview(self, obj):
        cover = obj.images.first()
        if cover:
            return format_html(
                '<img src="{}" width="72" height="54" style="object-fit:cover;border-radius:9px">',
                cover.image.url,
            )
        return "—"

    @admin.display(description="Narx / цена", ordering="price")
    def price_display(self, obj):
        return f"{obj.price:,}".replace(",", " ") + " so‘m"

    @admin.action(description="✅ Mavjud deb belgilash / В наличии")
    def make_available(self, request, queryset):
        self.message_user(request, f"Yangilandi / Обновлено: {queryset.update(is_available=True)}")

    @admin.action(description="❌ Mavjud emas / Нет в наличии")
    def make_unavailable(self, request, queryset):
        self.message_user(request, f"Yangilandi / Обновлено: {queryset.update(is_available=False)}")


@admin.register(RestaurantSettings)
class RestaurantSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Brend / бренд", {"fields": ("restaurant_name", "logo", "hero_image")}),
        ("Matnlar / тексты", {"fields": ("subtitle_uz", "subtitle_ru", "about_uz", "about_ru")}),
        ("Aloqa / контакты", {"fields": ("phone", "working_hours_uz", "working_hours_ru", "location_text_uz", "location_text_ru", "location_url")}),
        ("Ijtimoiy tarmoqlar / соцсети", {"fields": ("telegram_url", "instagram_url")}),
    )

    def has_add_permission(self, request):
        return not RestaurantSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
