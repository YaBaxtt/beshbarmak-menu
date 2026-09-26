LANGUAGES = {"uz", "ru"}


WEEKDAYS = {
    "uz": ("Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"),
    "ru": ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"),
}


INFO_TEXT = {
    "uz": {
        "page_title": "Restoran haqida",
        "menu": "Menyu", "reserve": "Stol band qilish", "open_menu": "Menyuni ochish",
        "about_title": "Bir dasturxon atrofida jam bo‘ladigan maskan",
        "about_fallback": "Milliy taomlar, samimiy mehmondo‘stlik va yaqinlaringiz bilan baham ko‘rishga arzigulik ta’mlar.",
        "book_table": "Stol band qilish",
        "contacts_kicker": "Kontaktlar", "contacts_title": "Mehmonimiz bo‘ling",
        "contacts_text": "Yo‘nalishni Yandex Xaritalarda ochishingiz mumkin. Bron bo‘yicha yordam kerak bo‘lsa, bizga qo‘ng‘iroq qiling yoki yozing.",
        "address": "Manzil", "route": "Yo‘nalishni ochish ↗", "phone": "Telefon", "telegram": "Telegram orqali yozish ↗",
        "working_hours": "Ish vaqti", "hours_note": "Oshxona va bron xizmati ish vaqtida mavjud.",
        "schedule": "Jadval", "schedule_title": "Ish vaqti", "closed": "Yopiq", "every_day": "Har kuni",
        "faq_kicker": "Ko‘p beriladigan savollar", "faq_title": "Tashrifdan oldin muhim ma’lumotlar",
        "faqs": (
            ("Bron qilish uchun ro‘yxatdan o‘tish kerakmi?", "Yo‘q. Sana, vaqt va joyni tanlab, ism va telefon raqamini qoldirish kifoya."),
            ("Ariza darhol tasdiqlanadimi?", "Yo‘q. Avval menejer bo‘sh joyni tekshiradi. Ariza sahifasida holat avtomatik yangilanadi."),
            ("Tasdiqlangan bronni bekor qilish mumkinmi?", "Ha, agar tashrifgacha restoran belgilagan vaqtdan ko‘proq qolgan bo‘lsa. Keyinroq telefon orqali bog‘lanishingiz mumkin."),
            ("Katta davra uchun joyni qanday band qilaman?", "Mehmonlar sonini kiriting — sayt sig‘imi mos zal, xona yoki tapchanni ko‘rsatadi."),
            ("Restoran qayerda joylashgan?", "Quyidagi “Yo‘nalishni ochish” tugmasi orqali Yandex Xaritalarga o‘tishingiz mumkin."),
        ),
        "support_kicker": "Yordam", "support_title": "Savolingiz yoki e’tirozingiz bormi?",
        "support_text": "Savol bo‘lsa bizga yozing. Xizmat yoki taom bo‘yicha muammo bo‘lsa, anonim shikoyat yuborishingiz mumkin.",
        "support_button": "Yordamga yozish", "call": "Qo‘ng‘iroq qilish", "complaint": "Shikoyat yuborish",
        "reservation": "Bron qilish", "contacts": "Kontaktlar", "faq": "Savollar",
    },
    "ru": {
        "page_title": "О ресторане",
        "menu": "Меню", "reserve": "Забронировать", "open_menu": "Открыть меню",
        "about_title": "Место, где собираются за одним столом",
        "about_fallback": "Национальная кухня, тёплое гостеприимство и блюда, которыми хочется делиться с близкими.",
        "book_table": "Забронировать стол",
        "contacts_kicker": "Контакты", "contacts_title": "Приезжайте в гости",
        "contacts_text": "Построить маршрут можно сразу в Яндекс Картах. Если нужна помощь с бронированием — позвоните или напишите нам.",
        "address": "Адрес", "route": "Открыть маршрут ↗", "phone": "Телефон", "telegram": "Написать в Telegram ↗",
        "working_hours": "Время работы", "hours_note": "Кухня и бронирование доступны в часы работы.",
        "schedule": "График", "schedule_title": "Время работы", "closed": "Закрыто", "every_day": "Ежедневно",
        "faq_kicker": "Частые вопросы", "faq_title": "Всё важное перед визитом",
        "faqs": (
            ("Нужно ли регистрироваться для бронирования?", "Нет. Выберите дату, время и место, оставьте имя и телефон — этого достаточно."),
            ("Заявка сразу считается подтверждённой?", "Нет. Сначала менеджер проверит наличие мест. Статус обновится автоматически на странице вашей заявки."),
            ("Можно ли отменить подтверждённую бронь?", "Да, если до визита остаётся больше установленного рестораном времени. Позже можно связаться с нами по телефону."),
            ("Как забронировать место для большой компании?", "Укажите количество гостей — сайт покажет подходящий по вместимости зал, комнату или тапчан."),
            ("Где находится ресторан?", "Нажмите «Открыть маршрут», чтобы перейти в Яндекс Карты."),
        ),
        "support_kicker": "Поддержка", "support_title": "Остались вопросы или замечания?",
        "support_text": "Напишите нам, если нужна помощь. Если возникла проблема с обслуживанием или едой, отправьте анонимную жалобу.",
        "support_button": "Написать в поддержку", "call": "Позвонить", "complaint": "Отправить жалобу",
        "reservation": "Бронирование", "contacts": "Контакты", "faq": "Частые вопросы",
    },
}


