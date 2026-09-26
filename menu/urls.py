from django.urls import path

from . import views


app_name = "menu"

urlpatterns = [
    path("", views.home, name="home"),
    path("dish/<int:dish_id>/like/", views.toggle_dish_like, name="toggle-dish-like"),
    path("reviews/submit/", views.submit_review, name="submit-review"),
    path("about/", views.restaurant_info, name="info"),
    path("complaint/", views.complaint, name="complaint"),
]
