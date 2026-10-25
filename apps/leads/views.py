from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _

from apps.core.models import Category
from apps.core.phone import normalize_phone
from apps.core.search import match_category
from apps.core.selection import current_area, current_city

from .models import Lead, Rating, WorkRequest


def rate(request, token):
    """The link sent on WhatsApp the day after a contact: did the work happen, and how was it?"""
    lead = get_object_or_404(Lead.objects.select_related("provider", "provider__category"), token=token)
    already = Rating.objects.filter(lead=lead).first()
    ctx = {"lead": lead, "p": lead.provider, "already": already, "outcomes": [
        ("done", _("Yes, the work is done")),
        ("no_answer", _("He did not pick up")),
        ("no_show", _("He did not come")),
        ("price", _("Price was too high")),
        ("cancelled", _("I cancelled it myself")),
    ]}
    if request.method == "POST" and not already:
        outcome = request.POST.get("outcome")
        if outcome not in Lead.Outcome.values or outcome == Lead.Outcome.UNKNOWN:
            ctx["error"] = _("Please tell us what happened.")
            return render(request, "leads/rate.html", ctx)
        stars = 0
        if outcome == Lead.Outcome.DONE:
            try:
                stars = int(request.POST.get("stars", 0))
            except ValueError:
                stars = 0
            if not 1 <= stars <= 5:
                ctx["error"] = _("Please choose 1 to 5 stars.")
                return render(request, "leads/rate.html", ctx)
        lead.set_outcome(outcome)
        if outcome == Lead.Outcome.DONE:
            Rating.objects.create(
                lead=lead, provider=lead.provider, stars=stars,
                text=(request.POST.get("text") or "").strip()[:400],
            )
        ctx["thanks"] = True
    return render(request, "leads/rate.html", ctx)


def work_request(request):
    city = current_city(request)
    area = current_area(request, city)
    ctx = {
        "categories": Category.objects.filter(is_active=True),
        "areas": city.areas.filter(is_active=True) if city else [],
        "when_choices": WorkRequest.When.choices,
        "form": {"text": request.GET.get("text", ""), "area": area.pk if area else ""},
    }
    if request.method == "POST":
        text = (request.POST.get("text") or "").strip()
        phone_raw = request.POST.get("phone") or (request.customer.phone if request.customer else "")
        ctx["form"] = request.POST
        if len(text) < 3:
            ctx["error"] = _("Please describe the work in a few words.")
            return render(request, "leads/work_request.html", ctx)
        try:
            phone = normalize_phone(phone_raw)
        except ValidationError as e:
            ctx["error"] = e.messages[0]
            return render(request, "leads/work_request.html", ctx)
        when = request.POST.get("when")
        wr = WorkRequest.objects.create(
            customer=request.customer, phone=phone, description=text[:400],
            category=match_category(text),
            area=ctx["areas"].filter(pk=request.POST.get("area") or 0).first() if city else None,
            when=when if when in WorkRequest.When.values else WorkRequest.When.TODAY,
        )
        return render(request, "leads/work_request.html", {**ctx, "done": wr})
    return render(request, "leads/work_request.html", ctx)
