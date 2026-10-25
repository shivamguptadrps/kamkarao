from django.contrib import admin
from unfold.decorators import display

from apps.core.admin_base import KKAdmin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(KKAdmin):
    list_display = ["phone", "name", "created_at", "last_seen_at", "lead_count", "blocked"]
    list_filter = ["is_blocked"]
    search_fields = ["phone", "name"]
    readonly_fields = ["created_at", "last_seen_at"]

    def has_add_permission(self, request):
        return False  # customers sign up themselves on the website

    @display(description="Contacts seen")
    def lead_count(self, obj):
        return obj.leads.count()

    @display(description="Status", ordering="is_blocked", label={True: "danger", False: "success"})
    def blocked(self, obj):
        return obj.is_blocked, ("Blocked" if obj.is_blocked else "OK")
