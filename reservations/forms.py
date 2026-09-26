import re
from datetime import date, timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Permission
from django.db import transaction

from menu.models import RestaurantSettings

from .models import Complaint, DiningSpace, Reservation, ReservationOccasion, RestaurantClosure, StaffProfile, WorkingHours


def sync_staff_permissions(user, role):
    if role == StaffProfile.Role.OWNER:
        permissions = Permission.objects.filter(content_type__app_label__in=("menu", "reservations"))
    elif role == StaffProfile.Role.CONTENT_MANAGER:
        permissions = Permission.objects.filter(content_type__app_label="menu")
    else:
        permissions = Permission.objects.none()
    user.user_permissions.set(permissions)


class RussianAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="Логин", widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}))
    password = forms.CharField(label="Пароль", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))
    error_messages = {"invalid_login": "Неверный логин или пароль.", "inactive": "Доступ сотрудника отключён."}


class ReservationForm(forms.ModelForm):
    occasion = forms.ChoiceField(required=False)

    class Meta:
        model = Reservation
        fields = ("date", "time", "guests_count", "space", "customer_name", "phone", "occasion", "customer_comment")
        labels = {
            "date": "Дата", "time": "Время", "guests_count": "Количество гостей", "space": "Зал или комната",
            "customer_name": "Ваше имя", "phone": "Телефон", "occasion": "Повод", "customer_comment": "Комментарий",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "time": forms.Select(choices=()),
            "guests_count": forms.NumberInput(attrs={"min": 1, "inputmode": "numeric"}),
            "space": forms.RadioSelect(),
            "customer_name": forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Как к вам обращаться"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel", "placeholder": "+998 90 123 45 67"}),
            "occasion": forms.Select(),
            "customer_comment": forms.Textarea(attrs={"rows": 3, "placeholder": "День рождения, нужен детский стул…"}),
        }

    def __init__(self, *args, language="ru", **kwargs):
        super().__init__(*args, **kwargs)
        self.language = language
        restaurant = RestaurantSettings.load()
        no_occasion = "Ko‘rsatilmagan" if language == "uz" else "Не указан"
        self.fields["occasion"].choices = [("", no_occasion)] + [
            (item.code, item.label(language)) for item in ReservationOccasion.objects.filter(is_active=True)
        ]
        self.fields["space"].queryset = DiningSpace.objects.filter(is_active=True)
        self.fields["date"].widget.attrs["min"] = date.today().isoformat()
        self.fields["date"].widget.attrs["max"] = (date.today() + timedelta(days=restaurant.maximum_days_ahead)).isoformat()
        self.fields["guests_count"].widget.attrs.update({"min": restaurant.minimum_guests, "max": restaurant.maximum_guests})
        self.fields["guests_count"].initial = max(restaurant.minimum_guests, 2)
        submitted_time = self.data.get("time") if self.is_bound else ""
        choose_date = "Avval sanani tanlang" if language == "uz" else "Сначала выберите дату"
        self.fields["time"].widget.choices = [(submitted_time, submitted_time)] if submitted_time else [("", choose_date)]
        if language == "uz":
            self.fields["customer_name"].widget.attrs["placeholder"] = "Ismingiz"
            self.fields["customer_comment"].widget.attrs["placeholder"] = "Tug‘ilgan kun, bolalar stuli kerak…"

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 7 or len(digits) > 15:
            message = "Telefon raqamini tekshiring." if self.language == "uz" else "Проверьте номер телефона."
            raise forms.ValidationError(message)
        return phone


