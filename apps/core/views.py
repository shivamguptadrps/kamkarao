from django.contrib import messages
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.ads.models import banners_for
from apps.providers.models import Provider
from apps.providers.ranking import Filters, ranked_providers

from .geo import nearest_area
from .models import Area, Category
from .search import match_category
from .selection import current_area, current_city, set_area


def home(request):
    city = current_city(request)
    area = current_area(request, city)
    live = Q(providers__status=Provider.Status.LIVE)
    categories = Category.objects.filter(is_active=True).annotate(live_count=Count("providers", filter=live))
    top = []
    if city:
        top_qs = Provider.objects.filter(
            status=Provider.Status.LIVE, city=city, available_today=True,
            rating_count__gte=3,
        ).select_related("category", "area").order_by("-rating_avg", "-rating_count")
        top = list(top_qs[:8])
    stats = {
        "providers": Provider.objects.filter(status=Provider.Status.LIVE).count(),
        "areas": city.areas.filter(is_active=True).count() if city else 0,
        "services": categories.count(),
    }
    return render(request, "core/home.html", {
        "categories": categories,
        "top_providers": top,
        "stats": stats,
        "banners": banners_for(request, "home", city, area=area),
    })


def category_list(request, city_slug, slug):
    city = current_city(request)
    if not city or city.slug != city_slug:
        raise Http404
    category = get_object_or_404(Category, slug=slug, is_active=True)
    area = current_area(request, city)
    if request.GET.get("area"):
        picked = Area.objects.filter(city=city, slug=request.GET["area"], is_active=True).first()
        if picked:
            set_area(request, picked)
            area = picked
    f = Filters.from_request(request)
    providers = ranked_providers(category, city, area, f)
    ctx = {
        "category": category,
        "providers": providers,
        "filters": f,
        "subcategories": category.subcategories.all(),
        "rate_items": category.rate_items.all()[:4],
        "banners": banners_for(request, "listing", city, category=category, area=area),
        "other_categories": Category.objects.filter(is_active=True).exclude(pk=category.pk),
    }
    return render(request, "core/category.html", ctx)


def area_sheet(request):
    city = current_city(request)
    areas = city.areas.filter(is_active=True).order_by("name_en") if city else []
    q = (request.GET.get("q") or "").strip().lower()
    if q:
        areas = [a for a in areas if q in a.name_en.lower() or q in a.name_hi]
    template = "core/_area_list.html" if request.GET.get("q") is not None and request.headers.get("HX-Request") else "core/_area_sheet.html"
    return render(request, template, {"areas": areas, "next": request.GET.get("next", "")})


@require_POST
def area_set(request):
    city = current_city(request)
    area = get_object_or_404(Area, pk=request.POST.get("area"), city=city, is_active=True)
    set_area(request, area)
    nxt = request.POST.get("next") or reverse("home")
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = reverse("home")
    if request.headers.get("HX-Request"):
        resp = HttpResponse("")
        resp["HX-Redirect"] = nxt
        return resp
    return redirect(nxt)


def area_nearest(request):
    """'Use my location': only used to pick the closest mohalla, never stored."""
    city = current_city(request)
    try:
        lat, lon = float(request.GET["lat"]), float(request.GET["lon"])
    except (KeyError, ValueError):
        return JsonResponse({"error": "bad location"}, status=400)
    area, km = nearest_area(city.areas.filter(is_active=True), lat, lon)
    if not area or km > 15:
        return JsonResponse({"error": "outside"}, status=404)
    return JsonResponse({"id": area.id, "name": area.name, "km": round(km, 1)})


def search(request):
    q = (request.GET.get("q") or "").strip()
    city = current_city(request)
    cat = match_category(q)
    if cat and city:
        return redirect("category_list", city_slug=city.slug, slug=cat.slug)
    if q:
        messages.info(request, q)
    url = reverse("work_request")
    return redirect(f"{url}?text={q}" if q else url)


def robots(request):
    lines = ["User-agent: *", "Disallow: /admin/", "Disallow: /*/account/",
             f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def offline(request):
    return render(request, "core/offline.html")


def credits(request):
    return render(request, "core/credits.html")
