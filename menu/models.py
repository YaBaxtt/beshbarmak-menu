from django.core.exceptions import ValidationError
from django.db import models


class Category(models.Model):
    name_uz = models.CharField("Nomi (UZ)", max_length=120)
    name_ru = models.CharField("Название (RU)", max_length=120)
    icon = models.CharField("Belgi / иконка", max_length=16, blank=True)
    slug = models.SlugField(unique=True)
    sort_order = models.PositiveSmallIntegerField("Tartib / порядок", default=0)
    is_active = models.BooleanField("Faol / активно", default=True)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "Kategoriya / категория"
        verbose_name_plural = "Kategoriyalar / категории"

    def __str__(self):
        return self.name_uz


class Dish(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="dishes",
        verbose_name="Kategoriya / категория",
    )
    name_uz = models.CharField("Nomi (UZ)", max_length=160)
    name_ru = models.CharField("Название (RU)", max_length=160)
    description_uz = models.TextField("Tavsif (UZ)")
    description_ru = models.TextField("Описание (RU)")
    price = models.PositiveIntegerField("Narx, so‘m / цена, сум")
    weight = models.CharField("Vazn yoki porsiya / вес или порция", max_length=60, blank=True)
    is_available = models.BooleanField("Mavjud / в наличии", default=True)
    is_popular = models.BooleanField("Ko‘p tanlanadi / популярное", default=False)
    is_recommended = models.BooleanField("Tavsiya / рекомендуем", default=False)
    sort_order = models.PositiveSmallIntegerField("Tartib / порядок", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("category__sort_order", "sort_order", "id")
        verbose_name = "Taom / блюдо"
        verbose_name_plural = "Taomlar / блюда"

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
        verbose_name="Taom / блюдо",
    )
    image = models.ImageField("Rasm / фото", upload_to="dishes/%Y/%m/")
    sort_order = models.PositiveSmallIntegerField("Tartib / порядок", default=0)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "Taom rasmi / фото блюда"
        verbose_name_plural = "Taom rasmlari / фото блюд"

    def __str__(self):
        return f"{self.dish} — {self.sort_order + 1}"


class RestaurantSettings(models.Model):
    restaurant_name = models.CharField("Restoran nomi / название", max_length=160, default="Beshbarmak House")
    subtitle_uz = models.CharField("Taglavha (UZ)", max_length=180, default="Milliy taomlar • Issiq • Mazali")
    subtitle_ru = models.CharField("Подзаголовок (RU)", max_length=180, default="Национальная кухня • С пылу с жару")
    about_uz = models.TextField("Qisqa matn (UZ)", blank=True)
    about_ru = models.TextField("Короткий текст (RU)", blank=True)
    phone = models.CharField("Telefon", max_length=40, default="+998 90 123 45 67")
    working_hours_uz = models.CharField("Ish vaqti (UZ)", max_length=120, default="Har kuni, 10:00–23:00")
    working_hours_ru = models.CharField("Время работы (RU)", max_length=120, default="Ежедневно, 10:00–23:00")
    location_text_uz = models.CharField("Manzil (UZ)", max_length=180, default="Yangiyo‘l")
    location_text_ru = models.CharField("Адрес (RU)", max_length=180, default="Янгиюль")
    location_url = models.URLField("Xarita havolasi / ссылка на карту", blank=True)
    telegram_url = models.URLField("Telegram", blank=True)
    instagram_url = models.URLField("Instagram", blank=True)
    hero_image = models.ImageField("Asosiy rasm / фото обложки", upload_to="restaurant/", blank=True)
    logo = models.ImageField("Logotip / логотип", upload_to="restaurant/", blank=True)

    class Meta:
        verbose_name = "Restoran sozlamalari / настройки ресторана"
        verbose_name_plural = "Restoran sozlamalari / настройки ресторана"

    def clean(self):
        if not self.pk and RestaurantSettings.objects.exists():
            raise ValidationError("Faqat bitta sozlamalar yozuvi mumkin / Допустима только одна запись.")

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
