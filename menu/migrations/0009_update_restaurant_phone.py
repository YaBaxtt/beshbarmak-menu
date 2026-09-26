from django.db import migrations, models


PHONE = "+998 94 636 11 44"


def update_restaurant_phone(apps, schema_editor):
    RestaurantSettings = apps.get_model("menu", "RestaurantSettings")
    RestaurantSettings.objects.update(phone=PHONE)


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0008_replace_menu_catalog"),
    ]

    operations = [
        migrations.AlterField(
            model_name="restaurantsettings",
            name="phone",
            field=models.CharField(default=PHONE, max_length=40, verbose_name="Telefon"),
        ),
        migrations.RunPython(update_restaurant_phone, migrations.RunPython.noop),
    ]
