from urllib.parse import urlencode

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from unfold.decorators import action, display
from unfold.enums import ActionVariant

from apps.core.admin_base import KKAdmin
from apps.core.models import City

from .models import JoinRequest, Provider

STATUS_COLORS = {"live": "success", "draft": "info", "paused": "warning", "blocked": "danger"}


def go_live_problems(p):
    """What still has to be done before a worker can be shown on the site."""
    problems = []
    if not p.consent_given:
        problems.append("Consent not recorded")
    if not p.phone_verified:
        problems.append("Phone not verified")
    if not p.photo:
        problems.append("No profile photo (optional, but customers trust a face)")
    if not p.id_last4:
        problems.append("ID not checked (optional)")
    return problems


def _blocking(problems):
    return [x for x in problems if "optional" not in x]


@admin.register(Provider)
class ProviderAdmin(KKAdmin):
    list_display = ["worker", "category", "area", "phone", "status_label", "rating",
                    "missed_calls", "available_today", "is_featured"]
    list_display_links = ["worker"]
    list_filter = ["status", "category", "area", "available_today", "is_featured", "service_range", "gender"]
    list_editable = ["available_today"]
    search_fields = ["name_en", "name_hi", "phone"]
    filter_horizontal = ["subcategories"]
    list_select_related = ["category", "area"]
    readonly_fields = ["checklist", "photo_preview", "id_photo_link", "rating_avg", "rating_count", "jobs_done",
                       "missed_streak", "verified_at", "created_at", "updated_at", "public_link"]
    actions = ["make_live", "pause", "block", "mark_available", "mark_busy"]
    actions_row = ["row_make_live", "row_whatsapp"]
    actions_detail = ["detail_make_live", "detail_pause", "detail_open_page", "detail_whatsapp"]

    fieldsets = [
        ("Basic info", {
            "classes": ["tab"],
            "fields": ["checklist", ("name_hi", "name_en"), ("phone", "whatsapp"), "gender",
                       ("photo", "photo_preview"), ("bio_hi", "bio_en")],
        }),
        ("Work and area", {
            "classes": ["tab"],
            "fields": ["category", "subcategories", ("city", "area"), "service_range",
                       "experience_years", "available_today"],
            "description": "“Travels to” decides who sees this worker: only nearby mohallas (2.5 km) or all of Banda.",
        }),
        ("Verification", {
            "classes": ["tab"],
            "fields": [("phone_verified", "consent_given"), ("id_type", "id_last4"),
                       ("id_photo", "id_photo_link"), "onboarded_by", "verified_at"],
            "description": "Done in person. Never type the full Aadhaar number: only the last 4 digits, "
                           "and a photo with the other digits covered.",
        }),
        ("Status", {
            "classes": ["tab"],
            "fields": [("status", "status_note"), "is_featured", "public_link", "admin_notes"],
        }),
        ("Ratings and calls", {
            "classes": ["tab"],
            "fields": [("rating_avg", "rating_count"), ("jobs_done", "missed_streak"),
                       ("created_at", "updated_at")],
            "description": "Filled in automatically. A worker who misses 3 calls in a row is paused by itself.",
        }),
    ]

    # --- list columns ------------------------------------------------------------
    @display(description="Worker", header=True, ordering="name_en")
    def worker(self, obj):
        img = {"path": obj.photo.url, "width": 36, "height": 36} if obj.photo else None
        return [obj.name_en, obj.name_hi, obj.initials, img]

    @display(description="Status", ordering="status", label=STATUS_COLORS)
    def status_label(self, obj):
        return obj.status, obj.get_status_display()

    @display(description="Rating", ordering="rating_avg")
    def rating(self, obj):
        return "New" if obj.is_new else f"★ {obj.rating_avg:.1f} ({obj.rating_count})"

    @display(description="Missed calls", ordering="missed_streak",
             label={0: "success", 1: "info", 2: "warning", 3: "danger"})
    def missed_calls(self, obj):
        return min(obj.missed_streak, 3), obj.missed_streak

    # --- form helpers ------------------------------------------------------------
    @display(description="Ready to go live?")
    def checklist(self, obj):
        if not obj.pk:
            return "Fill in the details and save. Then you can approve the worker."
        problems = go_live_problems(obj)
        if not problems:
            return format_html('<span class="kk-ok">✓ Everything done</span>')
        return format_html('<ul class="kk-check">{}</ul>', format_html_join(
            "", '<li class="{}">{}</li>',
            (("kk-soft" if "optional" in x else "kk-bad", x) for x in problems)))

    @display(description="Preview")
    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="max-width:120px;border-radius:12px">', obj.photo.url)
        return "—"

    @display(description="ID photo")
    def id_photo_link(self, obj):
        if obj.id_photo:
            url = reverse("admin_private_file", kwargs={"name": obj.id_photo.name})
            return format_html('<a href="{}" target="_blank" class="text-primary-600">View ID (staff only) ↗</a>', url)
        return "—"

    @display(description="Public page")
    def public_link(self, obj):
        if obj.pk:
            return format_html('<a href="{0}" target="_blank" class="text-primary-600">{0}</a>',
                               obj.get_absolute_url())
        return "—"

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        city = City.objects.filter(is_live=True).first()
        if city and "city" not in initial:
            initial["city"] = city.pk
        initial.setdefault("onboarded_by", request.user.get_full_name() or request.user.username)
        return initial

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        join_id = request.GET.get("from_join")
        if not change and join_id:
            JoinRequest.objects.filter(pk=join_id).update(
                handled=True, notes=f"Profile created #{obj.pk}")

    # --- shared logic ------------------------------------------------------------
    def _make_live(self, request, providers):
        ok = 0
        for p in providers:
            missing = _blocking(go_live_problems(p))
            if missing:
                self.message_user(request, f"{p.name_en}: not live yet – {', '.join(missing)}.", messages.WARNING)
                continue
            p.status = Provider.Status.LIVE
            p.status_note = ""
            p.missed_streak = 0
            p.verified_at = p.verified_at or timezone.now()
            p.save()
            ok += 1
        if ok:
            self.message_user(request, f"{ok} worker(s) are now live on the website.", messages.SUCCESS)

    # --- bulk actions (tick rows, then choose) -------------------------------------
    @action(description="Approve and make live")
    def make_live(self, request, queryset):
        self._make_live(request, queryset)

    @action(description="Pause (hide from website)")
    def pause(self, request, queryset):
        n = queryset.update(status=Provider.Status.PAUSED)
        self.message_user(request, f"{n} paused.")

    @action(description="Block (remove for bad behaviour)")
    def block(self, request, queryset):
        n = queryset.update(status=Provider.Status.BLOCKED, is_featured=False)
        self.message_user(request, f"{n} blocked.")

    @action(description="Mark available today")
    def mark_available(self, request, queryset):
        queryset.update(available_today=True)

    @action(description="Mark busy today")
    def mark_busy(self, request, queryset):
        queryset.update(available_today=False)

    # --- buttons on each row ------------------------------------------------------
    @action(description="Make live", url_path="row-make-live", icon="check_circle")
    def row_make_live(self, request, object_id):
        self._make_live(request, Provider.objects.filter(pk=object_id))
        return redirect(request.headers.get("referer") or reverse("admin:providers_provider_changelist"))

    @action(description="WhatsApp", url_path="row-whatsapp", icon="chat")
    def row_whatsapp(self, request, object_id):
        p = Provider.objects.get(pk=object_id)
        return redirect(f"https://wa.me/91{p.wa_number}")

    # --- buttons at the top of the worker's page -------------------------------------
    @action(description="Approve and make live", url_path="make-live", icon="check_circle",
            variant=ActionVariant.SUCCESS)
    def detail_make_live(self, request, object_id):
        self._make_live(request, Provider.objects.filter(pk=object_id))
        return redirect(reverse("admin:providers_provider_change", args=[object_id]))

    @action(description="Pause", url_path="pause", icon="pause_circle", variant=ActionVariant.WARNING)
    def detail_pause(self, request, object_id):
        Provider.objects.filter(pk=object_id).update(status=Provider.Status.PAUSED)
        self.message_user(request, "Paused. The worker is hidden from the website.")
        return redirect(reverse("admin:providers_provider_change", args=[object_id]))

    @action(description="Open public page", url_path="open-page", icon="open_in_new")
    def detail_open_page(self, request, object_id):
        return redirect(Provider.objects.get(pk=object_id).get_absolute_url())

    @action(description="WhatsApp", url_path="whatsapp", icon="chat")
    def detail_whatsapp(self, request, object_id):
        return redirect(f"https://wa.me/91{Provider.objects.get(pk=object_id).wa_number}")


