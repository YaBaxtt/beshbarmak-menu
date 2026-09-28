from django.db import migrations


def update_menu(apps, schema_editor):
    Category = apps.get_model("menu", "Category")
    Dish = apps.get_model("menu", "Dish")

    def update(name, **values):
        Dish.objects.filter(name_uz=name).update(**values)

    def add(category_slug, name_uz, name_ru, description_uz, description_ru, price, weight, sort_order):
        category = Category.objects.get(slug=category_slug)
        Dish.objects.get_or_create(
            category=category,
            name_uz=name_uz,
            defaults={
                "name_ru": name_ru,
                "description_uz": description_uz,
                "description_ru": description_ru,
                "price": price,
                "weight": weight,
                "is_available": True,
                "is_popular": False,
                "is_recommended": False,
                "sort_order": sort_order,
            },
        )

    update("Beshbarmoq", price=90000, weight="1 porsiya")
    update("Norin — porsiya", price=50000, weight="1 porsiya")
    update("Baliq (dona)", price=85000)
    update("Baliq — 1 kg dan yuqori", price=110000, weight="1 kg dan yuqori")
    update("Baliq — 2 kg dan yuqori", price=120000, weight="2 kg dan yuqori")

    for name in ("Coca-Cola 1 L", "Pepsi 1 L", "Fanta 1 L"):
        update(name, price=15000, weight="1 L")
    for name in ("Coca-Cola 1,5 L", "Pepsi 1,5 L", "Fanta 1,5 L"):
        update(name, price=18000, weight="1,5 L")

    update("Chortoq", name_uz="Chortoq 0,5 L", name_ru="Чартак 0,5 л", price=15000, weight="0,5 L")
    update("Moxito", name_uz="Moxito 0,5 L", name_ru="Мохито 0,5 л", price=25000, weight="0,5 L")
    update("Moxito 1 L", price=40000, weight="1 L")

    add("norin", "Norin — 1 kg", "Нарын — 1 кг", "Katta davra uchun bir kilogramm to‘yimli norin.", "Один килограмм сытного нарына для большой компании.", 135000, "1 kg", 25)
    add("baliq", "Baliq — 3 kg dan yuqori", "Рыба — свыше 3 кг", "Katta tadbir va davralar uchun 3 kg dan yuqori baliq.", "Рыба весом свыше 3 кг для большого праздника или компании.", 130000, "3 kg dan yuqori", 85)
    add("baliq", "Baliq filesi — porsiya", "Филе рыбы — порция", "Suyaksiz baliq filesidan tayyorlanadigan qulay porsiya.", "Удобная порция нежного рыбного филе без костей.", 65000, "1 porsiya", 86)
    add("baliq", "Baliq filesi — 1 kg", "Филе рыбы — 1 кг", "Katta davra uchun bir kilogramm mayin baliq filesi.", "Один килограмм нежного рыбного филе для компании.", 130000, "1 kg", 87)
    add("ichimliklar", "Sharbat", "Сок", "Mevali ta’mga ega tetiklantiruvchi sharbat.", "Освежающий фруктовый сок.", 18000, "", 305)
    add("ichimliklar", "Muzli ichimlik 1 L", "Холодный напиток 1 л", "Muzdek tortiladigan bir litrlik tetiklantiruvchi ichimlik.", "Освежающий холодный напиток объёмом 1 литр.", 15000, "1 L", 306)


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0010_fill_bilingual_dish_descriptions"),
    ]

    operations = [
        migrations.RunPython(update_menu, migrations.RunPython.noop),
    ]
