from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.ads.models import banners_for
from apps.core.geo import km_between
from apps.core.models import Category
from apps.core.phone import normalize_phone
from apps.core.selection import current_area, current_city
from apps.leads.models import Complaint, Lead

from .models import JoinRequest, Provider

VISIBLE = [Provider.Status.LIVE]


def _resume_url(request, provider, mode):
    """After OTP, come back to the same page and open this provider's number automatically."""
    current = request.headers.get("HX-Current-URL") or provider.get_absolute_url()
    parts = urlsplit(current)
    if parts.netloc and parts.netloc != request.get_host():
        parts = urlsplit(provider.get_absolute_url())
    query = [(k, v) for k, v in parse_qsl(parts.query) if k not in ("reveal", "mode", "login")]
    query += [("reveal", str(provider.pk)), ("mode", mode)]
    return urlunsplit(("", "", parts.path, urlencode(query), ""))


def provider_detail(request, pk, slug=None):
    p = get_object_or_404(
        Provider.objects.select_related("category", "area", "city").prefetch_related("subcategories"),
        pk=pk,
    )
    if p.status not in VISIBLE and not request.user.is_staff:
        raise Http404
    city = current_city(request)
    area = current_area(request, city)
    distance = km_between(area.lat, area.lon, p.area.lat, p.area.lon) if area else None
    reviews = p.ratings.filter(is_approved=True).exclude(text="").select_related("lead__area")[:6]
    revealed = bool(request.customer and p.leads.filter(customer=request.customer).exists())
    similar = (Provider.objects.filter(status=Provider.Status.LIVE, category=p.category, city=p.city)
               .exclude(pk=p.pk).select_related("area").order_by("-rating_avg")[:4])
    return render(request, "providers/detail.html", {
        "p": p,
        "distance": distance,
        "reviews": reviews,
        "rate_items": p.category.rate_items.all(),
        "answer_rate": p.answer_rate(),
        "revealed": revealed,
        "similar": similar,
        "banners": banners_for(request, "profile", city, category=p.category, area=area, limit=1),
    })


def reveal(request, pk):
    """Show the full number. Needs a verified phone; every reveal is a lead."""
    p = get_object_or_404(Provider, pk=pk, status=Provider.Status.LIVE)
    mode = request.GET.get("mode", "call")
    mode = mode if mode in ("call", "wa") else "call"
    if not request.customer:
        return render(request, "accounts/_login_phone.html", {
            "next": _resume_url(request, p, mode), "reason": "reveal", "provider": p,
        })
    today = timezone.localdate()
    existing = Lead.objects.filter(customer=request.customer, provider=p, created_at__date=today).first()
    if not existing:
        count = Lead.objects.filter(customer=request.customer, created_at__date=today).count()
        if count >= settings.DAILY_REVEAL_LIMIT:
            return render(request, "providers/_reveal_limit.html", {"p": p})
        city = current_city(request)
        existing = Lead.objects.create(
            customer=request.customer, provider=p, mode=mode, area=current_area(request, city)
        )
    area = current_area(request)
    return render(request, "providers/_reveal.html", {"p": p, "mode": mode, "area": area})


def join(request):
    categories = Category.objects.filter(is_active=True)
    city = current_city(request)
    ctx = {"categories": categories, "areas": city.areas.filter(is_active=True) if city else []}
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()[:120]
        try:
            phone = normalize_phone(request.POST.get("phone", ""))
        except ValidationError as e:
            ctx.update(error=e.messages[0], form=request.POST)
            return render(request, "providers/join.html", ctx)
        if not name:
            ctx.update(error=_("Please write your name."), form=request.POST)
            return render(request, "providers/join.html", ctx)
        JoinRequest.objects.create(
            name=name, phone=phone,
            category=categories.filter(pk=request.POST.get("category") or 0).first(),
            other_work=(request.POST.get("other_work") or "")[:120],
            area=ctx["areas"].filter(pk=request.POST.get("area") or 0).first() if city else None,
        )
        return render(request, "providers/join.html", {**ctx, "done": True})
    return render(request, "providers/join.html", ctx)


def complaint(request, pk):
    p = get_object_or_404(Provider, pk=pk)
    ctx = {"p": p, "reasons": Complaint.Reason.choices}
    if request.method == "POST":
        reason = request.POST.get("reason")
        if reason not in Complaint.Reason.values:
            ctx["error"] = _("Please choose what happened.")
            return render(request, "providers/complaint.html", ctx)
        phone = ""
        if request.customer:
            phone = request.customer.phone
        else:
            try:
                phone = normalize_phone(request.POST.get("phone", ""))
            except ValidationError as e:
                ctx.update(error=e.messages[0], form=request.POST)
                return render(request, "providers/complaint.html", ctx)
        Complaint.objects.create(
            provider=p, customer=request.customer, phone=phone, reason=reason,
            details=(request.POST.get("details") or "")[:1000],
        )
        messages.success(request, _("Thank you. Our team will call you and the provider, then decide."))
        return redirect(p.get_absolute_url())
    return render(request, "providers/complaint.html", ctx)
