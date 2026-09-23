from django.db.models import F
from django.utils import timezone

from .models import SiteVisitDaily


class SiteVisitMiddleware:
    """Counts public HTML page views without collecting personal data."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_count(request):
            today = timezone.localdate()
            session_key = f"site_visit_counted_{today.isoformat()}"
            is_unique = not request.session.get(session_key)
            stats, _ = SiteVisitDaily.objects.get_or_create(date=today)
            updates = {"views": F("views") + 1}
            if is_unique:
                updates["unique_visitors"] = F("unique_visitors") + 1
                request.session[session_key] = True
            SiteVisitDaily.objects.filter(pk=stats.pk).update(**updates)
        return self.get_response(request)

    @staticmethod
    def _should_count(request):
        if request.method != "GET":
            return False
        path = request.path
        if path.startswith(("/admin/", "/staff/", "/static/", "/media/", "/reservation/api/")):
            return False
        if path.endswith("/data/"):
            return False
        return path == "/" or path.startswith(("/about/", "/reservation/"))
