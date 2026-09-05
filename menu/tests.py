import tempfile

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from .models import Category, Dish, RestaurantSettings


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
        self.assertContains(response, "Beshbarmak")
        self.assertContains(response, "Taom qidirish")

    def test_demo_seed_is_idempotent(self):
        counts = (Category.objects.count(), Dish.objects.count(), RestaurantSettings.objects.count())
        call_command("seed_demo")
        self.assertEqual(counts, (Category.objects.count(), Dish.objects.count(), RestaurantSettings.objects.count()))

    def test_unavailable_dish_stays_visible(self):
        dish = Dish.objects.filter(is_available=False).first()
        response = self.client.get(reverse("menu:home"))
        self.assertContains(response, dish.name_uz)

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
            reverse("admin:menu_restaurantsettings_changelist"),
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_missing_media_returns_404(self):
        response = self.client.get("/media/does-not-exist.webp")
        self.assertEqual(response.status_code, 404)
