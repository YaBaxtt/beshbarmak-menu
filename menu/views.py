from django.db.models import Prefetch
from django.shortcuts import render

from .models import Category, Dish, DishImage, RestaurantSettings


def home(request):
    images = Prefetch("images", queryset=DishImage.objects.order_by("sort_order", "id"))
    dishes = list(
        Dish.objects.select_related("category")
        .prefetch_related(images)
        .filter(category__is_active=True)
        .order_by("category__sort_order", "sort_order", "id")
    )
    categories = list(Category.objects.filter(is_active=True))
    settings = RestaurantSettings.load()

    dish_data = {
        str(dish.pk): {
            "id": dish.pk,
            "category_uz": dish.category.name_uz,
            "category_ru": dish.category.name_ru,
            "name_uz": dish.name_uz,
            "name_ru": dish.name_ru,
            "description_uz": dish.description_uz,
            "description_ru": dish.description_ru,
            "price": dish.price,
            "weight": dish.weight,
            "available": dish.is_available,
            "popular": dish.is_popular,
            "recommended": dish.is_recommended,
            "images": [image.image.url for image in dish.images.all()],
        }
        for dish in dishes
    }

    return render(
        request,
        "menu/home.html",
        {
            "restaurant": settings,
            "categories": categories,
            "dishes": dishes,
            "popular_dishes": [dish for dish in dishes if dish.is_popular],
            "dish_data": dish_data,
        },
    )


def not_found(request, exception):
    return render(request, "404.html", status=404)