COMPLAINT_TEXT = {
    "uz": {
        "page_title": "Anonim shikoyat", "menu": "Menyu", "reserve": "Stol band qilish", "open_menu": "Menyuni ochish",
        "kicker": "Sizning fikringiz muhim", "title": "Muammo haqida anonim xabar bering",
        "intro": "Ism va telefon raqami kerak emas. Xabarni faqat restoran egasi va administratorlari ko‘radi.",
        "anonymous_title": "To‘liq anonim", "anonymous_text": "Biz IP manzil, ism yoki telefon raqamini saqlamaymiz.",
        "reason": "Nima yoqmadi?", "location": "Qayerda o‘tirgandingiz?", "location_note": "Zal yoki xonani tanlang. Aniq raqam bo‘lsa, pastga yozing.",
        "space": "Zal yoki xona", "place_details": "Xona, kabinka yoki stol raqami", "description": "Nima bo‘lganini batafsil yozing",
        "required": "Majburiy", "optional": "Ixtiyoriy", "privacy": "Xabaringiz anonim saqlanadi va umumiy saytda ko‘rinmaydi.",
        "submit": "Shikoyatni yuborish", "sending": "Yuborilmoqda…",
        "success_title": "Xabaringiz qabul qilindi", "success_text": "Restoran administratorlari shikoyatni boshqaruv botidagi maxsus bo‘limda ko‘radi.",
        "back": "Menyuga qaytish", "another": "Yana xabar yuborish",
    },
    "ru": {
        "page_title": "Анонимная жалоба", "menu": "Меню", "reserve": "Забронировать", "open_menu": "Открыть меню",
        "kicker": "Ваше мнение важно", "title": "Анонимно сообщите о проблеме",
        "intro": "Имя и телефон не нужны. Сообщение увидят только владелец и администраторы ресторана.",
        "anonymous_title": "Полностью анонимно", "anonymous_text": "Мы не сохраняем IP-адрес, имя или номер телефона.",
        "reason": "Что вам не понравилось?", "location": "Где вы сидели?", "location_note": "Выберите зал или комнату. Если знаете точный номер, укажите его ниже.",
        "space": "Зал или комната", "place_details": "Номер комнаты, кабинки или стола", "description": "Подробно опишите, что произошло",
        "required": "Обязательно", "optional": "Необязательно", "privacy": "Сообщение сохраняется анонимно и не публикуется на сайте.",
        "submit": "Отправить жалобу", "sending": "Отправляем…",
        "success_title": "Сообщение принято", "success_text": "Администраторы ресторана увидят жалобу в специальном разделе управляющего Telegram-бота.",
        "back": "Вернуться в меню", "another": "Отправить ещё одно сообщение",
    },
}


def language_from_request(request):
    language = request.GET.get("lang") or request.POST.get("lang") or request.COOKIES.get("site_language") or "uz"
    return language if language in LANGUAGES else "uz"
