"""Which city and mohalla the visitor picked. Stored in the session, chosen once."""
from .models import Area, City

SESSION_AREA = "area_id"


def current_city(request):
    if not hasattr(request, "_kk_city"):
        request._kk_city = City.objects.filter(is_live=True).order_by("id").first()
    return request._kk_city


def current_area(request, city=None):
    if hasattr(request, "_kk_area"):
        return request._kk_area
    area = None
    area_id = request.session.get(SESSION_AREA)
    if area_id:
        area = Area.objects.filter(pk=area_id, is_active=True).select_related("city").first()
    request._kk_area = area
    return area


def set_area(request, area):
    request.session[SESSION_AREA] = area.pk
    request._kk_area = area
