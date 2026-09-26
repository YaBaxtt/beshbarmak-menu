import uuid

import django.db.models.deletion
from django.db import migrations, models


def configure_spaces(apps, schema_editor):
    DiningSpace = apps.get_model("reservations", "DiningSpace")
    spaces = (
        {
            "aliases": ("Asosiy zal", "Stol-stulli zal"),
            "name": "Зал со столами и стульями",
            "name_uz": "Stol-stulli zal",
            "description": "Удобный зал со столами и стульями для компании от 2 до 8 человек.",
            "description_uz": "2 dan 8 kishigacha bo‘lgan davra uchun stol-stulli qulay zal.",
            "space_type": "HALL", "capacity_min": 2, "capacity_max": 8,
            "is_exclusive": False, "sort_order": 10,
        },
        {
            "aliases": ("Katta zal",),
            "name": "Большой зал",
            "name_uz": "Katta zal",
            "description": "Большой зал для компании от 8 до 18 человек.",
            "description_uz": "8 dan 18 kishigacha bo‘lgan katta davra uchun zal.",
            "space_type": "HALL", "capacity_min": 8, "capacity_max": 18,
            "is_exclusive": False, "sort_order": 20,
        },
        {
            "aliases": ("Oilaviy xona", "Oddiy xona"),
            "name": "Обычная комната",
            "name_uz": "Oddiy xona",
            "description": "Небольшая отдельная комната для 1–2 гостей.",
            "description_uz": "1–2 mehmon uchun kichik va alohida xona.",
            "space_type": "PRIVATE_ROOM", "capacity_min": 1, "capacity_max": 2,
            "is_exclusive": True, "sort_order": 30,
        },
        {
            "aliases": ("VIP xona", "Tapchan"),
            "name": "Тапчан",
            "name_uz": "Tapchan",
            "description": "Отдельный тапчан для компании от 6 до 20 человек.",
            "description_uz": "6 dan 20 kishigacha bo‘lgan davra uchun alohida tapchan.",
            "space_type": "PRIVATE_ROOM", "capacity_min": 6, "capacity_max": 20,
            "is_exclusive": True, "sort_order": 40,
        },
    )
    for config in spaces:
        aliases = config["aliases"]
        item = DiningSpace.objects.filter(name_uz__in=aliases).order_by("pk").first()
        defaults = {
            **{key: value for key, value in config.items() if key != "aliases"},
            "is_active": True,
            "is_bookable": True,
            "is_temporarily_unavailable": False,
            "hide_when_unavailable": False,
            "unavailable_reason": "",
            "unavailable_reason_uz": "",
        }
        if item:
            for field, value in defaults.items():
                setattr(item, field, value)
            item.save()
        else:
            DiningSpace.objects.create(**defaults)


class Migration(migrations.Migration):

    dependencies = [
        ("reservations", "0004_reservation_submission_token"),
    ]

    operations = [
        migrations.CreateModel(
            name="Complaint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_number", models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name="Номер")),
                ("submission_token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="Ключ отправки")),
                ("reason", models.CharField(choices=[("CLEANLINESS", "Грязная комната или зал"), ("AIR", "Душно или неприятный воздух"), ("COLD_FOOD", "Еда была недостаточно горячей"), ("TASTE", "Не понравился вкус еды"), ("MISSING_ITEM", "Чего-то не было в заказе"), ("SERVICE", "Не понравилось обслуживание"), ("SLOW_SERVICE", "Официант долго не подходил"), ("OTHER", "Другая причина")], max_length=30, verbose_name="Причина")),
                ("place_details", models.CharField(blank=True, max_length=160, verbose_name="Номер комнаты, кабинки или стола")),
                ("description", models.TextField(max_length=2000, verbose_name="Что произошло")),
                ("status", models.CharField(choices=[("NEW", "Новая"), ("IN_REVIEW", "В работе"), ("RESOLVED", "Решена"), ("DISMISSED", "Закрыта без действий")], db_index=True, default="NEW", max_length=20, verbose_name="Статус")),
                ("staff_comment", models.TextField(blank=True, max_length=1000, verbose_name="Комментарий сотрудника")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("handled_by_staff", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="handled_complaints", to="reservations.staffprofile", verbose_name="Ответственный")),
                ("space", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="complaints", to="reservations.diningspace", verbose_name="Зал или комната")),
            ],
            options={
                "verbose_name": "Жалоба гостя",
                "verbose_name_plural": "Жалобы гостей",
                "ordering": ("-created_at", "-pk"),
            },
        ),
        migrations.RunPython(configure_spaces, migrations.RunPython.noop),
    ]
