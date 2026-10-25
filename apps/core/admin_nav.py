"""
Sidebar of the admin panel, grouped by the job to do rather than by Django app.

Imported from settings.py, so nothing here may import models at module level.
Badges and permissions are looked up lazily, on each request.
"""
from django.urls import reverse_lazy
from django.utils.text import format_lazy


def perm(codename):
    """Show a sidebar link only to staff who are allowed to open it."""
    def check(request):
        return request.user.has_perm(codename)
    return check


def superuser_only(request):
    return request.user.is_superuser


def _count(n):
    return n or None  # None hides the badge; 0 would show "0"


# --- red/amber numbers next to sidebar links ------------------------------------
def badge_join_requests(request):
    from apps.providers.models import JoinRequest
    return _count(JoinRequest.objects.filter(handled=False).count())


def badge_drafts(request):
    from apps.providers.models import Provider
    return _count(Provider.objects.filter(status=Provider.Status.DRAFT).count())


def badge_work_requests(request):
    from apps.leads.models import WorkRequest
    return _count(WorkRequest.objects.filter(status=WorkRequest.Status.NEW).count())


def badge_complaints(request):
    from apps.leads.models import Complaint
    return _count(Complaint.objects.filter(resolved=False).count())


def badge_ratings(request):
    from apps.leads.models import Rating
    return _count(Rating.objects.filter(is_approved=False).exclude(text="").count())


def environment_badge(request):
    """Small label in the top bar so nobody confuses the laptop copy with the live site."""
    from django.conf import settings
    if settings.DEBUG:
        return ["Laptop copy (test)", "warning"]
    return ["Live site", "success"]


def _cl(model):
    return reverse_lazy(f"admin:{model}_changelist")


UNFOLD_SIDEBAR = [
    {
        "title": "Today",
        "separator": False,
        "items": [
            {"title": "Dashboard", "icon": "space_dashboard", "link": reverse_lazy("admin:index")},
            {"title": "Join requests (call back)", "icon": "person_add",
             "link": format_lazy("{}?handled__exact=0", _cl("providers_joinrequest")),
             "badge": "apps.core.admin_nav.badge_join_requests",
             "permission": perm("providers.view_joinrequest")},
            {"title": "Kaam batao (match a worker)", "icon": "assignment",
             "link": format_lazy("{}?status__exact=new", _cl("leads_workrequest")),
             "badge": "apps.core.admin_nav.badge_work_requests",
             "permission": perm("leads.view_workrequest")},
            {"title": "Complaints", "icon": "report",
             "link": format_lazy("{}?resolved__exact=0", _cl("leads_complaint")),
             "badge": "apps.core.admin_nav.badge_complaints",
             "permission": perm("leads.view_complaint")},
        ],
    },
    {
        "title": "Workers",
        "separator": True,
        "items": [
            {"title": "All workers", "icon": "engineering", "link": _cl("providers_provider"),
             "permission": perm("providers.view_provider")},
            {"title": "Waiting for approval", "icon": "pending_actions",
             "link": format_lazy("{}?status__exact=draft", _cl("providers_provider")),
             "badge": "apps.core.admin_nav.badge_drafts",
             "permission": perm("providers.view_provider")},
            {"title": "Add a new worker", "icon": "add_circle",
             "link": reverse_lazy("admin:providers_provider_add"),
             "permission": perm("providers.add_provider")},
        ],
    },
    {
        "title": "Customers and calls",
        "separator": True,
        "items": [
            {"title": "Calls / contacts", "icon": "call", "link": _cl("leads_lead"),
             "permission": perm("leads.view_lead")},
            {"title": "Ratings", "icon": "star", "link": _cl("leads_rating"),
             "badge": "apps.core.admin_nav.badge_ratings",
             "permission": perm("leads.view_rating")},
            {"title": "Customers", "icon": "group", "link": _cl("accounts_customer"),
             "permission": perm("accounts.view_customer")},
        ],
    },
    {
        "title": "Ads",
        "separator": True,
        "items": [
            {"title": "Shop banners", "icon": "campaign", "link": _cl("ads_banner"),
             "permission": perm("ads.view_banner")},
        ],
    },
    {
        "title": "Settings",
        "separator": True,
        "collapsible": True,
        "items": [
            {"title": "Services and rates", "icon": "category", "link": _cl("core_category"),
             "permission": perm("core.view_category")},
            {"title": "Mohallas", "icon": "location_on", "link": _cl("core_area"),
             "permission": perm("core.view_area")},
            {"title": "Cities", "icon": "location_city", "link": _cl("core_city"),
             "permission": superuser_only},
            {"title": "Staff logins", "icon": "badge", "link": _cl("auth_user"),
             "permission": superuser_only},
            {"title": "Staff roles", "icon": "admin_panel_settings", "link": _cl("auth_group"),
             "permission": superuser_only},
        ],
    },
]