COMPLAINT_REASON_LABELS = {
    "ru": {
        Complaint.Reason.CLEANLINESS: "Комната или зал были грязными",
        Complaint.Reason.AIR: "Было душно или неприятный воздух",
        Complaint.Reason.COLD_FOOD: "Еда была недостаточно горячей",
        Complaint.Reason.TASTE: "Не понравился вкус еды",
        Complaint.Reason.MISSING_ITEM: "Чего-то не было в заказе",
        Complaint.Reason.SERVICE: "Не понравилось обслуживание",
        Complaint.Reason.SLOW_SERVICE: "Официант долго не подходил",
        Complaint.Reason.OTHER: "Другая причина",
    },
    "uz": {
        Complaint.Reason.CLEANLINESS: "Xona yoki zal toza emas edi",
        Complaint.Reason.AIR: "Havo dim yoki yoqimsiz edi",
        Complaint.Reason.COLD_FOOD: "Taom issiq emas edi",
        Complaint.Reason.TASTE: "Taomning ta’mi yoqmadi",
        Complaint.Reason.MISSING_ITEM: "Buyurtmada nimadir yetishmadi",
        Complaint.Reason.SERVICE: "Xizmat ko‘rsatish yoqmadi",
        Complaint.Reason.SLOW_SERVICE: "Ofitsiant uzoq vaqt kelmadi",
        Complaint.Reason.OTHER: "Boshqa sabab",
    },
}


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ("reason", "space", "place_details", "description")
        widgets = {
            "reason": forms.RadioSelect(),
            "space": forms.Select(),
            "place_details": forms.TextInput(),
            "description": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, language="uz", **kwargs):
        super().__init__(*args, **kwargs)
        self.language = language if language in {"uz", "ru"} else "uz"
        self.fields["reason"].choices = [
            (value, COMPLAINT_REASON_LABELS[self.language][value])
            for value in Complaint.Reason.values
        ]
        self.fields["space"].queryset = DiningSpace.objects.filter(is_active=True).order_by("sort_order", "id")
        self.fields["space"].empty_label = "Ko‘rsatilmagan" if self.language == "uz" else "Не указано"
        language = self.language
        self.fields["space"].label_from_instance = lambda item: (
            f"{item.localized_name(language)} · {item.capacity_min or 1}–{item.capacity_max} "
            f"{'kishi' if language == 'uz' else 'гостей'}"
        )
        if self.language == "uz":
            self.fields["reason"].error_messages["required"] = "Iltimos, sababni tanlang."
            self.fields["description"].error_messages["required"] = "Iltimos, nima bo‘lganini yozing."
            self.fields["place_details"].widget.attrs["placeholder"] = "Masalan: 3-xona yoki 7-stol"
            self.fields["description"].widget.attrs["placeholder"] = "Nima bo‘lganini batafsil yozing"
        else:
            self.fields["reason"].error_messages["required"] = "Пожалуйста, выберите причину."
            self.fields["description"].error_messages["required"] = "Пожалуйста, опишите, что произошло."
            self.fields["place_details"].widget.attrs["placeholder"] = "Например: комната 3 или стол 7"
            self.fields["description"].widget.attrs["placeholder"] = "Подробно опишите, что произошло"

    def clean_description(self):
        value = " ".join(self.cleaned_data["description"].split())
        if len(value) < 10:
            message = "Iltimos, vaziyatni batafsilroq yozing." if self.language == "uz" else "Пожалуйста, опишите ситуацию подробнее."
            raise forms.ValidationError(message)
        return value


class DiningSpaceForm(forms.ModelForm):
    class Meta:
        model = DiningSpace
        fields = ("name", "name_uz", "space_type", "description", "description_uz", "image", "capacity_min", "capacity_max", "is_exclusive", "is_active", "is_bookable", "is_temporarily_unavailable", "hide_when_unavailable", "unavailable_reason", "unavailable_reason_uz", "sort_order")
        widgets = {"description": forms.Textarea(attrs={"rows": 4}), "description_uz": forms.Textarea(attrs={"rows": 4})}


class ProposalForm(forms.Form):
    proposed_date = forms.DateField(label="Новая дата", widget=forms.DateInput(attrs={"type": "date"}))
    proposed_time = forms.TimeField(label="Новое время", widget=forms.TimeInput(attrs={"type": "time", "step": 1800}))
    comment = forms.CharField(label="Комментарий для гостя", required=False, max_length=1000, widget=forms.Textarea(attrs={"rows": 3, "placeholder": "В 19:00 комната занята, можем предложить 20:00."}))


REJECTION_CHOICES = (
    ("Нет свободных мест", "Нет свободных мест"),
    ("Выбранное помещение недоступно", "Выбранное помещение недоступно"),
    ("На это время ресторан закрыт", "На это время ресторан закрыт"),
    ("Слишком большая группа", "Слишком большая группа"),
    ("OTHER", "Другая причина"),
)


