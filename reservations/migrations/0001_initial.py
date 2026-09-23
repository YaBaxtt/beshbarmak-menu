import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("menu", "0002_restaurantsettings_reservations"),
    ]
    operations = [
        migrations.CreateModel(
            name="DiningSpace",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160, verbose_name="Название")),
                ("description", models.TextField(blank=True, verbose_name="Описание")),
                ("image", models.ImageField(blank=True, upload_to="spaces/%Y/%m/", verbose_name="Фото")),
                ("space_type", models.CharField(choices=[("HALL", "Зал"), ("PRIVATE_ROOM", "Отдельная комната"), ("TERRACE", "Терраса"), ("VIP", "VIP-пространство"), ("OTHER", "Другое")], default="HALL", max_length=20, verbose_name="Тип")),
                ("capacity_min", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Минимум гостей")),
                ("capacity_max", models.PositiveSmallIntegerField(verbose_name="Максимум гостей")),
                ("is_exclusive", models.BooleanField(default=False, help_text="Одновременно может быть только одна подтверждённая бронь.", verbose_name="Эксклюзивное бронирование")),
                ("is_active", models.BooleanField(default=True, verbose_name="Показывать")),
                ("is_bookable", models.BooleanField(default=True, verbose_name="Можно бронировать")),
                ("is_temporarily_unavailable", models.BooleanField(default=False, verbose_name="Временно недоступно")),
                ("hide_when_unavailable", models.BooleanField(default=False, verbose_name="Скрывать при недоступности")),
                ("unavailable_reason", models.CharField(blank=True, max_length=240, verbose_name="Причина недоступности")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="Порядок")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Зал или комната", "verbose_name_plural": "Залы и комнаты", "ordering": ("sort_order", "id")},
        ),
        migrations.CreateModel(
            name="RestaurantClosure",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(verbose_name="Дата")),
                ("reason", models.CharField(max_length=240, verbose_name="Причина")),
                ("full_day", models.BooleanField(default=True, verbose_name="Весь день")),
                ("from_time", models.TimeField(blank=True, null=True, verbose_name="С")),
                ("to_time", models.TimeField(blank=True, null=True, verbose_name="До")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "Закрытая дата", "verbose_name_plural": "Закрытые даты", "ordering": ("date", "from_time")},
        ),
        migrations.CreateModel(
            name="WorkingHours",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("day_of_week", models.PositiveSmallIntegerField(choices=[(0, "Понедельник"), (1, "Вторник"), (2, "Среда"), (3, "Четверг"), (4, "Пятница"), (5, "Суббота"), (6, "Воскресенье")], unique=True, verbose_name="День недели")),
                ("open_time", models.TimeField(default="11:00", verbose_name="Открытие")),
                ("close_time", models.TimeField(default="23:00", verbose_name="Закрытие")),
                ("is_closed", models.BooleanField(default=False, verbose_name="Выходной")),
            ],
            options={"verbose_name": "Рабочие часы", "verbose_name_plural": "Рабочие часы", "ordering": ("day_of_week",)},
        ),
        migrations.CreateModel(
            name="Reservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_number", models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name="Номер")),
                ("public_token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="Публичный токен")),
                ("customer_name", models.CharField(max_length=120, verbose_name="Имя")),
                ("phone", models.CharField(max_length=40, verbose_name="Телефон")),
                ("date", models.DateField(verbose_name="Дата")),
                ("time", models.TimeField(verbose_name="Время")),
                ("guests_count", models.PositiveSmallIntegerField(verbose_name="Гостей")),
                ("occasion", models.CharField(blank=True, choices=[("REGULAR", "Обычный визит"), ("BIRTHDAY", "День рождения"), ("FAMILY", "Семейное мероприятие"), ("BUSINESS", "Деловая встреча"), ("OTHER", "Другое")], max_length=20, verbose_name="Повод")),
                ("customer_comment", models.TextField(blank=True, max_length=1000, verbose_name="Комментарий гостя")),
                ("manager_comment", models.TextField(blank=True, max_length=1000, verbose_name="Комментарий менеджера")),
                ("status", models.CharField(choices=[("PENDING", "Ожидает подтверждения"), ("ACCEPTED", "Подтверждено"), ("CHANGE_PROPOSED", "Предложено другое время"), ("REJECTED", "Отклонено"), ("CANCELLED", "Отменено"), ("COMPLETED", "Завершено"), ("NO_SHOW", "Гость не пришёл")], db_index=True, default="PENDING", max_length=24, verbose_name="Статус")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("rejected_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("proposed_date", models.DateField(blank=True, null=True, verbose_name="Предложенная дата")),
                ("proposed_time", models.TimeField(blank=True, null=True, verbose_name="Предложенное время")),
                ("rejection_reason", models.CharField(blank=True, max_length=500, verbose_name="Причина отказа")),
                ("space", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reservations", to="reservations.diningspace", verbose_name="Помещение")),
            ],
            options={"verbose_name": "Бронирование", "verbose_name_plural": "Бронирования", "ordering": ("-date", "-time", "-created_at")},
        ),
        migrations.CreateModel(
            name="StaffProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("OWNER", "Владелец"), ("MANAGER", "Менеджер"), ("CONTENT_MANAGER", "Контент-менеджер")], default="MANAGER", max_length=20, verbose_name="Роль")),
                ("telegram_id", models.BigIntegerField(blank=True, null=True, unique=True, verbose_name="Telegram ID")),
                ("telegram_username", models.CharField(blank=True, max_length=80, verbose_name="Telegram username")),
                ("telegram_notifications_enabled", models.BooleanField(default=True, verbose_name="Уведомления Telegram")),
                ("is_active", models.BooleanField(default=True, verbose_name="Доступ разрешён")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="staff_profile", to=settings.AUTH_USER_MODEL, verbose_name="Пользователь")),
            ],
            options={"verbose_name": "Сотрудник", "verbose_name_plural": "Сотрудники", "ordering": ("user__first_name", "user__username")},
        ),
        migrations.CreateModel(
            name="ReservationAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("CREATED", "Создано"), ("ACCEPTED", "Подтверждено"), ("TIME_PROPOSED", "Предложено другое время"), ("PROPOSAL_ACCEPTED", "Гость принял предложение"), ("PROPOSAL_DECLINED", "Гость отклонил предложение"), ("REJECTED", "Отклонено"), ("CANCELLED", "Отменено"), ("COMPLETED", "Завершено"), ("SPACE_DISABLED", "Помещение отключено"), ("SPACE_ENABLED", "Помещение включено")], max_length=30, verbose_name="Действие")),
                ("comment", models.TextField(blank=True, verbose_name="Комментарий")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="actions", to="reservations.staffprofile", verbose_name="Сотрудник")),
                ("reservation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="actions", to="reservations.reservation", verbose_name="Бронирование")),
                ("space", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="actions", to="reservations.diningspace", verbose_name="Помещение")),
            ],
            options={"verbose_name": "История действия", "verbose_name_plural": "История действий", "ordering": ("-created_at",)},
        ),
        migrations.AddField(
            model_name="reservation", name="handled_by_staff",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="handled_reservations", to="reservations.staffprofile", verbose_name="Ответственный"),
        ),
        migrations.AddIndex(model_name="reservation", index=models.Index(fields=["space", "date", "status"], name="reservation_lookup_idx")),
    ]
