import re
from urllib.parse import urlencode


LANGUAGES = {"uz", "ru"}


TEXT = {
    "ru": {
        "page_title": "Забронировать стол",
        "booking": "Бронирование",
        "hero_title": "Ваш стол ждёт",
        "hero_text": "Выберите удобное время и место. Менеджер проверит заявку и подтвердит её.",
        "when": "Когда", "where": "Где", "contacts": "Контакты",
        "date_time_guests": "Дата, время и гости",
        "hours_note": "Доступные часы зависят от графика ресторана.",
        "date": "Дата", "time": "Время", "guest_count": "Количество гостей",
        "decrease": "Уменьшить", "increase": "Увеличить", "choose_place": "Выбрать место",
        "space_title": "Зал или комната", "space_note": "Показываем только варианты, подходящие для вашей компании.",
        "no_spaces": "На это время подходящих мест не найдено.", "try_change": "Попробуйте изменить время или дату либо позвоните нам.",
        "change_time": "Изменить время", "call": "Позвонить", "back": "← Назад", "continue": "Продолжить",
        "contact_title": "Контактные данные", "privacy_note": "Аккаунт и email не нужны. Телефон увидят только сотрудники ресторана.",
        "name": "Ваше имя", "phone": "Телефон", "occasion": "Повод", "comment": "Комментарий", "optional": "необязательно",
        "check_data": "Проверьте данные", "all_correct": "Всё верно?", "guests": "Гостей", "place": "Место",
        "not_confirmed": "Отправка заявки ещё не означает подтверждение брони.", "submit": "Отправить заявку",
        "menu": "Меню", "reserve": "Забронировать", "open_menu": "Открыть меню",
        "application": "Заявка", "pending_title": "Заявка рассматривается", "pending_text": "Мы проверяем доступность. Это ещё не подтверждённая бронь.",
        "accepted_title": "Бронирование подтверждено", "accepted_text": "Ждём вас! Если планы изменятся, сообщите нам заранее.",
        "proposed_title": "Ресторан предлагает другое время", "proposed_text": "Проверьте предложение менеджера и выберите подходящий вариант.",
        "rejected_title": "Не можем подтвердить заявку", "rejected_text": "К сожалению, выбранный вариант сейчас недоступен.",
        "cancelled_title": "Бронирование отменено", "cancelled_text": "Вы можете отправить новую заявку на другое время.",
        "proposal": "Предлагаем", "agree": "Согласиться", "not_suitable": "Не подходит", "reason": "Причина",
        "cancel_booking": "Отменить бронирование", "cancel_confirm": "Отменить бронирование?", "choose_another": "Выбрать другую дату", "return_menu": "Вернуться в меню", "live": "Статус обновляется автоматически",
    },
    "uz": {
        "page_title": "Stol band qilish", "booking": "Stol band qilish", "hero_title": "Stolingiz sizni kutmoqda", "hero_text": "Qulay vaqt va joyni tanlang. Menejer arizani tekshiradi va tasdiqlaydi.",
        "when": "Qachon", "where": "Qayerda", "contacts": "Aloqa", "date_time_guests": "Sana, vaqt va mehmonlar", "hours_note": "Mavjud vaqtlar restoran ish jadvaliga bog‘liq.",
        "date": "Sana", "time": "Vaqt", "guest_count": "Mehmonlar soni", "decrease": "Kamaytirish", "increase": "Ko‘paytirish", "choose_place": "Joyni tanlash",
        "space_title": "Zal yoki xona", "space_note": "Faqat sizning davrangizga mos joylarni ko‘rsatamiz.", "no_spaces": "Bu vaqtga mos joy topilmadi.", "try_change": "Vaqt yoki sanani o‘zgartiring yoxud bizga qo‘ng‘iroq qiling.",
        "change_time": "Vaqtni o‘zgartirish", "call": "Qo‘ng‘iroq qilish", "back": "← Orqaga", "continue": "Davom etish",
        "contact_title": "Aloqa ma’lumotlari", "privacy_note": "Akkaunt va email kerak emas. Telefon raqamingizni faqat restoran xodimlari ko‘radi.", "name": "Ismingiz", "phone": "Telefon", "occasion": "Tadbir sababi", "comment": "Izoh", "optional": "ixtiyoriy",
        "check_data": "Ma’lumotlarni tekshiring", "all_correct": "Hammasi to‘g‘rimi?", "guests": "Mehmonlar", "place": "Joy", "not_confirmed": "Ariza yuborilishi bron tasdiqlanganini anglatmaydi.", "submit": "Arizani yuborish",
        "menu": "Menyu", "reserve": "Stol band qilish", "open_menu": "Menyuni ochish",
        "application": "Ariza", "pending_title": "Ariza ko‘rib chiqilmoqda", "pending_text": "Mavjudlikni tekshiryapmiz. Bu hali tasdiqlangan bron emas.",
        "accepted_title": "Bron tasdiqlandi", "accepted_text": "Sizni kutamiz! Rejalaringiz o‘zgarsa, oldindan xabar bering.",
        "proposed_title": "Restoran boshqa vaqtni taklif qilmoqda", "proposed_text": "Menejer taklifini tekshirib, sizga mos variantni tanlang.",
        "rejected_title": "Arizani tasdiqlay olmadik", "rejected_text": "Afsuski, tanlangan variant hozir mavjud emas.",
        "cancelled_title": "Bron bekor qilindi", "cancelled_text": "Boshqa vaqt uchun yangi ariza yuborishingiz mumkin.",
        "proposal": "Taklifimiz", "agree": "Roziman", "not_suitable": "Mos emas", "reason": "Sabab", "cancel_booking": "Bronni bekor qilish", "cancel_confirm": "Bronni bekor qilasizmi?", "choose_another": "Boshqa sanani tanlash", "return_menu": "Menyuga qaytish", "live": "Holat avtomatik yangilanadi",
    },
}


