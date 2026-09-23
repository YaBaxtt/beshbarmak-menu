from django.urls import path

from . import views

app_name = "reservations"

urlpatterns = [
    path("", views.reservation_start, name="start"),
    path("api/slots/", views.available_slots, name="slots"),
    path("api/spaces/", views.available_spaces, name="spaces"),
    path("status/<uuid:token>/", views.reservation_status, name="status"),
    path("status/<uuid:token>/data/", views.reservation_status_data, name="status_data"),
    path("status/<uuid:token>/accept-proposal/", views.accept_proposal, name="accept_proposal"),
    path("status/<uuid:token>/decline-proposal/", views.decline_proposal, name="decline_proposal"),
    path("status/<uuid:token>/cancel/", views.cancel_reservation, name="cancel"),
]
