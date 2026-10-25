from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from unfold.decorators import action, display

from apps.core.admin_base import KKAdmin

from .models import Complaint, Lead, Rating, WorkRequest

OUTCOME_COLORS = {"unknown": "info", "done": "success", "no_answer": "danger", "no_show": "danger",
                  "price": "warning", "cancelled": "default"}


@admin.register(Lead)
class LeadAdmin(KKAdmin):
    list_display = ["created_at", "customer", "provider", "area", "mode", "outcome_label", "followup_sent",
                    "send_followup"]
    list_filter = ["outcome", "mode", "followup_sent", "provider__category", "area", "created_at"]
    search_fields = ["customer__phone", "provider__name_en", "provider__phone"]
    list_editable = ["followup_sent"]
    list_select_related = ["customer", "provider", "area"]
    date_hierarchy = "created_at"
    readonly_fields = ["customer", "provider", "area", "mode", "token", "created_at", "rating_link"]
    fields = [("customer", "provider"), ("area", "mode"), "outcome", "followup_sent", "rating_link",
              ("token", "created_at")]
    actions = ["outcome_done", "outcome_no_answer", "outcome_no_show"]
    actions_row = ["row_done", "row_no_answer"]

    def has_add_permission(self, request):
        return False  # a call is recorded only when a customer taps "show number"

    @display(description="Result", ordering="outcome", label=OUTCOME_COLORS)
    def outcome_label(self, obj):
        return obj.outcome, obj.get_outcome_display()

    @display(description="Ask for rating")
    def send_followup(self, obj):
        if obj.outcome != Lead.Outcome.UNKNOWN:
            return "—"
        return format_html('<a href="{}" target="_blank" class="kk-pill kk-wa">WhatsApp ↗</a>',
                           obj.followup_whatsapp_url())

    @display(description="Rating link")
    def rating_link(self, obj):
        return format_html('<a href="{0}" target="_blank" class="text-primary-600">{0}</a>', obj.rating_url())

    def save_model(self, request, obj, form, change):
        if change and "outcome" in form.changed_data:
            obj.set_outcome(obj.outcome)  # applies the auto-pause rule
        else:
            super().save_model(request, obj, form, change)

    def _bulk(self, request, queryset, outcome):
        for lead in queryset:
            lead.set_outcome(outcome)
        self.message_user(request, f"{len(queryset)} updated.")

    @action(description="Result: work done")
    def outcome_done(self, request, queryset):
        self._bulk(request, queryset, Lead.Outcome.DONE)

    @action(description="Result: worker did not answer")
    def outcome_no_answer(self, request, queryset):
        self._bulk(request, queryset, Lead.Outcome.NO_ANSWER)

    @action(description="Result: worker did not come")
    def outcome_no_show(self, request, queryset):
        self._bulk(request, queryset, Lead.Outcome.NO_SHOW)

    def _back(self, request):
        return redirect(request.headers.get("referer") or reverse("admin:leads_lead_changelist"))

    @action(description="Work done", url_path="row-done", icon="task_alt")
    def row_done(self, request, object_id):
        Lead.objects.get(pk=object_id).set_outcome(Lead.Outcome.DONE)
        return self._back(request)

    @action(description="Didn't answer", url_path="row-no-answer", icon="phone_missed")
    def row_no_answer(self, request, object_id):
        Lead.objects.get(pk=object_id).set_outcome(Lead.Outcome.NO_ANSWER)
        return self._back(request)


@admin.register(Rating)
class RatingAdmin(KKAdmin):
    list_display = ["created_at", "provider", "stars_label", "text", "is_approved"]
    list_filter = ["is_approved", "stars", "provider__category"]
    list_editable = ["is_approved"]
    search_fields = ["provider__name_en", "text"]
    readonly_fields = ["lead", "provider", "stars", "text", "created_at"]
    actions = ["approve", "hide"]

    def has_add_permission(self, request):
        return False  # ratings only come from real calls

    @display(description="Stars", ordering="stars",
             label={1: "danger", 2: "danger", 3: "warning", 4: "success", 5: "success"})
    def stars_label(self, obj):
        return obj.stars, "★" * obj.stars

    @action(description="Show review text on website")
    def approve(self, request, queryset):
        for r in queryset:
            r.is_approved = True
            r.save()

    @action(description="Hide review text")
    def hide(self, request, queryset):
        for r in queryset:
            r.is_approved = False
            r.save()


@admin.register(Complaint)
class ComplaintAdmin(KKAdmin):
    list_display = ["created_at", "provider", "reason", "phone", "is_upheld", "resolved", "strikes"]
    list_filter = ["resolved", "is_upheld", "reason"]
    list_editable = ["is_upheld", "resolved"]
    search_fields = ["provider__name_en", "phone", "details"]
    list_select_related = ["provider"]

    @display(description="True complaints so far", label={"ok": "success", "warn": "warning", "bad": "danger"})
    def strikes(self, obj):
        n = obj.provider.complaints.filter(is_upheld=True).count()
        level = "bad" if n >= 3 else "warn" if n else "ok"
        return level, n


@admin.register(WorkRequest)
class WorkRequestAdmin(KKAdmin):
    list_display = ["number_display", "created_at", "description", "category", "area", "when", "phone",
                    "status_label", "assigned_provider", "call"]
    list_filter = ["status", "when", "category", "area"]
    list_editable = ["assigned_provider"]
    search_fields = ["description", "phone"]
    list_select_related = ["category", "area", "assigned_provider"]
    autocomplete_fields = ["assigned_provider"]
    actions = ["mark_matched", "mark_closed"]

    @display(description="No.")
    def number_display(self, obj):
        return obj.number

    @display(description="Status", ordering="status",
             label={"new": "warning", "matched": "info", "closed": "success"})
    def status_label(self, obj):
        return obj.status, obj.get_status_display()

    @display(description="Contact")
    def call(self, obj):
        return format_html('<a href="tel:+91{0}" class="kk-pill">Call</a> '
                           '<a href="https://wa.me/91{0}" target="_blank" class="kk-pill kk-wa">WhatsApp</a>',
                           obj.phone)

    @action(description="Worker arranged")
    def mark_matched(self, request, queryset):
        queryset.update(status=WorkRequest.Status.MATCHED)

    @action(description="Close")
    def mark_closed(self, request, queryset):
        queryset.update(status=WorkRequest.Status.CLOSED)