class RejectionForm(forms.Form):
    reason = forms.ChoiceField(label="Причина", choices=REJECTION_CHOICES, widget=forms.RadioSelect())
    custom_reason = forms.CharField(label="Другая причина", required=False, max_length=500, widget=forms.Textarea(attrs={"rows": 3}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("reason") == "OTHER" and not cleaned.get("custom_reason", "").strip():
            self.add_error("custom_reason", "Напишите причину для гостя.")
        return cleaned

    def final_reason(self):
        return self.cleaned_data["custom_reason"].strip() if self.cleaned_data["reason"] == "OTHER" else self.cleaned_data["reason"]


class ReservationSettingsForm(forms.ModelForm):
    class Meta:
        model = RestaurantSettings
        fields = ("reservation_enabled", "minimum_advance_minutes", "maximum_days_ahead", "default_reservation_duration_minutes", "slot_interval_minutes", "minimum_guests", "maximum_guests", "cancellation_limit_hours", "manager_confirmation_required")
        widgets = {"slot_interval_minutes": forms.Select(choices=((15, "15 минут"), (30, "30 минут"), (60, "60 минут")))}


class WorkingHoursForm(forms.ModelForm):
    class Meta:
        model = WorkingHours
        fields = ("open_time", "close_time", "is_closed")
        widgets = {"open_time": forms.TimeInput(attrs={"type": "time"}), "close_time": forms.TimeInput(attrs={"type": "time"})}


class ClosureForm(forms.ModelForm):
    class Meta:
        model = RestaurantClosure
        fields = ("date", "reason", "full_day", "from_time", "to_time")
        widgets = {"date": forms.DateInput(attrs={"type": "date"}), "from_time": forms.TimeInput(attrs={"type": "time"}), "to_time": forms.TimeInput(attrs={"type": "time"})}


class StaffCreateForm(forms.Form):
    username = forms.CharField(label="Логин", max_length=150)
    first_name = forms.CharField(label="Имя", max_length=150)
    last_name = forms.CharField(label="Фамилия", max_length=150, required=False)
    password = forms.CharField(label="Временный пароль", min_length=8, widget=forms.PasswordInput())
    role = forms.ChoiceField(label="Роль", choices=StaffProfile.Role.choices)
    telegram_id = forms.IntegerField(label="Telegram ID", required=False)
    telegram_username = forms.CharField(label="Telegram username", required=False, max_length=80)
    telegram_notifications_enabled = forms.BooleanField(label="Получать уведомления Telegram", required=False, initial=True)
    is_active = forms.BooleanField(label="Доступ разрешён", required=False, initial=True)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if get_user_model().objects.filter(username=username).exists():
            raise forms.ValidationError("Такой логин уже используется.")
        return username

    @transaction.atomic
    def save(self):
        user = get_user_model().objects.create_user(
            username=self.cleaned_data["username"], password=self.cleaned_data["password"],
            first_name=self.cleaned_data["first_name"], last_name=self.cleaned_data["last_name"],
            is_staff=True, is_active=self.cleaned_data["is_active"],
        )
        profile = StaffProfile.objects.create(
            user=user, role=self.cleaned_data["role"], telegram_id=self.cleaned_data.get("telegram_id"),
            telegram_username=self.cleaned_data.get("telegram_username", ""),
            telegram_notifications_enabled=self.cleaned_data.get("telegram_notifications_enabled", False),
            is_active=self.cleaned_data.get("is_active", False),
        )
        sync_staff_permissions(user, profile.role)
        return profile


class StaffUpdateForm(forms.ModelForm):
    first_name = forms.CharField(label="Имя", max_length=150)
    last_name = forms.CharField(label="Фамилия", max_length=150, required=False)

    class Meta:
        model = StaffProfile
        fields = ("first_name", "last_name", "role", "telegram_id", "telegram_username", "telegram_notifications_enabled", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name

    @transaction.atomic
    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.user.first_name = self.cleaned_data["first_name"]
        profile.user.last_name = self.cleaned_data["last_name"]
        profile.user.is_active = self.cleaned_data["is_active"]
        if commit:
            profile.user.save(update_fields=("first_name", "last_name", "is_active"))
            profile.save()
            sync_staff_permissions(profile.user, profile.role)
        return profile
