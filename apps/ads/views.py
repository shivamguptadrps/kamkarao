from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect

from .models import Banner, BannerDailyStat

ALLOWED_SCHEMES = ("http://", "https://", "tel:", "mailto:")


class BannerRedirect(HttpResponseRedirect):
    allowed_schemes = ["http", "https", "tel", "mailto"]


def banner_click(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    BannerDailyStat.bump([banner.pk], "clicks")
    link = banner.link.strip()
    if link.isdigit() and len(link) == 10:
        link = f"tel:+91{link}"
    if not link.startswith(ALLOWED_SCHEMES):
        return redirect("home")
    return BannerRedirect(link)
