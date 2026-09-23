from django.urls import path

from . import views


app_name = "menu"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.restaurant_info, name="info"),
]
