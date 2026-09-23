import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class DiningSpace(models.Model):
    class SpaceType(models.TextChoices):
        HALL = "HALL", "Зал"
        PRIVATE_ROOM = "PRIVATE_ROOM", "Отдельная комната"
        TERRACE = "TERRACE", "Терраса"
        VIP = "VIP", "VIP-пространство"
        OTHER = "OTHER", "Другое"

    name = models.CharField("Название", max_length=160)
    name_uz = models.CharField("Название на узбекском", max_length=160, blank=True)
    description = models.TextField("Описание", blank=True)
    description_uz = models.TextField("Описание на узбекском", blank=True)
    image = models.ImageField("Фото", upload_to="spaces/%Y/%m/", blank=True)
    space_type = models.CharField("Тип", max_length=20, choices=SpaceType.choices, default=SpaceType.HALL)
    capacity_min = models.PositiveSmallIntegerField("Минимум гостей", blank=True, null=True)
    capacity_max = models.PositiveSmallIntegerField("Максимум гостей")
    is_exclusive = models.BooleanField("Эксклюзивное бронирование", default=False, help_text="Одновременно может быть только одна подтверждённая бронь.")
    is_active = models.BooleanField("Показывать", default=True)
    is_bookable = models.BooleanField("Можно бронировать", default=True)
    is_temporarily_unavailable = models.BooleanField("Временно недоступно", default=False)
    hide_when_unavailable = models.BooleanField("Скрывать при недоступности", default=False)
    unavailable_reason = models.CharField("Причина недоступности", max_length=240, blank=True)
    unavailable_reason_uz = models.CharField("Причина недоступности на узбекском", max_length=240, blank=True)
    sort_order = models.PositiveSmallIntegerField("Порядок", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "Зал или комната"
        verbose_name_plural = "Залы и комнаты"

    def clean(self):
        if self.capacity_min and self.capacity_min > self.capacity_max:
            raise ValidationError({"capacity_max": "Максимум гостей не может быть меньше минимума."})
        if self.is_temporarily_unavailable and not self.unavailable_reason:
            raise ValidationError({"unavailable_reason": "Укажите понятную причину недоступности."})

    def __str__(self):
        return self.name

    def localized_name(self, language="ru"):
        return self.name_uz or self.name if language == "uz" else self.name

    def localized_description(self, language="ru"):
        return self.description_uz or self.description if language == "uz" else self.description

    def localized_unavailable_reason(self, language="ru"):
        return self.unavailable_reason_uz or self.unavailable_reason if language == "uz" else self.unavailable_reason


class ReservationOccasion(models.Model):
    code = models.SlugField("Код", max_length=30, unique=True, help_text="Латиница, цифры, дефис или подчёркивание. Например: anniversary")
    name_ru = models.CharField("Название на русском", max_length=120)
    name_uz = models.CharField("Название на узбекском", max_length=120)
    is_active = models.BooleanField("Показывать в форме", default=True)
    sort_order = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "Повод бронирования"
        verbose_name_plural = "Поводы бронирования"

    def label(self, language="ru"):
        return self.name_uz if language == "uz" else self.name_ru

    def __str__(self):
        return self.name_ru


class WorkingHours(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Понедельник"
        TUESDAY = 1, "Вторник"
        WEDNESDAY = 2, "Среда"
        THURSDAY = 3, "Четверг"
        FRIDAY = 4, "Пятница"
        SATURDAY = 5, "Суббота"
        SUNDAY = 6, "Воскресенье"

    day_of_week = models.PositiveSmallIntegerField("День недели", choices=Weekday.choices, unique=True)
    open_time = models.TimeField("Открытие", default="11:00")
    close_time = models.TimeField("Закрытие", default="23:00")
    is_closed = models.BooleanField("Выходной", default=False)

    class Meta:
        ordering = ("day_of_week",)
        verbose_name = "Рабочие часы"
        verbose_name_plural = "Рабочие часы"

    def __str__(self):
        return f"{self.get_day_of_week_display()}: {'закрыто' if self.is_closed else f'{self.open_time:%H:%M}–{self.close_time:%H:%M}'}"


class RestaurantClosure(models.Model):
    date = models.DateField("Дата")
    reason = models.CharField("Причина", max_length=240)
    full_day = models.BooleanField("Весь день", default=True)
    from_time = models.TimeField("С", blank=True, null=True)
    to_time = models.TimeField("До", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("date", "from_time")
        verbose_name = "Закрытая дата"
        verbose_name_plural = "Закрытые даты"

    def clean(self):
        if not self.full_day and (not self.from_time or not self.to_time):
            raise ValidationError("Для частичного закрытия укажите время начала и окончания.")
        if not self.full_day and self.from_time >= self.to_time:
            raise ValidationError({"to_time": "Окончание должно быть позже начала."})

    def __str__(self):
        return f"{self.date:%d.%m.%Y} — {self.reason}"


class StaffProfile(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Владелец"
        MANAGER = "MANAGER", "Менеджер"
        CONTENT_MANAGER = "CONTENT_MANAGER", "Контент-менеджер"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile", verbose_name="Пользователь")
    role = models.CharField("Роль", max_length=20, choices=Role.choices, default=Role.MANAGER)
    telegram_id = models.BigIntegerField("Telegram ID", blank=True, null=True, unique=True)
    telegram_username = models.CharField("Telegram username", max_length=80, blank=True)
    telegram_notifications_enabled = models.BooleanField("Уведомления Telegram", default=True)
    is_active = models.BooleanField("Доступ разрешён", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("user__first_name", "user__username")
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Ожидает подтверждения"
        ACCEPTED = "ACCEPTED", "Подтверждено"
        CHANGE_PROPOSED = "CHANGE_PROPOSED", "Предложено другое время"
        REJECTED = "REJECTED", "Отклонено"
        CANCELLED = "CANCELLED", "Отменено"
        COMPLETED = "COMPLETED", "Завершено"
        NO_SHOW = "NO_SHOW", "Гость не пришёл"

    class Occasion(models.TextChoices):
        REGULAR = "REGULAR", "Обычный визит"
        BIRTHDAY = "BIRTHDAY", "День рождения"
        FAMILY = "FAMILY", "Семейное мероприятие"
        BUSINESS = "BUSINESS", "Деловая встреча"
        OTHER = "OTHER", "Другое"

    public_number = models.CharField("Номер", max_length=20, unique=True, blank=True, null=True)
    public_token = models.UUIDField("Публичный токен", default=uuid.uuid4, unique=True, editable=False)
    submission_token = models.UUIDField("Ключ отправки", unique=True, blank=True, null=True, editable=False)
    customer_name = models.CharField("Имя", max_length=120)
    phone = models.CharField("Телефон", max_length=40)
    date = models.DateField("Дата")
    time = models.TimeField("Время")
    guests_count = models.PositiveSmallIntegerField("Гостей")
    space = models.ForeignKey(DiningSpace, on_delete=models.PROTECT, related_name="reservations", verbose_name="Помещение")
    occasion = models.CharField("Повод", max_length=30, blank=True)
    customer_comment = models.TextField("Комментарий гостя", max_length=1000, blank=True)
    manager_comment = models.TextField("Комментарий менеджера", max_length=1000, blank=True)
    status = models.CharField("Статус", max_length=24, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    handled_by_staff = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, related_name="handled_reservations", blank=True, null=True, verbose_name="Ответственный")
    proposed_date = models.DateField("Предложенная дата", blank=True, null=True)
    proposed_time = models.TimeField("Предложенное время", blank=True, null=True)
    rejection_reason = models.CharField("Причина отказа", max_length=500, blank=True)

    class Meta:
        ordering = ("-date", "-time", "-created_at")
        indexes = [models.Index(fields=("space", "date", "status"), name="reservation_lookup_idx")]
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.public_number:
            self.public_number = f"R-{1000 + self.pk}"
            type(self).objects.filter(pk=self.pk).update(public_number=self.public_number)

    def __str__(self):
        return self.public_number or f"Бронь {self.pk}"

    def get_occasion_label(self, language="ru"):
        if not self.occasion:
            return "Ko‘rsatilmagan" if language == "uz" else "Не указан"
        option = ReservationOccasion.objects.filter(code=self.occasion).first()
        if option:
            return option.label(language)
        legacy = dict(self.Occasion.choices).get(self.occasion, self.occasion)
        if language == "uz":
            return {
                self.Occasion.REGULAR: "Oddiy tashrif",
                self.Occasion.BIRTHDAY: "Tug‘ilgan kun",
                self.Occasion.FAMILY: "Oilaviy tadbir",
                self.Occasion.BUSINESS: "Ish uchrashuvi",
                self.Occasion.OTHER: "Boshqa",
            }.get(self.occasion, legacy)
        return legacy


class ReservationAction(models.Model):
    class Action(models.TextChoices):
        CREATED = "CREATED", "Создано"
        ACCEPTED = "ACCEPTED", "Подтверждено"
        TIME_PROPOSED = "TIME_PROPOSED", "Предложено другое время"
        PROPOSAL_ACCEPTED = "PROPOSAL_ACCEPTED", "Гость принял предложение"
        PROPOSAL_DECLINED = "PROPOSAL_DECLINED", "Гость отклонил предложение"
        REJECTED = "REJECTED", "Отклонено"
        CANCELLED = "CANCELLED", "Отменено"
        COMPLETED = "COMPLETED", "Завершено"
        SPACE_DISABLED = "SPACE_DISABLED", "Помещение отключено"
        SPACE_ENABLED = "SPACE_ENABLED", "Помещение включено"

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="actions", blank=True, null=True, verbose_name="Бронирование")
    space = models.ForeignKey(DiningSpace, on_delete=models.SET_NULL, related_name="actions", blank=True, null=True, verbose_name="Помещение")
    actor = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, related_name="actions", blank=True, null=True, verbose_name="Сотрудник")
    action = models.CharField("Действие", max_length=30, choices=Action.choices)
    comment = models.TextField("Комментарий", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "История действия"
        verbose_name_plural = "История действий"

    def __str__(self):
        return f"{self.get_action_display()} — {self.created_at:%d.%m.%Y %H:%M}"


class SiteVisitDaily(models.Model):
    date = models.DateField("Дата", unique=True)
    views = models.PositiveIntegerField("Просмотры", default=0)
    unique_visitors = models.PositiveIntegerField("Уникальные посетители", default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-date",)
        verbose_name = "Статистика сайта за день"
        verbose_name_plural = "Статистика сайта по дням"

    def __str__(self):
        return f"{self.date:%d.%m.%Y}: {self.views} просмотров"
