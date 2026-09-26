from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from menu.models import Category, Dish, DishImage, Promotion, RestaurantSettings
from reservations.models import DiningSpace, ReservationOccasion, WorkingHours


CATEGORIES = [
    ("asosiy", "Asosiy taomlar", "Основные блюда", "🥩", 10),
    ("shorvalar", "Sho‘rvalar", "Супы", "🍲", 20),
    ("baliqlar", "Baliq taomlari", "Рыбные блюда", "🐟", 30),
    ("salatlar", "Salatlar", "Салаты", "🥗", 40),
    ("ichimliklar", "Ichimliklar", "Напитки", "🥤", 50),
    ("desertlar", "Desertlar", "Десерты", "🍰", 60),
]

DISHES = [
    ("asosiy", "Beshbarmak", "Бешбармак", "Mayin go‘sht, uy xamiri, piyoz va xushbo‘y sho‘rva. Dasturxonning bosh taomi.", "Нежное мясо, домашняя лапша, лук и ароматный бульон. Главное блюдо стола.", 75000, "450 g", True, True, "beshbarmak.webp"),
    ("asosiy", "Sur go‘shtli beshbarmak", "Бешбармак с вяленым мясом", "Sur go‘sht, uy xamiri va xushbo‘y sho‘rva bilan to‘yimli beshbarmak.", "Сытный бешбармак с вяленым мясом, домашней лапшой и ароматным бульоном.", 100000, "450 g", True, True, "menu-beshbarmak.png"),
    ("asosiy", "Qazi assorti", "Ассорти казы", "An’anaviy ot go‘shti qazisi, ko‘kat va piyoz bilan.", "Традиционная конская колбаса с зеленью и луком.", 72000, "220 g", True, False, "qazi.webp"),
    ("asosiy", "Manti", "Манты", "Bug‘da pishirilgan yupqa xamir, shirali go‘sht va piyoz.", "Тонкое тесто на пару с сочным мясом и луком.", 49000, "5 dona", True, True, "manti.webp"),
    ("asosiy", "Qovurma lag‘mon", "Жареный лагман", "Qo‘lda cho‘zilgan lag‘mon, mol go‘shti va mavsumiy sabzavotlar.", "Домашняя лапша, говядина и сезонные овощи.", 54000, "380 g", True, False, "lagman.webp"),
    ("asosiy", "KFC uslubidagi tovuq", "Курица в стиле KFC", "Qarsildoq qobiqda qovurilgan, ziravorli tovuq bo‘laklari.", "Пряные кусочки курицы в хрустящей панировке.", 40000, "1 porsiya", True, False, "menu-fish.png"),
    ("asosiy", "Norin va sho‘rva", "Нарын с шурпой", "Mayin to‘g‘ralgan xamir va go‘sht, yoniga issiq sho‘rva.", "Тонко нарезанное тесто с мясом и горячая шурпа.", 40000, "1 porsiya", True, True, "menu-norin.png"),
    ("shorvalar", "Go‘shtli sho‘rva", "Мясная шурпа", "Suyakli go‘sht, kartoshka, sabzi va tiniq bulyon.", "Мясо на кости, картофель, морковь и прозрачный бульон.", 39000, "350 ml", True, True, "soup.webp"),
    ("shorvalar", "Mastava", "Мастава", "Guruch, mayda go‘sht va sabzavotlardan quyuq sho‘rva.", "Наваристый суп с рисом, мясом и овощами.", 35000, "350 ml", True, False, "soup.webp"),
    ("shorvalar", "Chuchvara", "Чучвара", "Mayda chuchvara va ko‘katli tiniq bulyon.", "Маленькие пельмени в прозрачном бульоне с зеленью.", 37000, "350 ml", False, False, "soup.webp"),
    ("baliqlar", "Mangalda baliq", "Рыба на мангале", "Mangalda xushbo‘y ziravorlar bilan pishirilgan baliq.", "Рыба, приготовленная на мангале с ароматными специями.", 70000, "1 porsiya", True, True, "menu-fish.png"),
    ("baliqlar", "Cho‘poncha baliq", "Рыба по-чабански", "Sabzavot va maxsus qayla bilan cho‘poncha usuldagi baliq.", "Рыба по-чабански с овощами и фирменным соусом.", 65000, "1 porsiya", True, False, "menu-fish.png"),
    ("baliqlar", "Qovurilgan baliq", "Жареная рыба", "Oltin ranggacha qovurilgan baliq, limon va piyoz bilan.", "Рыба, обжаренная до золотистой корочки, с лимоном и луком.", 70000, "1 porsiya", True, True, "menu-fried-fish.png"),
    ("salatlar", "Achchiq-chuchuk", "Ачу-чук", "Pomidor, piyoz, rayhon va bir chimdim achchiq qalampir.", "Помидоры, лук, базилик и щепотка острого перца.", 25000, "180 g", True, True, "salad.webp"),
    ("salatlar", "Oq salat", "Белый салат", "Tovuq filesi, bodring, tuxum va mayin qayla.", "Куриное филе, огурец, яйцо и нежная заправка.", 29000, "200 g", True, False, "salad.webp"),
    ("salatlar", "Erkaklar kaprizi", "Мужской каприз", "Go‘sht, tuxum, pishloq va mayin qaylali to‘yimli salat.", "Сытный салат с мясом, яйцом, сыром и нежной заправкой.", 40000, "200 g", True, False, "menu-salads.png"),
    ("salatlar", "Tailand salati", "Тайский салат", "Go‘sht va rang-barang sabzavotlardan tayyorlangan iliq salat.", "Тёплый салат с мясом и яркими овощами.", 40000, "200 g", True, True, "menu-salads.png"),
    ("salatlar", "Yangi salat", "Свежий салат", "Yangi bodring, pomidor va ko‘katlardan yengil salat.", "Лёгкий салат из свежих огурцов, помидоров и зелени.", 25000, "180 g", True, False, "menu-salads.png"),
    ("salatlar", "Chiroqchi salati", "Салат Чирокчи", "Sabzavot va maxsus qayla bilan restoran uslubidagi salat.", "Фирменный салат с овощами и специальной заправкой.", 30000, "200 g", True, False, "menu-salads.png"),
    ("ichimliklar", "Ko‘k choy", "Зелёный чай", "Choynakda yangi damlangan ko‘k choy.", "Свежезаваренный зелёный чай в чайнике.", 12000, "0.8 l", True, False, "tea.webp"),
    ("ichimliklar", "Qimiz", "Кумыс", "An’anaviy, tetiklantiruvchi qimiz.", "Традиционный освежающий кумыс.", 50000, "1 l", True, True, "menu-qimiz.png"),
    ("ichimliklar", "Mevali kompot", "Фруктовый компот", "Mavsumiy mevalardan tayyorlangan uy kompoti.", "Домашний компот из сезонных фруктов.", 16000, "0.5 l", True, False, "tea.webp"),
    ("desertlar", "Baursak", "Баурсак", "Oltin rangda qovurilgan yumshoq xamir bo‘laklari.", "Воздушные кусочки теста, обжаренные до золотистой корочки.", 22000, "250 g", True, True, "baursak.webp"),
    ("desertlar", "Chak-chak", "Чак-чак", "Asal bilan biriktirilgan mayin qovurilgan xamir.", "Нежное обжаренное тесто, соединённое ароматным мёдом.", 26000, "180 g", True, False, "baursak.webp"),
    ("desertlar", "Asalli tort", "Медовый торт", "Yupqa asalli qatlamlar va yengil qaymoqli krem.", "Тонкие медовые коржи и лёгкий сливочный крем.", 28000, "1 bo‘lak", False, True, "dessert.webp"),
]

