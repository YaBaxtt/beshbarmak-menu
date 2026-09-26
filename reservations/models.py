import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class DiningSpace(models.Model):
    class SpaceType(models.TextChoices):
        HALL = "HALL", "Zal"
        PRIVATE_ROOM = "PRIVATE_ROOM", "Alohida xona"
        TERRACE = "TERRACE", "Ayvon"
        VIP = "VIP", "VIP joy"
        OTHER = "OTHER", "Boshqa"

    name = models.CharField("Nomi (ruscha)", max_length=160)
    name_uz = models.CharField("Nomi (o‘zbekcha)", max_length=160, blank=True)
    description = models.TextField("Tavsifi (ruscha)", blank=True)
    description_uz = models.TextField("Tavsifi (o‘zbekcha)", blank=True)
    image = models.ImageField("Rasm", upload_to="spaces/%Y/%m/", blank=True)
    space_type = models.CharField("Joy turi", max_length=20, choices=SpaceType.choices, default=SpaceType.HALL)
    capacity_min = models.PositiveSmallIntegerField("Eng kam mehmonlar", blank=True, null=True)
    capacity_max = models.PositiveSmallIntegerField("Eng ko‘p mehmonlar")
    is_exclusive = models.BooleanField("Faqat bitta davra uchun", default=False, help_text="Bu joyda bir vaqtda faqat bitta tasdiqlangan bron bo‘lishi mumkin.")
    is_active = models.BooleanField("Saytda ko‘rsatilsin", default=True)
    is_bookable = models.BooleanField("Bron qilish mumkin", default=True)
    is_temporarily_unavailable = models.BooleanField("Vaqtincha yopilgan", default=False)
    hide_when_unavailable = models.BooleanField("Yopilganda yashirilsin", default=False)
    unavailable_reason = models.CharField("Yopilish sababi (ruscha)", max_length=240, blank=True)
    unavailable_reason_uz = models.CharField("Yopilish sababi (o‘zbekcha)", max_length=240, blank=True)
    sort_order = models.PositiveSmallIntegerField("Ko‘rsatish tartibi", default=0)
    created_at = models.DateTimeField("Yaratilgan vaqt", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan vaqt", auto_now=True)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "Zal yoki xona"
        verbose_name_plural = "Zallar va xonalar"

    def clean(self):
        if self.capacity_min and self.capacity_min > self.capacity_max:
            raise ValidationError({"capacity_max": "Eng ko‘p mehmonlar soni eng kam sondan kichik bo‘lishi mumkin emas."})
        if self.is_temporarily_unavailable and not self.unavailable_reason:
            raise ValidationError({"unavailable_reason": "Vaqtincha yopilish sababini kiriting."})

    def __str__(self):
        return self.name_uz or self.name

    def localized_name(self, language="ru"):
        return self.name_uz or self.name if language == "uz" else self.name

    def localized_description(self, language="ru"):
        return self.description_uz or self.description if language == "uz" else self.description

    def localized_unavailable_reason(self, language="ru"):
        return self.unavailable_reason_uz or self.unavailable_reason if language == "uz" else self.unavailable_reason


class ReservationOccasion(models.Model):
    code = models.SlugField("Kod", max_length=30, unique=True, help_text="Lotin harflari, raqam, chiziqcha yoki pastki chiziq. Masalan: anniversary")
    name_ru = models.CharField("Nomi (ruscha)", max_length=120)
    name_uz = models.CharField("Nomi (o‘zbekcha)", max_length=120)
    is_active = models.BooleanField("Bron formasida ko‘rsatilsin", default=True)
    sort_order = models.PositiveSmallIntegerField("Ko‘rsatish tartibi", default=0)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "Tashrif sababi"
        verbose_name_plural = "Tashrif sabablari"

    def label(self, language="ru"):
        return self.name_uz if language == "uz" else self.name_ru

    def __str__(self):
        return self.name_uz


class WorkingHours(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Dushanba"
        TUESDAY = 1, "Seshanba"
        WEDNESDAY = 2, "Chorshanba"
        THURSDAY = 3, "Payshanba"
        FRIDAY = 4, "Juma"
        SATURDAY = 5, "Shanba"
        SUNDAY = 6, "Yakshanba"

    day_of_week = models.PositiveSmallIntegerField("Hafta kuni", choices=Weekday.choices, unique=True)
    open_time = models.TimeField("Ochilish vaqti", default="11:00")
    close_time = models.TimeField("Yopilish vaqti", default="23:00")
    is_closed = models.BooleanField("Dam olish kuni", default=False)

    class Meta:
        ordering = ("day_of_week",)
        verbose_name = "Ish vaqti"
        verbose_name_plural = "Ish vaqtlari"

    def __str__(self):
        return f"{self.get_day_of_week_display()}: {'yopiq' if self.is_closed else f'{self.open_time:%H:%M}–{self.close_time:%H:%M}'}"


class RestaurantClosure(models.Model):
    date = models.DateField("Sana")
    reason = models.CharField("Sabab", max_length=240)
    full_day = models.BooleanField("Kun bo‘yi", default=True)
    from_time = models.TimeField("Boshlanish vaqti", blank=True, null=True)
    to_time = models.TimeField("Tugash vaqti", blank=True, null=True)
    created_at = models.DateTimeField("Yaratilgan vaqt", auto_now_add=True)

    class Meta:
        ordering = ("date", "from_time")
        verbose_name = "Restoran yopiq sana"
        verbose_name_plural = "Restoran yopiq sanalari"

    def clean(self):
        if not self.full_day and (not self.from_time or not self.to_time):
            raise ValidationError("Qisman yopish uchun boshlanish va tugash vaqtini kiriting.")
        if not self.full_day and self.from_time >= self.to_time:
            raise ValidationError({"to_time": "Tugash vaqti boshlanish vaqtidan keyin bo‘lishi kerak."})

    def __str__(self):
        return f"{self.date:%d.%m.%Y} — {self.reason}"


class StaffProfile(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Restoran egasi"
        MANAGER = "MANAGER", "Administrator"
        CONTENT_MANAGER = "CONTENT_MANAGER", "Kontent boshqaruvchisi"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile", verbose_name="Foydalanuvchi")
    role = models.CharField("Vazifasi", max_length=20, choices=Role.choices, default=Role.MANAGER)
    telegram_id = models.BigIntegerField("Telegram ID", blank=True, null=True, unique=True)
    telegram_username = models.CharField("Telegram username", max_length=80, blank=True)
    telegram_notifications_enabled = models.BooleanField("Telegram bildirishnomalari", default=True)
    is_active = models.BooleanField("Kirishga ruxsat berilgan", default=True)
    created_at = models.DateTimeField("Yaratilgan vaqt", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan vaqt", auto_now=True)

    class Meta:
        ordering = ("user__first_name", "user__username")
        verbose_name = "Xodim"
        verbose_name_plural = "Xodimlar"

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Tasdiqlanishi kutilmoqda"
        ACCEPTED = "ACCEPTED", "Tasdiqlandi"
        CHANGE_PROPOSED = "CHANGE_PROPOSED", "Boshqa vaqt taklif qilindi"
        REJECTED = "REJECTED", "Rad etildi"
        CANCELLED = "CANCELLED", "Bekor qilindi"
        COMPLETED = "COMPLETED", "Yakunlandi"
        NO_SHOW = "NO_SHOW", "Mehmon kelmadi"

    class Occasion(models.TextChoices):
        REGULAR = "REGULAR", "Oddiy tashrif"
        BIRTHDAY = "BIRTHDAY", "Tug‘ilgan kun"
        FAMILY = "FAMILY", "Oilaviy tadbir"
        BUSINESS = "BUSINESS", "Ish uchrashuvi"
        OTHER = "OTHER", "Boshqa"

    public_number = models.CharField("Bron raqami", max_length=20, unique=True, blank=True, null=True)
    public_token = models.UUIDField("Ochiq kuzatuv kaliti", default=uuid.uuid4, unique=True, editable=False)
    submission_token = models.UUIDField("Yuborish kaliti", unique=True, blank=True, null=True, editable=False)
    customer_name = models.CharField("Mehmon ismi", max_length=120)
    phone = models.CharField("Telefon raqami", max_length=40)
    date = models.DateField("Tashrif sanasi")
    time = models.TimeField("Tashrif vaqti")
    guests_count = models.PositiveSmallIntegerField("Mehmonlar soni")
    space = models.ForeignKey(DiningSpace, on_delete=models.PROTECT, related_name="reservations", verbose_name="Tanlangan joy")
    occasion = models.CharField("Tashrif sababi", max_length=30, blank=True)
    customer_comment = models.TextField("Mehmon izohi", max_length=1000, blank=True)
    manager_comment = models.TextField("Administrator izohi", max_length=1000, blank=True)
    status = models.CharField("Holati", max_length=24, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField("Ariza yuborilgan vaqt", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan vaqt", auto_now=True)
    accepted_at = models.DateTimeField("Tasdiqlangan vaqt", blank=True, null=True)
    rejected_at = models.DateTimeField("Rad etilgan vaqt", blank=True, null=True)
    cancelled_at = models.DateTimeField("Bekor qilingan vaqt", blank=True, null=True)
    completed_at = models.DateTimeField("Yakunlangan vaqt", blank=True, null=True)
    handled_by_staff = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, related_name="handled_reservations", blank=True, null=True, verbose_name="Mas’ul xodim")
    proposed_date = models.DateField("Taklif qilingan sana", blank=True, null=True)
    proposed_time = models.TimeField("Taklif qilingan vaqt", blank=True, null=True)
    rejection_reason = models.CharField("Rad etish sababi", max_length=500, blank=True)

    class Meta:
        ordering = ("-date", "-time", "-created_at")
        indexes = [models.Index(fields=("space", "date", "status"), name="reservation_lookup_idx")]
        verbose_name = "Bron arizasi"
        verbose_name_plural = "Bron arizalari"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.public_number:
            self.public_number = f"R-{1000 + self.pk}"
            type(self).objects.filter(pk=self.pk).update(public_number=self.public_number)

    def __str__(self):
        return self.public_number or f"Bron {self.pk}"

    def get_occasion_label(self, language="ru"):
        if not self.occasion:
            return "Ko‘rsatilmagan" if language == "uz" else "Не указан"
        option = ReservationOccasion.objects.filter(code=self.occasion).first()
        if option:
            return option.label(language)
        legacy_uz = dict(self.Occasion.choices).get(self.occasion, self.occasion)
        if language == "uz":
            return legacy_uz
        return {
            self.Occasion.REGULAR: "Обычный визит",
            self.Occasion.BIRTHDAY: "День рождения",
            self.Occasion.FAMILY: "Семейное мероприятие",
            self.Occasion.BUSINESS: "Деловая встреча",
            self.Occasion.OTHER: "Другое",
        }.get(self.occasion, self.occasion)


class Complaint(models.Model):
    class Reason(models.TextChoices):
        CLEANLINESS = "CLEANLINESS", "Xona yoki zal toza emas"
        AIR = "AIR", "Havo dim yoki yoqimsiz"
        COLD_FOOD = "COLD_FOOD", "Taom issiq emas edi"
        TASTE = "TASTE", "Taomning ta’mi yoqmadi"
        MISSING_ITEM = "MISSING_ITEM", "Buyurtmada nimadir yetishmadi"
        SERVICE = "SERVICE", "Xizmat ko‘rsatish yoqmadi"
        SLOW_SERVICE = "SLOW_SERVICE", "Ofitsiant uzoq vaqt kelmadi"
        OTHER = "OTHER", "Boshqa sabab"

    class Status(models.TextChoices):
        NEW = "NEW", "Yangi"
        IN_REVIEW = "IN_REVIEW", "Ko‘rib chiqilmoqda"
        RESOLVED = "RESOLVED", "Hal qilindi"
        DISMISSED = "DISMISSED", "Yopildi"

    public_number = models.CharField("Shikoyat raqami", max_length=20, unique=True, blank=True, null=True)
    submission_token = models.UUIDField("Yuborish kaliti", default=uuid.uuid4, unique=True, editable=False)
    reason = models.CharField("Shikoyat sababi", max_length=30, choices=Reason.choices)
    space = models.ForeignKey(
        DiningSpace, on_delete=models.SET_NULL, related_name="complaints",
        blank=True, null=True, verbose_name="Zal yoki xona",
    )
    place_details = models.CharField("Xona, kabinka yoki stol raqami", max_length=160, blank=True)
    description = models.TextField("Nima sodir bo‘ldi", max_length=2000)
    status = models.CharField("Holati", max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    handled_by_staff = models.ForeignKey(
        StaffProfile, on_delete=models.SET_NULL, related_name="handled_complaints",
        blank=True, null=True, verbose_name="Mas’ul xodim",
    )
    staff_comment = models.TextField("Xodim izohi", max_length=1000, blank=True)
    created_at = models.DateTimeField("Yuborilgan vaqt", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan vaqt", auto_now=True)
    reviewed_at = models.DateTimeField("Ko‘rib chiqilgan vaqt", blank=True, null=True)
    resolved_at = models.DateTimeField("Yopilgan vaqt", blank=True, null=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "Mehmon shikoyati"
        verbose_name_plural = "Mehmon shikoyatlari"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.public_number:
            self.public_number = f"C-{1000 + self.pk}"
            type(self).objects.filter(pk=self.pk).update(public_number=self.public_number)

    def __str__(self):
        return self.public_number or f"Shikoyat {self.pk}"

    def localized_reason(self, language="ru"):
        labels = {
            self.Reason.CLEANLINESS: "Xona yoki zal toza emas",
            self.Reason.AIR: "Havo dim yoki yoqimsiz",
            self.Reason.COLD_FOOD: "Taom issiq emas edi",
            self.Reason.TASTE: "Taomning ta’mi yoqmadi",
            self.Reason.MISSING_ITEM: "Buyurtmada nimadir yetishmadi",
            self.Reason.SERVICE: "Xizmat ko‘rsatish yoqmadi",
            self.Reason.SLOW_SERVICE: "Ofitsiant uzoq vaqt kelmadi",
            self.Reason.OTHER: "Boshqa sabab",
        }
        if language == "uz":
            return labels.get(self.reason, self.reason)
        return {
            self.Reason.CLEANLINESS: "Грязная комната или зал",
            self.Reason.AIR: "Душно или неприятный воздух",
            self.Reason.COLD_FOOD: "Еда была недостаточно горячей",
            self.Reason.TASTE: "Не понравился вкус еды",
            self.Reason.MISSING_ITEM: "Чего-то не было в заказе",
            self.Reason.SERVICE: "Не понравилось обслуживание",
            self.Reason.SLOW_SERVICE: "Официант долго не подходил",
            self.Reason.OTHER: "Другая причина",
        }.get(self.reason, self.reason)


class ReservationAction(models.Model):
    class Action(models.TextChoices):
        CREATED = "CREATED", "Yaratildi"
        ACCEPTED = "ACCEPTED", "Tasdiqlandi"
        TIME_PROPOSED = "TIME_PROPOSED", "Boshqa vaqt taklif qilindi"
        PROPOSAL_ACCEPTED = "PROPOSAL_ACCEPTED", "Mehmon taklifni qabul qildi"
        PROPOSAL_DECLINED = "PROPOSAL_DECLINED", "Mehmon taklifni rad etdi"
        REJECTED = "REJECTED", "Rad etildi"
        CANCELLED = "CANCELLED", "Bekor qilindi"
        COMPLETED = "COMPLETED", "Yakunlandi"
        SPACE_DISABLED = "SPACE_DISABLED", "Joy vaqtincha yopildi"
        SPACE_ENABLED = "SPACE_ENABLED", "Joy ochildi"

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="actions", blank=True, null=True, verbose_name="Bron arizasi")
    space = models.ForeignKey(DiningSpace, on_delete=models.SET_NULL, related_name="actions", blank=True, null=True, verbose_name="Joy")
    actor = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, related_name="actions", blank=True, null=True, verbose_name="Xodim")
    action = models.CharField("Amal", max_length=30, choices=Action.choices)
    comment = models.TextField("Izoh", blank=True)
    created_at = models.DateTimeField("Amal vaqti", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Amallar tarixi"
        verbose_name_plural = "Amallar tarixi"

    def __str__(self):
        return f"{self.get_action_display()} — {self.created_at:%d.%m.%Y %H:%M}"


class SiteVisitDaily(models.Model):
    date = models.DateField("Sana", unique=True)
    views = models.PositiveIntegerField("Ko‘rishlar", default=0)
    unique_visitors = models.PositiveIntegerField("Noyob tashrifchilar", default=0)
    updated_at = models.DateTimeField("Yangilangan vaqt", auto_now=True)

    class Meta:
        ordering = ("-date",)
        verbose_name = "Kunlik sayt statistikasi"
        verbose_name_plural = "Kunlik sayt statistikasi"

    def __str__(self):
        return f"{self.date:%d.%m.%Y}: {self.views} ta ko‘rish"
