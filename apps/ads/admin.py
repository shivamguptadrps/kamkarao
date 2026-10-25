from django.contrib import admin
from django.db.models import Sum
from django.utils import timezone
from django.utils.html import format_html
from unfold.decorators import display

from apps.core.admin_base import KKAdmin, KKTabularInline

from .models import Banner, BannerDailyStat


class StatInline(KKTabularInline):
    model = BannerDailyStat
    extra = 0
    can_delete = False
    readonly_fields = ["date", "views", "clicks"]
    max_num = 0
    ordering = ["-date"]
    tab = True
    verbose_name_plural = "Daily views and clicks"


@admin.register(Banner)
class BannerAdmin(KKAdmin):
    list_display = ["preview", "shop_name", "placement", "category", "ends_on", "state",
                    "views_month", "clicks_month", "monthly_price", "is_active"]
    list_display_links = ["preview", "shop_name"]
    list_filter = ["placement", "is_active", "category", "city"]
    list_editable = ["is_active"]
    search_fields = ["shop_name", "title_en", "title_hi"]
    filter_horizontal = ["areas"]
    inlines = [StatInline]
    fieldsets = [
        ("Shop", {"classes": ["tab"], "fields": ["shop_name", "advertiser_phone", "monthly_price"]}),
        ("What it shows", {"classes": ["tab"],
                           "fields": [("title_hi", "title_en"), ("subtitle_hi", "subtitle_en"),
                                      ("cta_hi", "cta_en"), "link", "image", "theme"],
                           "description": "No image? A clean text banner is made from these lines. "
                                          "Link: a phone number like tel:+919876543210, or a website."}),
        ("Where and when", {"classes": ["tab"],
                            "fields": ["placement", "city", "category", "areas", ("starts_on", "ends_on"),
                                       "priority", "is_active"]}),
    ]

    def _month(self, obj, field):
        start = timezone.localdate().replace(day=1)
        return obj.stats.filter(date__gte=start).aggregate(n=Sum(field))["n"] or 0

    @display(description="Views (month)")
    def views_month(self, obj):
        return self._month(obj, "views")

    @display(description="Clicks (month)")
    def clicks_month(self, obj):
        return self._month(obj, "clicks")

    @display(description="Running", label={"on": "success", "off": "default", "ended": "danger"})
    def state(self, obj):
        if obj.is_running:
            return "on", "Showing"
        if obj.ends_on and obj.ends_on < timezone.localdate():
            return "ended", "Ended"
        return "off", "Not showing"

    @display(description="")
    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:34px;border-radius:6px">', obj.image.url)
        return format_html('<span class="kk-pill">text banner</span>')
