from django.urls import path

from . import staff_views

app_name = "staff"

urlpatterns = [
    path("login/", staff_views.staff_login, name="login"),
    path("logout/", staff_views.staff_logout, name="logout"),
    path("", staff_views.dashboard, name="dashboard"),
    path("reservations/", staff_views.reservation_list, name="reservations"),
    path("reservations/<int:pk>/", staff_views.reservation_detail, name="reservation_detail"),
    path("reservations/<int:pk>/accept/", staff_views.reservation_accept, name="reservation_accept"),
    path("reservations/<int:pk>/propose/", staff_views.reservation_propose, name="reservation_propose"),
    path("reservations/<int:pk>/reject/", staff_views.reservation_reject, name="reservation_reject"),
    path("spaces/", staff_views.space_list, name="spaces"),
    path("spaces/add/", staff_views.space_edit, name="space_add"),
    path("spaces/<int:pk>/edit/", staff_views.space_edit, name="space_edit"),
    path("spaces/<int:pk>/deactivate/", staff_views.space_deactivate, name="space_deactivate"),
    path("settings/", staff_views.reservation_settings, name="settings"),
    path("settings/closures/add/", staff_views.closure_add, name="closure_add"),
    path("settings/closures/<int:pk>/delete/", staff_views.closure_delete, name="closure_delete"),
    path("employees/", staff_views.staff_list, name="members"),
    path("employees/add/", staff_views.staff_create, name="member_add"),
    path("employees/<int:pk>/edit/", staff_views.staff_edit, name="member_edit"),
    path("analytics/", staff_views.analytics, name="analytics"),
]
