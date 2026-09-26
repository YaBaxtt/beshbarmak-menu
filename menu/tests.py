import tempfile
import uuid

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from reservations.models import Complaint, DiningSpace

from .models import Category, Dish, DishLike, Promotion, RestaurantSettings, Review


class MenuTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._media_directory = tempfile.TemporaryDirectory()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_directory.name)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls._media_override.disable()
            cls._media_directory.cleanup()

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def test_home_page_contains_database_menu(self):
        response = self.client.get(reverse("menu:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Beshbarmak House")
        self.assertContains(response, "Beshbarmoq")
        self.assertContains(response, "Taom qidirish")
        self.assertContains(response, "Norin — porsiya")
        self.assertContains(response, "50 000")
        self.assertNotContains(response, "complaint-entry")
        self.assertNotContains(response, "available-status")

    def test_catalog_matches_the_supplied_menu_without_fake_prices_or_photos(self):
        self.assertEqual(Category.objects.count(), 6)
        self.assertEqual(Dish.objects.count(), 30)
        self.assertEqual(Dish.objects.filter(category__slug="salatlar").count(), 8)
        self.assertEqual(Dish.objects.filter(category__slug="ichimliklar").count(), 14)
        self.assertEqual(Dish.objects.get(name_uz="Norin — porsiya").price, 50000)
        self.assertEqual(Dish.objects.get(name_uz="Norin — 1 kg + 3 dona qazi").price, 155000)
        self.assertIsNone(Dish.objects.get(name_uz="Beshbarmoq").price)
        self.assertFalse(Dish.objects.exclude(images=None).exists())
        self.assertFalse(Dish.objects.filter(description_uz="").exists())
        self.assertFalse(Dish.objects.filter(description_ru="").exists())

    def test_demo_seed_is_idempotent(self):
        counts = (Category.objects.count(), Dish.objects.count(), Promotion.objects.count(), RestaurantSettings.objects.count())
        dish = Dish.objects.get(name_uz="Beshbarmoq")
        dish.price = 987654
        dish.weight = "Restoran kiritgan porsiya"
        dish.is_popular = True
        dish.description_uz = "Restoran yozgan maxsus tavsif"
        dish.save(update_fields=("price", "weight", "is_popular", "description_uz"))
        call_command("seed_demo")
        self.assertEqual(counts, (Category.objects.count(), Dish.objects.count(), Promotion.objects.count(), RestaurantSettings.objects.count()))
        dish.refresh_from_db()
        self.assertEqual(dish.price, 987654)
        self.assertEqual(dish.weight, "Restoran kiritgan porsiya")
        self.assertTrue(dish.is_popular)
        self.assertEqual(dish.description_uz, "Restoran yozgan maxsus tavsif")

    def test_unavailable_dish_stays_visible(self):
        dish = Dish.objects.first()
        dish.is_available = False
        dish.save(update_fields=("is_available",))
        response = self.client.get(reverse("menu:home"))
        self.assertContains(response, dish.name_uz)

    def test_anonymous_guest_can_like_and_unlike_a_dish(self):
        dish = Dish.objects.first()
        url = reverse("menu:toggle-dish-like", args=(dish.pk,))

        liked = self.client.post(url)
        self.assertEqual(liked.status_code, 200)
        self.assertEqual(liked.json(), {"ok": True, "liked": True, "count": 1})
        self.assertEqual(DishLike.objects.filter(dish=dish).count(), 1)

        unliked = self.client.post(url)
        self.assertEqual(unliked.status_code, 200)
        self.assertEqual(unliked.json(), {"ok": True, "liked": False, "count": 0})
        self.assertFalse(DishLike.objects.filter(dish=dish).exists())

    def test_review_is_saved_once_and_waits_for_moderation(self):
        token = uuid.uuid4()
        payload = {
            "lang": "uz",
            "submission_token": str(token),
            "guest_name": "Dilshod",
            "rating": 5,
            "text": "Taom juda mazali, xizmat ham yaxshi bo‘ldi.",
        }
        first = self.client.post(reverse("menu:submit-review"), payload)
        second = self.client.post(reverse("menu:submit-review"), payload)
        self.assertRedirects(first, f"{reverse('menu:home')}?lang=uz&review=sent#reviews", fetch_redirect_response=False)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(Review.objects.filter(submission_token=token).count(), 1)
        review = Review.objects.get(submission_token=token)
        self.assertFalse(review.is_published)

        hidden_page = self.client.get(reverse("menu:home"))
        self.assertNotContains(hidden_page, review.text)
        review.is_published = True
        review.save(update_fields=("is_published",))
        visible_page = self.client.get(reverse("menu:home"))
        self.assertContains(visible_page, review.text)

    def test_invalid_review_is_rejected(self):
        response = self.client.post(reverse("menu:submit-review"), {
            "lang": "ru", "rating": 6, "text": "Нет",
        })
        self.assertRedirects(response, f"{reverse('menu:home')}?lang=ru&review=invalid#review-form", fetch_redirect_response=False)
        self.assertEqual(Review.objects.count(), 0)

    def test_mobile_navigation_and_information_page(self):
        response = self.client.get(reverse("menu:home"))
        self.assertContains(response, "data-nav-open")
        self.assertContains(response, reverse("menu:info") + "?lang=uz#faq")
        info = self.client.get(reverse("menu:info"))
        self.assertEqual(info.status_code, 200)
        self.assertContains(info, "Ko‘p beriladigan savollar")
        self.assertContains(info, "+998 94 636 11 44")
        self.assertContains(info, "Yandex Xaritalarda")
        self.assertContains(info, "Shikoyat yuborish")

        russian = self.client.get(reverse("menu:info"), {"lang": "ru"})
        self.assertContains(russian, "Частые вопросы")
        self.assertContains(russian, "Яндекс Картах")
        self.assertEqual(russian.cookies["site_language"].value, "ru")

    def test_anonymous_complaint_is_bilingual_and_idempotent(self):
        page = self.client.get(reverse("menu:complaint"))
        self.assertContains(page, "Muammo haqida anonim xabar bering")
        self.assertContains(page, "Ism va telefon raqami kerak emas")
        russian = self.client.get(reverse("menu:complaint"), {"lang": "ru"})
        self.assertContains(russian, "Анонимно сообщите о проблеме")

        token = uuid.uuid4()
        space = DiningSpace.objects.get(name_uz="Tapchan")
        payload = {
            "lang": "uz",
            "submission_token": str(token),
            "reason": Complaint.Reason.COLD_FOOD,
            "space": space.pk,
            "place_details": "4-tapchan",
            "description": "Taom sovuq holda olib kelindi.",
        }
        first = self.client.post(reverse("menu:complaint"), payload)
        second = self.client.post(reverse("menu:complaint"), payload)
        self.assertRedirects(first, f"{reverse('menu:complaint')}?lang=uz&sent=1", fetch_redirect_response=False)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(Complaint.objects.filter(submission_token=token).count(), 1)
        complaint = Complaint.objects.get(submission_token=token)
        self.assertEqual(complaint.status, Complaint.Status.NEW)
        self.assertEqual(complaint.space, space)

    def test_requested_spaces_are_seeded_with_capacity_ranges(self):
        expected = {
            "Stol-stulli zal": (2, 8),
            "Katta zal": (8, 18),
            "Oddiy xona": (1, 2),
            "Tapchan": (6, 20),
        }
        rows = DiningSpace.objects.filter(name_uz__in=expected).values_list("name_uz", "capacity_min", "capacity_max")
        self.assertEqual({name: (minimum, maximum) for name, minimum, maximum in rows}, expected)

    def test_only_one_restaurant_settings_record(self):
        RestaurantSettings.load()
        RestaurantSettings.load()
        self.assertEqual(RestaurantSettings.objects.count(), 1)

    def test_admin_redirects_anonymous_users_to_login(self):
        response = self.client.get("/admin/")
        self.assertRedirects(response, "/admin/login/?next=/admin/", fetch_redirect_response=False)

    def test_admin_menu_pages_load_for_superuser(self):
        user = get_user_model().objects.create_superuser("qa-admin", password="temporary-test-password")
        self.client.force_login(user)
        dish = Dish.objects.first()
        urls = (
            reverse("admin:index"),
            reverse("admin:menu_category_changelist"),
            reverse("admin:menu_dish_changelist"),
            reverse("admin:menu_dish_change", args=(dish.pk,)),
            reverse("admin:menu_promotion_changelist"),
            reverse("admin:menu_review_changelist"),
            reverse("admin:menu_dishlike_changelist"),
            reverse("admin:menu_restaurantsettings_changelist"),
            reverse("admin:reservations_complaint_changelist"),
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

        settings_page = self.client.get(reverse("admin:menu_restaurantsettings_change", args=(1,)))
        self.assertContains(settings_page, "YouTube havolasi")
        self.assertContains(settings_page, "Bron qilish sozlamalari")

    def test_missing_media_returns_404(self):
        response = self.client.get("/media/does-not-exist.webp")
        self.assertEqual(response.status_code, 404)
