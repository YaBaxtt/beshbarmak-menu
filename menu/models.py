import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name_uz = models.CharField("Nomi (o‘zbekcha)", max_length=120)
    name_ru = models.CharField("Nomi (ruscha)", max_length=120)
    icon = models.CharField("Belgi", max_length=16, blank=True)
    slug = models.SlugField("Manzil kodi (slug)", unique=True)
    sort_order = models.PositiveSmallIntegerField("Ko‘rsatish tartibi", default=0)
    is_active = models.BooleanField("Saytda ko‘rsatilsin", default=True)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "Taom kategoriyasi"
        verbose_name_plural = "Taom kategoriyalari"

    def __str__(self):
        return self.name_uz


class Dish(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="dishes",
        verbose_name="Kategoriya",
    )
    name_uz = models.CharField("Nomi (o‘zbekcha)", max_length=160)
    name_ru = models.CharField("Nomi (ruscha)", max_length=160)
    description_uz = models.TextField("Tavsifi (o‘zbekcha)")
    description_ru = models.TextField("Tavsifi (ruscha)")
    price = models.PositiveIntegerField("Narxi, so‘m")
    weight = models.CharField("Vazni yoki porsiyasi", max_length=60, blank=True)
    is_available = models.BooleanField("Hozir mavjud", default=True)
    is_popular = models.BooleanField("Ko‘p tanlanadi", default=False)
    is_recommended = models.BooleanField("Tavsiya qilinadi", default=False)
    sort_order = models.PositiveSmallIntegerField("Ko‘rsatish tartibi", default=0)
    created_at = models.DateTimeField("Yaratilgan vaqt", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan vaqt", auto_now=True)

    class Meta:
        ordering = ("category__sort_order", "sort_order", "id")
        verbose_name = "Taom"
        verbose_name_plural = "Taomlar"

    def __str__(self):
        return self.name_uz

    @property
    def cover(self):
        images = list(self.images.all())
        return images[0] if images else None


class DishImage(models.Model):
    dish = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Taom",
    )
    image = models.ImageField("Rasm", upload_to="dishes/%Y/%m/")
    sort_order = models.PositiveSmallIntegerField("Rasm tartibi", default=0)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "Taom rasmi"
        verbose_name_plural = "Taom rasmlari"

    def __str__(self):
        return f"{self.dish} — {self.sort_order + 1}"


class DishLike(models.Model):
    dish = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name="likes",
        verbose_name="Taom",
    )
    session_key = models.CharField("Tashrifchi kaliti", max_length=40)
    created_at = models.DateTimeField("Bosilgan vaqt", auto_now_add=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(fields=("dish", "session_key"), name="one_like_per_dish_and_session"),
        )
        ordering = ("-created_at",)
        verbose_name = "Taomga yoqtirish"
        verbose_name_plural = "Taom yoqtirishlari"

    def __str__(self):
        return f"{self.dish} — ♥"