@admin.register(JoinRequest)
class JoinRequestAdmin(KKAdmin):
    list_display = ["person", "work", "area", "created_at", "state", "call"]
    list_filter = ["handled", "category", "area"]
    search_fields = ["name", "phone"]
    list_select_related = ["category", "area"]
    actions = ["mark_called"]
    actions_row = ["row_create_provider", "row_mark_called"]
    actions_detail = ["detail_create_provider"]
    fields = [("name", "phone"), ("category", "other_work"), "area", "handled", "notes"]

    @display(description="Person", header=True, ordering="name")
    def person(self, obj):
        return [obj.name, obj.phone, obj.name[:1].upper(), None]

    @display(description="Work")
    def work(self, obj):
        return obj.category.name_en if obj.category else (obj.other_work or "—")

    @display(description="Status", ordering="handled", label={"new": "warning", "done": "success"})
    def state(self, obj):
        return ("done", "Called back") if obj.handled else ("new", "New – call")

    @display(description="Contact")
    def call(self, obj):
        return format_html(
            '<a href="tel:+91{0}" class="kk-pill">Call</a> '
            '<a href="https://wa.me/91{0}" target="_blank" class="kk-pill kk-wa">WhatsApp</a>', obj.phone)

    def _create(self, request, object_id):
        jr = JoinRequest.objects.select_related("area", "category").get(pk=object_id)
        existing = Provider.objects.filter(phone=jr.phone).first()
        if existing:
            JoinRequest.objects.filter(pk=jr.pk).update(handled=True)
            self.message_user(request, f"{jr.phone} already has a worker profile. Opened it.", messages.INFO)
            return redirect(reverse("admin:providers_provider_change", args=[existing.pk]))
        params = {"name_en": jr.name, "name_hi": jr.name, "phone": jr.phone, "whatsapp": jr.phone,
                  "from_join": jr.pk}
        if jr.category_id:
            params["category"] = jr.category_id
        if jr.area_id:
            params["area"] = jr.area_id
            params["city"] = jr.area.city_id
        self.message_user(request, "Details copied from the join request. Add the photo, Hindi name and "
                                   "verification, then save.", messages.INFO)
        return redirect(f"{reverse('admin:providers_provider_add')}?{urlencode(params)}")

    @action(description="Create worker profile", url_path="create-provider", icon="person_add")
    def row_create_provider(self, request, object_id):
        return self._create(request, object_id)

    @action(description="Create worker profile", url_path="create-provider-detail", icon="person_add",
            variant=ActionVariant.PRIMARY)
    def detail_create_provider(self, request, object_id):
        return self._create(request, object_id)

    @action(description="Called back", url_path="mark-called", icon="done")
    def row_mark_called(self, request, object_id):
        JoinRequest.objects.filter(pk=object_id).update(handled=True)
        return redirect(request.headers.get("referer") or reverse("admin:providers_joinrequest_changelist"))

    @action(description="Mark as called back")
    def mark_called(self, request, queryset):
        queryset.update(handled=True)
