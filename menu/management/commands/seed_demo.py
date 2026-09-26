from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from menu.models import Category, Dish, Promotion, RestaurantSettings
from reservations.models import DiningSpace, ReservationOccasion, WorkingHours


CATEGORIES = [
    ("beshbarmoq", "Beshbarmoq", "Бешбармак", "𓎩", 10),
    ("norin", "Norin", "Нарын", "🍜", 20),
    ("shashliklar", "Shashliklar", "Шашлыки", "♨", 30),
    ("baliq", "Baliq", "Рыба", "🐟", 40),
    ("salatlar", "Salatlar", "Салаты", "🥗", 50),
    ("ichimliklar", "Ichimliklar", "Напитки", "🥤", 60),
]

DISHES = [
    ("beshbarmoq", "Beshbarmoq", "Бешбармак", "", "", None),
    ("norin", "Norin — porsiya", "Нарын — порция", "", "", 50000),
    ("norin", "Norin — 1 kg + 3 dona qazi", "Нарын — 1 кг + 3 казы", "", "", 155000),
    ("shashliklar", "Qiyma shashlik", "Шашлык из фарша", "", "", None),
    ("shashliklar", "Ot jaz shashlik", "Шашлык «От жаз»", "", "", None),
    ("baliq", "Baliq (dona)", "Рыба (штука)", "", "", None),
    ("baliq", "Baliq — 1 kg dan yuqori", "Рыба — свыше 1 кг", "", "", None),
    ("baliq", "Baliq — 2 kg dan yuqori", "Рыба — свыше 2 кг", "", "", None),
    ("salatlar", "Svejiy", "Свежий", "", "", None),
    ("salatlar", "Achiq-chuchuk", "Ачичук", "", "", None),
    ("salatlar", "Morskoy kapriz", "Морской каприз", "", "", None),
    ("salatlar", "Yaponskiy", "Японский", "", "", None),
    ("salatlar", "Chiroqchi", "Чирокчи", "", "", None),
    ("salatlar", "Suzma", "Сузьма", "", "", None),
    ("salatlar", "Smak", "Смак", "", "", None),
    ("salatlar", "Sezar", "Цезарь", "", "", None),
    ("ichimliklar", "Choy", "Чай", "", "", None),
    ("ichimliklar", "Limonli choy", "Чай с лимоном", "", "", None),
    ("ichimliklar", "Coca-Cola 1 L", "Coca-Cola 1 л", "", "", None),
    ("ichimliklar", "Coca-Cola 1,5 L", "Coca-Cola 1,5 л", "", "", None),
    ("ichimliklar", "Pepsi 1 L", "Pepsi 1 л", "", "", None),
    ("ichimliklar", "Pepsi 1,5 L", "Pepsi 1,5 л", "", "", None),
    ("ichimliklar", "Fanta 1 L", "Fanta 1 л", "", "", None),
    ("ichimliklar", "Fanta 1,5 L", "Fanta 1,5 л", "", "", None),
    ("ichimliklar", "Gazsiz suv 1 L", "Вода без газа 1 л", "", "", None),
    ("ichimliklar", "Gazli suv 1 L", "Газированная вода 1 л", "", "", None),
    ("ichimliklar", "Chortoq", "Чартак", "", "", None),
    ("ichimliklar", "Moxito", "Мохито", "", "", None),
    ("ichimliklar", "Moxito 1 L", "Мохито 1 л", "", "", None),
    ("ichimliklar", "Kokteyl", "Коктейль", "", "", None),
]

PROMOTIONS = []


