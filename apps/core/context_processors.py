from django.conf import settings

from .models import Category
from .selection import current_area, current_city


def site(request):
    city = current_city(request)
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_URL": settings.SITE_URL,
        "SUPPORT_WHATSAPP": settings.SUPPORT_WHATSAPP,
        "OTP_MODE": settings.OTP_PROVIDER,
        "current_city": city,
        "current_area": current_area(request, city),
        "customer": getattr(request, "customer", None),
        "footer_categories": Category.objects.filter(is_active=True),
    }
