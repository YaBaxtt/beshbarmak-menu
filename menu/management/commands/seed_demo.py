from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from menu.models import Category, Dish, DishImage, RestaurantSettings


CATEGORIES = [
    ("asosiy", "Asosiy taomlar", "Основные блюда", "🥩", 10),
    ("shorvalar", "Sho‘rvalar", "Супы", "🍲", 20),
    ("salatlar", "Salatlar", "Салаты", "🥗", 30),
    ("ichimliklar", "Ichimliklar", "Напитки", "🥤", 40),
    ("desertlar", "Desertlar", "Десерты", "🍰", 50),
]

DISHES = [
    ("asosiy", "Beshbarmak", "Бешбармак", "Mayin go‘sht, uy xamiri, piyoz va xushbo‘y sho‘rva. Dasturxonning bosh taomi.", "Нежное мясо, домашняя лапша, лук и ароматный бульон. Главное блюдо стола.", 89000, "450 g", True, True, "beshbarmak.webp"),
    ("asosiy", "Qazi assorti", "Ассорти казы", "An’anaviy ot go‘shti qazisi, ko‘kat va piyoz bilan.", "Традиционная конская колбаса с зеленью и луком.", 72000, "220 g", True, False, "qazi.webp"),
    ("asosiy", "Manti", "Манты", "Bug‘da pishirilgan yupqa xamir, shirali go‘sht va piyoz.", "Тонкое тесто на пару с сочным мясом и луком.", 49000, "5 dona", True, True, "manti.webp"),
    ("asosiy", "Qovurma lag‘mon", "Жареный лагман", "Qo‘lda cho‘zilgan lag‘mon, mol go‘shti va mavsumiy sabzavotlar.", "Домашняя лапша, говядина и сезонные овощи.", 54000, "380 g", True, False, "lagman.webp"),
    ("shorvalar", "Go‘shtli sho‘rva", "Мясная шурпа", "Suyakli go‘sht, kartoshka, sabzi va tiniq bulyon.", "Мясо на кости, картофель, морковь и прозрачный бульон.", 39000, "350 ml", True, True, "soup.webp"),
    ("shorvalar", "Mastava", "Мастава", "Guruch, mayda go‘sht va sabzavotlardan quyuq sho‘rva.", "Наваристый суп с рисом, мясом и овощами.", 35000, "350 ml", True, False, "soup.webp"),
    ("shorvalar", "Chuchvara", "Чучвара", "Mayda chuchvara va ko‘katli tiniq bulyon.", "Маленькие пельмени в прозрачном бульоне с зеленью.", 37000, "350 ml", False, False, "soup.webp"),
    ("salatlar", "Achchiq-chuchuk", "Ачичук", "Pomidor, piyoz, rayhon va bir chimdim achchiq qalampir.", "Помидоры, лук, базилик и щепотка острого перца.", 24000, "180 g", True, True, "salad.webp"),
    ("salatlar", "Oq salat", "Белый салат", "Tovuq filesi, bodring, tuxum va mayin qayla.", "Куриное филе, огурец, яйцо и нежная заправка.", 29000, "200 g", True, False, "salad.webp"),
    ("ichimliklar", "Ko‘k choy", "Зелёный чай", "Choynakda yangi damlangan ko‘k choy.", "Свежезаваренный зелёный чай в чайнике.", 12000, "0.8 l", True, False, "tea.webp"),
    ("ichimliklar", "Ayran", "Айран", "Salqin, yengil tuzlangan uy ayrani.", "Прохладный домашний айран с лёгкой солёностью.", 14000, "0.4 l", True, True, "ayran.webp"),
    ("ichimliklar", "Mevali kompot", "Фруктовый компот", "Mavsumiy mevalardan tayyorlangan uy kompoti.", "Домашний компот из сезонных фруктов.", 16000, "0.5 l", True, False, "tea.webp"),
    ("desertlar", "Baursak", "Баурсак", "Oltin rangda qovurilgan yumshoq xamir bo‘laklari.", "Воздушные кусочки теста, обжаренные до золотистой корочки.", 22000, "250 g", True, True, "baursak.webp"),
    ("desertlar", "Chak-chak", "Чак-чак", "Asal bilan biriktirilgan mayin qovurilgan xamir.", "Нежное обжаренное тесто, соединённое ароматным мёдом.", 26000, "180 g", True, False, "baursak.webp"),
    ("desertlar", "Asalli tort", "Медовый торт", "Yupqa asalli qatlamlar va yengil qaymoqli krem.", "Тонкие медовые коржи и лёгкий сливочный крем.", 28000, "1 bo‘lak", False, True, "dessert.webp"),
]


class Command(BaseCommand):
    help = "Idempotently create bilingual demo categories, dishes and restaurant settings."

    def handle(self, *args, **options):
        demo_dir = Path(settings.BASE_DIR) / "static" / "images" / "demo"
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
            if source.exists() and not dish.images.exists():
                with source.open("rb") as image_file:
                    dish_image = DishImage(dish=dish, sort_order=0)
                    dish_image.image.save(filename, File(image_file), save=True)

        restaurant = RestaurantSettings.load()
        restaurant.restaurant_name = "Beshbarmak House"
        restaurant.subtitle_uz = "Milliy taomlar • Issiq • Mazali"
        restaurant.subtitle_ru = "Национальная кухня • С пылу с жару"
        restaurant.about_uz = "Mehmondo‘stlik, iliq muhit va avlodlardan kelayotgan ta’mlar."
        restaurant.about_ru = "Гостеприимство, тёплая атмосфера и вкус, переданный поколениями."
        restaurant.phone = "+998 90 123 45 67"
        restaurant.working_hours_uz = "Har kuni, 10:00–23:00"
        restaurant.working_hours_ru = "Ежедневно, 10:00–23:00"
        restaurant.location_text_uz = "Yangiyo‘l, markaz"
        restaurant.location_text_ru = "Янгиюль, центр"
        restaurant.location_url = "https://maps.google.com/?q=Yangiyol"
        restaurant.telegram_url = "https://t.me/"
        restaurant.instagram_url = "https://instagram.com/"
        hero_source = demo_dir / "hero.webp"
        if hero_source.exists() and not restaurant.hero_image:
            with hero_source.open("rb") as image_file:
                restaurant.hero_image.save("hero.webp", File(image_file), save=False)
        restaurant.save()

        self.stdout.write(self.style.SUCCESS(f"Demo ready: {len(categories)} categories, {len(DISHES)} dishes."))