class Review(models.Model):
    class Language(models.TextChoices):
        UZBEK = "uz", "O‘zbekcha"
        RUSSIAN = "ru", "Ruscha"

    submission_token = models.UUIDField("Takrorlanmas yuborish kaliti", default=uuid.uuid4, unique=True, editable=False)
    guest_name = models.CharField("Mehmon ismi", max_length=80, blank=True)
    rating = models.PositiveSmallIntegerField(
        "Baho",
        validators=(MinValueValidator(1), MaxValueValidator(5)),
    )
    text = models.TextField("Fikr", max_length=1000)
    language = models.CharField("Fikr tili", max_length=2, choices=Language.choices, default=Language.UZBEK)
    is_published = models.BooleanField("Saytda ko‘rsatilsin", default=False)
    admin_note = models.CharField("Administrator izohi", max_length=300, blank=True)
    created_at = models.DateTimeField("Yuborilgan vaqt", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Mehmon fikri"
        verbose_name_plural = "Mehmon fikrlari"

    def __str__(self):
        name = self.guest_name or "Anonim mehmon"
        return f"{name} — {self.rating}/5"


class Promotion(models.Model):
    title_uz = models.CharField("Sarlavhasi (o‘zbekcha)", max_length=180)
    title_ru = models.CharField("Sarlavhasi (ruscha)", max_length=180)
    description_uz = models.TextField("Tavsifi (o‘zbekcha)", blank=True)
    description_ru = models.TextField("Tavsifi (ruscha)", blank=True)
    badge_uz = models.CharField("Belgisi (o‘zbekcha)", max_length=80, default="Aksiya", blank=True)
    badge_ru = models.CharField("Belgisi (ruscha)", max_length=80, default="Акция", blank=True)
    image = models.ImageField("Banner rasmi", upload_to="promotions/%Y/%m/", blank=True)
    link_url = models.CharField("Batafsil havolasi", max_length=500, blank=True)
    starts_at = models.DateTimeField("Boshlanish vaqti", blank=True, null=True)
    ends_at = models.DateTimeField("Tugash vaqti", blank=True, null=True)
    is_active = models.BooleanField("Saytda ko‘rsatilsin", default=True)
    sort_order = models.PositiveSmallIntegerField("Ko‘rsatish tartibi", default=0)
    created_at = models.DateTimeField("Yaratilgan vaqt", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan vaqt", auto_now=True)

    class Meta:
        ordering = ("sort_order", "-created_at")
        verbose_name = "Aksiya"
        verbose_name_plural = "Aksiyalar"

    def __str__(self):
        return self.title_uz

    @property
    def is_current(self):
        now = timezone.now()
        return self.is_active and (not self.starts_at or self.starts_at <= now) and (not self.ends_at or self.ends_at >= now)


class RestaurantSettings(models.Model):
    restaurant_name = models.CharField("Restoran nomi", max_length=160, default="Beshbarmak House")
    subtitle_uz = models.CharField("Taglavha (o‘zbekcha)", max_length=180, default="Milliy taomlar • Issiq • Mazali")
    subtitle_ru = models.CharField("Taglavha (ruscha)", max_length=180, default="Национальная кухня • С пылу с жару")
    about_uz = models.TextField("Restoran haqida (o‘zbekcha)", blank=True)
    about_ru = models.TextField("Restoran haqida (ruscha)", blank=True)
    phone = models.CharField("Telefon", max_length=40, default="+998 90 123 45 67")
    working_hours_uz = models.CharField("Ish vaqti (o‘zbekcha)", max_length=120, default="Har kuni, 10:00–23:00")
    working_hours_ru = models.CharField("Ish vaqti (ruscha)", max_length=120, default="Ежедневно, 10:00–23:00")
    location_text_uz = models.CharField("Manzil (o‘zbekcha)", max_length=180, default="Yangiyo‘l")
    location_text_ru = models.CharField("Manzil (ruscha)", max_length=180, default="Янгиюль")
    location_url = models.URLField(
        "Xarita havolasi",
        max_length=1000,
        blank=True,
    )
    telegram_url = models.URLField("Telegram havolasi", blank=True)
    instagram_url = models.URLField("Instagram havolasi", blank=True)
    youtube_url = models.URLField("YouTube havolasi", blank=True, default="https://www.youtube.com/")
    hero_image = models.ImageField("Sayt muqovasi", upload_to="restaurant/", blank=True)
    logo = models.ImageField("Logotip", upload_to="restaurant/", blank=True)
    reservation_enabled = models.BooleanField("Bron qilish yoqilgan", default=True)
    minimum_advance_minutes = models.PositiveIntegerField("Tashrifgacha eng kam vaqt, daqiqa", default=60)
    maximum_days_ahead = models.PositiveSmallIntegerField("Oldindan bron qilish muddati, kun", default=30)
    default_reservation_duration_minutes = models.PositiveIntegerField("Bron davomiyligi, daqiqa", default=120)
    slot_interval_minutes = models.PositiveSmallIntegerField("Vaqt oralig‘i, daqiqa", default=30)
    minimum_guests = models.PositiveSmallIntegerField("Eng kam mehmonlar soni", default=1)
    maximum_guests = models.PositiveSmallIntegerField("Eng ko‘p mehmonlar soni", default=30)
    cancellation_limit_hours = models.PositiveSmallIntegerField("Bekor qilish chegarasi, soat", default=3)
    manager_confirmation_required = models.BooleanField("Administrator tasdig‘i kerak", default=True)

    class Meta:
        verbose_name = "Restoran sozlamalari"
        verbose_name_plural = "Restoran sozlamalari"

    def clean(self):
        if not self.pk and RestaurantSettings.objects.exists():
            raise ValidationError("Faqat bitta restoran sozlamalari yozuvi bo‘lishi mumkin.")
        if self.minimum_guests > self.maximum_guests:
            raise ValidationError({"maximum_guests": "Eng ko‘p mehmonlar soni eng kam sondan kichik bo‘lishi mumkin emas."})
        if self.slot_interval_minutes not in {15, 30, 60}:
            raise ValidationError({"slot_interval_minutes": "15, 30 yoki 60 daqiqalik oraliqni tanlang."})

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return None

    def __str__(self):
        return self.restaurant_name

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