PROMOTIONS = [
    (
        "Beshbarmak — 75 000 so‘m", "Бешбармак — 75 000 сум",
        "Milliy taomimizni maxsus narxda tatib ko‘ring.",
        "Попробуйте главное национальное блюдо по специальной цене.",
        "Maxsus taklif", "Специальное предложение", "menu-beshbarmak.png", 10,
    ),
    (
        "Baliq taomlari — 65 000 so‘mdan", "Рыбные блюда — от 65 000 сум",
        "Mangal va cho‘poncha usulidagi baliq taomlarini tanlang.",
        "Выберите рыбу на мангале или по-чабански.",
        "Yangi menyu", "Новинка меню", "menu-fish.png", 20,
    ),
    (
        "Norin + sho‘rva — 40 000 so‘m", "Нарын + шурпа — 40 000 сум",
        "An’anaviy norin va issiq sho‘rva bir porsiyada.",
        "Традиционный нарын и горячая шурпа в одной подаче.",
        "Mazali to‘plam", "Выгодный набор", "menu-norin.png", 30,
    ),
]


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

        for order, item in enumerate(DISHES, start=1):
            slug, uz, ru, desc_uz, desc_ru, price, weight, available, popular, filename = item
            dish, _ = Dish.objects.update_or_create(
                category=categories[slug],
                name_uz=uz,
                defaults={
                    "name_ru": ru,
                    "description_uz": desc_uz,
                    "description_ru": desc_ru,
                    "price": price,
                    "weight": weight,
                    "is_available": available,
                    "is_popular": popular,
                    "is_recommended": order in {1, 3, 5, 8, 13},
                    "sort_order": order,
                },
            )
            source = demo_dir / filename
            if not source.exists():
                source = source_dir / filename
            if source.exists() and not dish.images.exists():
                with source.open("rb") as image_file:
                    dish_image = DishImage(dish=dish, sort_order=0)
                    dish_image.image.save(filename, File(image_file), save=True)

        Dish.objects.filter(name_uz__in=("Ayran", "Ayron"), name_ru="Айран").delete()

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

        restaurant, created = RestaurantSettings.objects.get_or_create(pk=1)
        if created:
            restaurant.restaurant_name = "Beshbarmak House"
            restaurant.subtitle_uz = "Milliy taomlar • Issiq • Mazali"
            restaurant.subtitle_ru = "Национальная кухня • С пылу с жару"
            restaurant.about_uz = "Mehmondo‘stlik, iliq muhit va avlodlardan kelayotgan ta’mlar."
            restaurant.about_ru = "Гостеприимство, тёплая атмосфера и вкус, переданный поколениями."
            restaurant.phone = "+998 97 877 24 34"
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
