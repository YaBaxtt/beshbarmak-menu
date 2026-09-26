import uuid

from django.db.models import Avg, Count, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from reservations.forms import ComplaintForm
from reservations.models import Complaint, WorkingHours

from .forms import ReviewForm
from .i18n import COMPLAINT_TEXT, INFO_TEXT, WEEKDAYS, language_from_request
from .models import Category, Dish, DishImage, DishLike, Promotion, RestaurantSettings, Review


def _remember_language(request, response, language):
    if request.GET.get("lang") in {"uz", "ru"} or request.POST.get("lang") in {"uz", "ru"}:
        response.set_cookie("site_language", language, max_age=31_536_000, samesite="Lax")
    return response


def home(request):
    language = language_from_request(request)
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    images = Prefetch("images", queryset=DishImage.objects.order_by("sort_order", "id"))
    dishes = list(
        Dish.objects.select_related("category")
        .prefetch_related(images)
        .annotate(likes_count=Count("likes"))
        .filter(category__is_active=True)
        .order_by("category__sort_order", "sort_order", "id")
    )
    liked_dish_ids = set(
        DishLike.objects.filter(session_key=session_key).values_list("dish_id", flat=True)
    )
    categories = list(Category.objects.filter(is_active=True))
    settings = RestaurantSettings.load()
    now = timezone.now()
    promotions = Promotion.objects.filter(is_active=True).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        Q(ends_at__isnull=True) | Q(ends_at__gte=now),
    )
    reviews = Review.objects.filter(is_published=True)
    review_stats = reviews.aggregate(average=Avg("rating"), total=Count("id"))

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
            "likes_count": dish.likes_count,
            "liked": dish.pk in liked_dish_ids,
            "images": [image.image.url for image in dish.images.all()],
        }
        for dish in dishes
    }

    response = render(
        request,
        "menu/home.html",
        {
            "restaurant": settings,
            "categories": categories,
            "dishes": dishes,
            "popular_dishes": [dish for dish in dishes if dish.is_popular],
            "promotions": promotions,
            "dish_data": dish_data,
            "language": language,
            "liked_dish_ids": liked_dish_ids,
            "reviews": reviews,
            "review_average": review_stats["average"] or 0,
            "review_total": review_stats["total"],
            "review_form": ReviewForm(),
            "review_token": uuid.uuid4(),
            "review_submitted": request.GET.get("review") == "sent",
            "review_invalid": request.GET.get("review") == "invalid",
        },
    )
    return _remember_language(request, response, language)


@require_POST
def toggle_dish_like(request, dish_id):
    if not request.session.session_key:
        request.session.create()
    try:
        dish = Dish.objects.get(pk=dish_id)
    except Dish.DoesNotExist:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)

    like, created = DishLike.objects.get_or_create(
        dish=dish,
        session_key=request.session.session_key,
    )
    if not created:
        like.delete()
    return JsonResponse({
        "ok": True,
        "liked": created,
        "count": DishLike.objects.filter(dish=dish).count(),
    })


@require_POST
def submit_review(request):
    language = language_from_request(request)
    form = ReviewForm(request.POST)
    try:
        submission_token = uuid.UUID(request.POST.get("submission_token", ""))
    except (TypeError, ValueError, AttributeError):
        submission_token = uuid.uuid4()

    if form.is_valid():
        review = form.save(commit=False)
        review.submission_token = submission_token
        review.language = language
        Review.objects.get_or_create(
            submission_token=submission_token,
            defaults={
                "guest_name": review.guest_name,
                "rating": review.rating,
                "text": review.text,
                "language": review.language,
            },
        )
        response = redirect(f"{reverse('menu:home')}?lang={language}&review=sent#reviews")
        return _remember_language(request, response, language)

    response = redirect(f"{reverse('menu:home')}?lang={language}&review=invalid#review-form")
    return _remember_language(request, response, language)


def restaurant_info(request):
    language = language_from_request(request)
    restaurant = RestaurantSettings.load()
    schedule = [
        {"label": WEEKDAYS[language][hours.day_of_week], "hours": hours}
        for hours in WorkingHours.objects.order_by("day_of_week")
    ]
    response = render(request, "menu/info.html", {
        "restaurant": restaurant,
        "schedule": schedule,
        "language": language,
        "t": INFO_TEXT[language],
        "about_text": restaurant.about_uz if language == "uz" else restaurant.about_ru,
        "location_text": restaurant.location_text_uz if language == "uz" else restaurant.location_text_ru,
        "working_hours_text": restaurant.working_hours_uz if language == "uz" else restaurant.working_hours_ru,
    })
    return _remember_language(request, response, language)


def complaint(request):
    language = language_from_request(request)
    restaurant = RestaurantSettings.load()
    raw_token = request.POST.get("submission_token", "") if request.method == "POST" else ""
    try:
        submission_token = uuid.UUID(raw_token) if raw_token else uuid.uuid4()
    except (TypeError, ValueError, AttributeError):
        submission_token = uuid.uuid4()

    form = ComplaintForm(request.POST or None, language=language)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        Complaint.objects.get_or_create(
            submission_token=submission_token,
            defaults={
                "reason": data["reason"],
                "space": data.get("space"),
                "place_details": data.get("place_details", ""),
                "description": data["description"],
            },
        )
        response = redirect(f"{reverse('menu:complaint')}?lang={language}&sent=1")
        return _remember_language(request, response, language)

    response = render(request, "menu/complaint.html", {
        "restaurant": restaurant,
        "language": language,
        "t": COMPLAINT_TEXT[language],
        "form": form,
        "submission_token": submission_token,
        "submitted": request.GET.get("sent") == "1",
    })
    return _remember_language(request, response, language)


def not_found(request, exception):
    return render(request, "404.html", status=404)
