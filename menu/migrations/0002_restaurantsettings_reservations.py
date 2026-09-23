from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("menu", "0001_initial")]

    operations = [
        migrations.AddField(model_name="restaurantsettings", name="reservation_enabled", field=models.BooleanField(default=True, verbose_name="Бронирование включено")),
        migrations.AddField(model_name="restaurantsettings", name="minimum_advance_minutes", field=models.PositiveIntegerField(default=60, verbose_name="Минимум минут до визита")),
        migrations.AddField(model_name="restaurantsettings", name="maximum_days_ahead", field=models.PositiveSmallIntegerField(default=30, verbose_name="Дней для бронирования вперёд")),
        migrations.AddField(model_name="restaurantsettings", name="default_reservation_duration_minutes", field=models.PositiveIntegerField(default=120, verbose_name="Длительность брони, минут")),
        migrations.AddField(model_name="restaurantsettings", name="slot_interval_minutes", field=models.PositiveSmallIntegerField(default=30, verbose_name="Интервал слотов, минут")),
        migrations.AddField(model_name="restaurantsettings", name="minimum_guests", field=models.PositiveSmallIntegerField(default=1, verbose_name="Минимум гостей")),
        migrations.AddField(model_name="restaurantsettings", name="maximum_guests", field=models.PositiveSmallIntegerField(default=30, verbose_name="Максимум гостей")),
        migrations.AddField(model_name="restaurantsettings", name="cancellation_limit_hours", field=models.PositiveSmallIntegerField(default=3, verbose_name="Отмена не позднее, часов")),
        migrations.AddField(model_name="restaurantsettings", name="manager_confirmation_required", field=models.BooleanField(default=True, verbose_name="Требуется подтверждение менеджера")),
    ]