STATUS_LABELS = {
    "ru": {"PENDING": "Ожидает подтверждения", "ACCEPTED": "Подтверждено", "CHANGE_PROPOSED": "Предложено другое время", "REJECTED": "Отклонено", "CANCELLED": "Отменено", "COMPLETED": "Завершено", "NO_SHOW": "Гость не пришёл"},
    "uz": {"PENDING": "Tasdiqlash kutilmoqda", "ACCEPTED": "Tasdiqlandi", "CHANGE_PROPOSED": "Boshqa vaqt taklif qilindi", "REJECTED": "Rad etildi", "CANCELLED": "Bekor qilindi", "COMPLETED": "Yakunlandi", "NO_SHOW": "Mehmon kelmadi"},
}

SPACE_TYPES_UZ = {"HALL": "Zal", "PRIVATE_ROOM": "Alohida xona", "TERRACE": "Terrasa", "VIP": "VIP joy", "OTHER": "Boshqa"}


def language_from_request(request):
    language = request.GET.get("lang") or request.POST.get("lang") or request.COOKIES.get("site_language") or "uz"
    return language if language in LANGUAGES else "uz"


def text_for(language):
    return TEXT[language]


def add_language(url, language):
    return f"{url}?{urlencode({'lang': language})}"


def localize_error(message, language):
    if language != "uz":
        return message
    exact = {
        "Онлайн-бронирование сейчас приостановлено. Позвоните в ресторан.": "Onlayn bron qilish vaqtincha to‘xtatilgan. Restoranga qo‘ng‘iroq qiling.",
        "В этот день бронирование недоступно.": "Bu kunda bron qilish imkoni yo‘q.",
        "На это время ресторан закрыт.": "Bu vaqtda restoran yopiq.",
        "Для большой группы свяжитесь с рестораном по телефону.": "Katta guruh uchun restoran bilan telefon orqali bog‘laning.",
        "Это помещение сейчас нельзя забронировать.": "Bu joyni hozir band qilib bo‘lmaydi.",
        "Это помещение временно недоступно.": "Bu joy vaqtincha mavjud emas.",
        "Это время уже занято. Выберите другой вариант.": "Bu vaqt band. Boshqa variantni tanlang.",
        "Заявка уже обработана.": "Ariza allaqachon ko‘rib chiqilgan.",
        "Это предложение уже недоступно.": "Bu taklif endi mavjud emas.",
        "Эту бронь уже нельзя отменить.": "Bu bronni endi bekor qilib bo‘lmaydi.",
    }
    if message in exact:
        return exact[message]
    patterns = (
        (r"Бронь нужно оформить минимум за (\d+) минут\.", r"Bronni kamida \1 daqiqa oldin rasmiylashtirish kerak."),
        (r"Можно выбрать дату не дальше чем на (\d+) дней вперёд\.", r"Sanani ko‘pi bilan \1 kun oldinga tanlash mumkin."),
        (r"Минимальное количество гостей: (\d+)\.", r"Mehmonlar soni kamida \1 ta bo‘lishi kerak."),
        (r"Это помещение рассчитано минимум на (\d+) гостей\.", r"Bu joy kamida \1 mehmon uchun mo‘ljallangan."),
        (r"Это помещение рассчитано максимум на (\d+) гостей\.", r"Bu joy ko‘pi bilan \1 mehmon uchun mo‘ljallangan."),
    )
    for pattern, replacement in patterns:
        if re.fullmatch(pattern, message):
            return re.sub(pattern, replacement, message)
    return message
