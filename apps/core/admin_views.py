"""Staff-only pages: the daily numbers, and the private ID photos."""
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.utils import timezone

from apps.accounts.models import Customer
from apps.ads.models import Banner, BannerDailyStat
from apps.leads.models import Complaint, Lead, WorkRequest
from apps.providers.models import JoinRequest, Provider, private_storage


def dashboard_data():
    today = timezone.localdate()
    since = today - timedelta(days=13)
    days = [since + timedelta(days=i) for i in range(14)]
    per_day = dict(
        Lead.objects.filter(created_at__date__gte=since)
        .values_list("created_at__date").annotate(n=Count("id")).values_list("created_at__date", "n")
    )
    series = [{"day": d, "n": per_day.get(d, 0)} for d in days]
    peak = max([s["n"] for s in series] + [1])
    for s in series:
        s["pct"] = round(100 * s["n"] / peak)

    week = today - timedelta(days=6)
    leads_week = Lead.objects.filter(created_at__date__gte=week)
    followed = leads_week.exclude(outcome=Lead.Outcome.UNKNOWN)
    done = followed.filter(outcome=Lead.Outcome.DONE).count()
    answered = followed.exclude(outcome=Lead.Outcome.NO_ANSWER).count()

    by_category = (leads_week.values("provider__category__name_en")
                   .annotate(n=Count("id")).order_by("-n"))
    by_area = (leads_week.values("area__name_en").annotate(n=Count("id")).order_by("-n")[:10])
    missing = (Provider.objects.filter(status=Provider.Status.LIVE, missed_streak__gte=2)
               .select_related("category").order_by("-missed_streak"))
    banners = (Banner.objects.filter(ends_on__gte=today - timedelta(days=30))
               .annotate(v=Sum("stats__views", filter=Q(stats__date__gte=today.replace(day=1))),
                         c=Sum("stats__clicks", filter=Q(stats__date__gte=today.replace(day=1))))
               .order_by("-is_active", "ends_on"))
    to_follow = (Lead.objects.filter(outcome=Lead.Outcome.UNKNOWN, followup_sent=False,
                                     created_at__date__lt=today, created_at__date__gte=today - timedelta(days=7))
                 .select_related("customer", "provider")[:30])

    return {
        "kpi": {
            "leads_today": Lead.objects.filter(created_at__date=today).count(),
            "leads_week": leads_week.count(),
            "done_rate": round(100 * done / followed.count()) if followed.count() else None,
            "answer_rate": round(100 * answered / followed.count()) if followed.count() else None,
            "live": Provider.objects.filter(status=Provider.Status.LIVE).count(),
            "drafts": Provider.objects.filter(status=Provider.Status.DRAFT).count(),
            "paused": Provider.objects.filter(status=Provider.Status.PAUSED).count(),
            "customers": Customer.objects.count(),
            "open_requests": WorkRequest.objects.filter(status=WorkRequest.Status.NEW).count(),
            "join_requests": JoinRequest.objects.filter(handled=False).count(),
            "complaints": Complaint.objects.filter(resolved=False).count(),
        },
        "series": series,
        "by_category": by_category,
        "by_area": by_area,
        "missing": missing,
        "banners": banners,
        "to_follow": to_follow,
        "today": today,
    }


def dashboard_callback(request, context):
    """Unfold calls this for the admin home page (templates/admin/index.html)."""
    context.update(dashboard_data())
    context["title"] = "Dashboard"
    return context


def dashboard(request):
    """Old address of the dashboard: it is now the admin home page."""
    return redirect("admin:index")


def private_file(request, name):
    """Stream an ID photo to staff only. Never linked from public pages."""
    if ".." in name or name.startswith("/"):
        raise Http404
    if not private_storage.exists(name):
        raise Http404
    url = None
    try:
        url = private_storage.url(name)
    except Exception:
        url = None
    if url and url.startswith("http"):
        return HttpResponseRedirect(url)  # signed, short-lived S3/R2 link
    return FileResponse(private_storage.open(name, "rb"))
