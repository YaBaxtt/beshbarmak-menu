from django.db import migrations


DESCRIPTIONS = {
    "Beshbarmoq": ("Mayin go‘sht, yupqa xamir va xushbo‘y sho‘rva uyg‘unligidagi an’anaviy taom.", "Традиционное блюдо с нежным мясом, тонким тестом и ароматным бульоном."),
    "Norin — porsiya": ("Mayda kesilgan xamir va go‘shtdan tayyorlanadigan to‘yimli milliy taom.", "Сытное национальное блюдо из тонко нарезанного теста и мяса."),
    "Norin — 1 kg + 3 dona qazi": ("Katta davra uchun norin va uch dona qazi bilan mo‘l to‘plam.", "Большой набор нарына с тремя казы — удобно для дружной компании."),
    "Qiyma shashlik": ("Mayin qiyma va ziravorlardan tayyorlanib, ochiq olovda pishiriladi.", "Сочный шашлык из нежного фарша со специями, приготовленный на открытом огне."),
    "Ot jaz shashlik": ("Ochiq olovda qizartirib pishiriladigan, to‘yimli va xushbo‘y shashlik.", "Сытный и ароматный шашлык, поджаренный на открытом огне."),
    "Baliq (dona)": ("Buyurtma uchun alohida tayyorlanadigan, tashqi qismi qarsildoq baliq.", "Рыба, приготовленная отдельно для заказа, с аппетитной хрустящей корочкой."),
    "Baliq — 1 kg dan yuqori": ("Katta davra uchun 1 kg dan yuqori baliq, buyurtma asosida pishiriladi.", "Рыба весом свыше 1 кг для компании, готовится под заказ."),
    "Baliq — 2 kg dan yuqori": ("Katta mehmonlar davrasi uchun 2 kg dan yuqori baliq.", "Рыба весом свыше 2 кг для большого стола и дружной компании."),
    "Svejiy": ("Yangi mahsulotlardan tayyorlanadigan yengil va tetiklantiruvchi salat.", "Лёгкий и освежающий салат из свежих продуктов."),
    "Achiq-chuchuk": ("Pomidor, piyoz va ziravorlar uyg‘unligidagi sharqona salat.", "Восточный салат с помидорами, луком и ароматными специями."),
    "Morskoy kapriz": ("Dengiz ta’mlarini yoqtiradiganlar uchun mayin va to‘yimli salat.", "Нежный и сытный салат для любителей морских вкусов."),
    "Yaponskiy": ("Sharqona ohangdagi yengil va o‘ziga xos salat.", "Лёгкий салат с выразительным восточным характером."),
    "Chiroqchi": ("Milliy ta’m va yangi masalliqlar uyg‘unligidagi salat.", "Салат, в котором сочетаются национальный вкус и свежие продукты."),
    "Suzma": ("Mayin suzma va ko‘katlar bilan tayyorlanadigan yengil gazak.", "Лёгкая закуска из нежной сузьмы со свежей зеленью."),
    "Smak": ("To‘yimli, mayin va muvozanatli ta’mga ega salat.", "Сытный салат с нежным и сбалансированным вкусом."),
    "Sezar": ("Qarsildoq salat barglari va mayin sous uyg‘unligidagi mashhur salat.", "Популярный салат с хрустящими листьями и нежным соусом."),
    "Choy": ("Dasturxonga issiq tortiladigan klassik xushbo‘y choy.", "Классический ароматный чай, который подаётся горячим."),
    "Limonli choy": ("Limonning yengil nordonligi bilan xushbo‘y issiq choy.", "Ароматный горячий чай с лёгкой лимонной кислинкой."),
    "Coca-Cola 1 L": ("Davra uchun 1 litrlik tetiklantiruvchi gazli ichimlik.", "Освежающий газированный напиток объёмом 1 литр."),
    "Coca-Cola 1,5 L": ("Katta davra uchun 1,5 litrlik tetiklantiruvchi gazli ichimlik.", "Освежающий газированный напиток объёмом 1,5 литра для компании."),
    "Pepsi 1 L": ("Davra uchun 1 litrlik tetiklantiruvchi gazli ichimlik.", "Освежающий газированный напиток объёмом 1 литр."),
    "Pepsi 1,5 L": ("Katta davra uchun 1,5 litrlik tetiklantiruvchi gazli ichimlik.", "Освежающий газированный напиток объёмом 1,5 литра для компании."),
    "Fanta 1 L": ("Mevali ta’mga ega 1 litrlik gazli ichimlik.", "Газированный напиток с ярким фруктовым вкусом, 1 литр."),
    "Fanta 1,5 L": ("Davra uchun mevali ta’mga ega 1,5 litrlik gazli ichimlik.", "Фруктовый газированный напиток объёмом 1,5 литра для компании."),
    "Gazsiz suv 1 L": ("Kundalik ichish uchun toza gazsiz suv.", "Чистая негазированная вода для ежедневного питья."),
    "Gazli suv 1 L": ("Yengil va tetiklantiruvchi gazli suv.", "Лёгкая и освежающая газированная вода."),
    "Chortoq": ("O‘ziga xos mineral ta’mga ega Chortoq suvi.", "Вода «Чартак» с характерным минеральным вкусом."),
    "Moxito": ("Yalpiz va sitrus ohanglari uyg‘unligidagi tetiklantiruvchi ichimlik.", "Освежающий напиток с нотами мяты и цитруса."),
    "Moxito 1 L": ("Davra uchun yalpiz va sitrus ta’mli 1 litrlik moxito.", "Литр освежающего мохито с мятой и цитрусом для компании."),
    "Kokteyl": ("Mayin ta’mli, tetiklantiruvchi sovuq kokteyl.", "Освежающий холодный коктейль с мягким вкусом."),
}


def fill_blank_descriptions(apps, schema_editor):
    Dish = apps.get_model("menu", "Dish")
    for name_uz, (description_uz, description_ru) in DESCRIPTIONS.items():
        Dish.objects.filter(name_uz=name_uz, description_uz="").update(description_uz=description_uz)
        Dish.objects.filter(name_uz=name_uz, description_ru="").update(description_ru=description_ru)


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0009_update_restaurant_phone"),
    ]

    operations = [
        migrations.RunPython(fill_blank_descriptions, migrations.RunPython.noop),
    ]