class Command(BaseCommand):
    help = "Idempotently create bilingual demo categories, dishes and restaurant settings."

    def handle(self, *args, **options):
        demo_dir = Path(settings.BASE_DIR) / "static" / "images" / "demo"
        source_dir = Path(settings.BASE_DIR) / "static" / "images" / "menu-source"
        categories = {}
        for slug, uz, ru, icon, order in CATEGORIES:
            category, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={"name_uz": uz, "name_ru": ru, "icon": icon, "sort_order": order, "is_active": True},
            )
            categories[slug] = category

        menu_dish_ids = []
        for order, item in enumerate(DISHES, start=1):
            slug, uz, ru, desc_uz, desc_ru, price = item
            dish, _ = Dish.objects.update_or_create(
                category=categories[slug],
                name_uz=uz,
                defaults={
                    "name_ru": ru,
                    "description_uz": desc_uz,
                    "description_ru": desc_ru,
                    "price": price,
                    "weight": "",
                    "is_available": True,
                    "is_popular": False,
                    "is_recommended": False,
                    "sort_order": order,
                },
            )
            menu_dish_ids.append(dish.pk)

        # Keep the command idempotent while removing the previous demo menu.
        Dish.objects.exclude(pk__in=menu_dish_ids).delete()
        Category.objects.exclude(slug__in=categories).delete()

        for title_uz, title_ru, description_uz, description_ru, badge_uz, badge_ru, filename, order in PROMOTIONS:
            promotion, _ = Promotion.objects.update_or_create(
                title_uz=title_uz,
                defaults={
                    "title_ru": title_ru, "description_uz": description_uz,
                    "description_ru": description_ru, "badge_uz": badge_uz,
                    "badge_ru": badge_ru, "link_url": "#dishes",
                    "is_active": True, "sort_order": order,
                },
            )
            source = source_dir / filename
            if source.exists() and not promotion.image:
                with source.open("rb") as image_file:
                    promotion.image.save(filename, File(image_file), save=True)
        if not PROMOTIONS:
            Promotion.objects.update(is_active=False)

        restaurant, created = RestaurantSettings.objects.get_or_create(pk=1)
        if created:
            restaurant.restaurant_name = "Beshbarmak House"
            restaurant.subtitle_uz = "Milliy taomlar • Issiq • Mazali"
            restaurant.subtitle_ru = "Национальная кухня • С пылу с жару"
            restaurant.about_uz = "Mehmondo‘stlik, iliq muhit va avlodlardan kelayotgan ta’mlar."
            restaurant.about_ru = "Гостеприимство, тёплая атмосфера и вкус, переданный поколениями."
            restaurant.working_hours_uz = "Har kuni, 11:00–23:00"
            restaurant.working_hours_ru = "Ежедневно, 11:00–23:00"
            restaurant.location_text_uz = "Turkys aholi punkti, Samarqand ko‘chasi, 44"
            restaurant.location_text_ru = "населённый пункт Туркыс, ул. Самарканд, 44"
            restaurant.location_url = "https://yandex.uz/maps/?text=%D0%BD%D0%B0%D1%81%D0%B5%D0%BB%D1%91%D0%BD%D0%BD%D1%8B%D0%B9%20%D0%BF%D1%83%D0%BD%D0%BA%D1%82%20%D0%A2%D1%83%D1%80%D0%BA%D1%8B%D1%81%2C%20%D1%83%D0%BB.%20%D0%A1%D0%B0%D0%BC%D0%B0%D1%80%D0%BA%D0%B0%D0%BD%D0%B4%2C%2044"
            restaurant.telegram_url = "https://t.me/bbaxttt"
            restaurant.youtube_url = "https://www.youtube.com/"
            hero_source = demo_dir / "hero.webp"
            if hero_source.exists():
                with hero_source.open("rb") as image_file:
                    restaurant.hero_image.save("hero.webp", File(image_file), save=False)
        restaurant.phone = "+998 94 636 11 44"
        restaurant.save()

        for day in range(7):
            WorkingHours.objects.get_or_create(day_of_week=day, defaults={"open_time": "11:00", "close_time": "23:00"})

        space_configs = (
            (("Asosiy zal", "Stol-stulli zal"), "Зал со столами и стульями", "Stol-stulli zal", "Удобный зал со столами и стульями для компании от 2 до 8 человек.", "2 dan 8 kishigacha bo‘lgan davra uchun stol-stulli qulay zal.", DiningSpace.SpaceType.HALL, 2, 8, False, 10),
            (("Katta zal",), "Большой зал", "Katta zal", "Большой зал для компании от 8 до 18 человек.", "8 dan 18 kishigacha bo‘lgan katta davra uchun zal.", DiningSpace.SpaceType.HALL, 8, 18, False, 20),
            (("Oilaviy xona", "Oddiy xona"), "Обычная комната", "Oddiy xona", "Небольшая отдельная комната для 1–2 гостей.", "1–2 mehmon uchun kichik va alohida xona.", DiningSpace.SpaceType.PRIVATE_ROOM, 1, 2, True, 30),
            (("VIP xona", "Tapchan"), "Тапчан", "Tapchan", "Отдельный тапчан для компании от 6 до 20 человек.", "6 dan 20 kishigacha bo‘lgan davra uchun alohida tapchan.", DiningSpace.SpaceType.PRIVATE_ROOM, 6, 20, True, 40),
        )
        for aliases, name_ru, name_uz, description_ru, description_uz, space_type, capacity_min, capacity_max, exclusive, sort_order in space_configs:
            space = DiningSpace.objects.filter(name_uz__in=aliases).order_by("pk").first()
            if not space:
                space = DiningSpace()
            space.name = name_ru
            space.name_uz = name_uz
            space.description = description_ru
            space.description_uz = description_uz
            space.space_type = space_type
            space.capacity_min = capacity_min
            space.capacity_max = capacity_max
            space.is_exclusive = exclusive
            space.is_active = True
            space.is_bookable = True
            space.is_temporarily_unavailable = False
            space.hide_when_unavailable = False
            space.unavailable_reason = ""
            space.unavailable_reason_uz = ""
            space.sort_order = sort_order
            space.save()

        for code, name_ru, name_uz, order in (
            ("REGULAR", "Обычный визит", "Oddiy tashrif", 10),
            ("BIRTHDAY", "День рождения", "Tug‘ilgan kun", 20),
            ("FAMILY", "Семейное мероприятие", "Oilaviy tadbir", 30),
            ("BUSINESS", "Деловая встреча", "Ish uchrashuvi", 40),
            ("OTHER", "Другое", "Boshqa", 50),
        ):
            ReservationOccasion.objects.get_or_create(
                code=code,
                defaults={"name_ru": name_ru, "name_uz": name_uz, "sort_order": order},
            )

        self.stdout.write(self.style.SUCCESS(f"Demo ready: {len(categories)} categories, {len(DISHES)} dishes, working hours and bookable spaces."))
