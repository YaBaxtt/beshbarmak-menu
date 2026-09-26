from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve as media_serve


urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url="/static/images/favicon.svg", permanent=False)),
    path("admin/", admin.site.urls),
    path("reservation/", include("reservations.urls")),
    path("staff/", include("reservations.staff_urls")),
    path("", include("menu.urls")),
]

urlpatterns += [
    re_path(
        r"^media/(?P<path>.*)$",
        media_serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]

handler404 = "menu.views.not_found"
