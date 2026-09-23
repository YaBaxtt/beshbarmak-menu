from django.db import migrations, models


DEFAULT_OCCASIONS = (
    ("REGULAR", "Обычный визит", "Oddiy tashrif", 10),
    ("BIRTHDAY", "День рождения", "Tug‘ilgan kun", 20),
    ("FAMILY", "Семейное мероприятие", "Oilaviy tadbir", 30),
    ("BUSINESS", "Деловая встреча", "Ish uchrashuvi", 40),
    ("OTHER", "Другое", "Boshqa", 50),
)


def seed_localized_content(apps, schema_editor):
    Occasion = apps.get_model("reservations", "ReservationOccasion")
    for code, name_ru, name_uz, order in DEFAULT_OCCASIONS:
        Occasion.objects.get_or_create(
            code=code,
            defaults={"name_ru": name_ru, "name_uz": name_uz, "sort_order": order, "is_active": True},
        )

    DiningSpace = apps.get_model("reservations", "DiningSpace")
    translations = {
        "Основной зал": ("Asosiy zal", "Oilaviy uchrashuvlar va katta davralar uchun keng zal."),
        "Семейная комната": ("Oilaviy xona", "Kichik davra uchun alohida va shinam xona."),
    }
    for space in DiningSpace.objects.all():
        name_uz, description_uz = translations.get(space.name, (space.name, space.description))
        space.name_uz = name_uz
        space.description_uz = description_uz
        space.save(update_fields=("name_uz", "description_uz"))


class Migration(migrations.Migration):
    dependencies = [("reservations", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="diningspace",
            name="name_uz",
            field=models.CharField(blank=True, max_length=160, verbose_name="Название на узбекском"),
        ),
        migrations.AddField(
            model_name="diningspace",
            name="description_uz",
            field=models.TextField(blank=True, verbose_name="Описание на узбекском"),
        ),
        migrations.AddField(
            model_name="diningspace",
            name="unavailable_reason_uz",
            field=models.CharField(blank=True, max_length=240, verbose_name="Причина недоступности на узбекском"),
        ),
        migrations.CreateModel(
            name="ReservationOccasion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(help_text="Латиница, цифры, дефис или подчёркивание. Например: anniversary", max_length=30, unique=True, verbose_name="Код")),
                ("name_ru", models.CharField(max_length=120, verbose_name="Название на русском")),
                ("name_uz", models.CharField(max_length=120, verbose_name="Название на узбекском")),
                ("is_active", models.BooleanField(default=True, verbose_name="Показывать в форме")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="Порядок")),
            ],
            options={
                "verbose_name": "Повод бронирования",
                "verbose_name_plural": "Поводы бронирования",
                "ordering": ("sort_order", "id"),
            },
        ),
        migrations.AlterField(
            model_name="reservation",
            name="occasion",
            field=models.CharField(blank=True, max_length=30, verbose_name="Повод"),
        ),
        migrations.RunPython(seed_localized_content, migrations.RunPython.noop),
    ]
