from django.contrib import admin
from django.utils.html import format_html
from unfold.decorators import display

from .admin_base import KKAdmin, KKTabularInline
from .models import Area, Category, City, RateItem, SubCategory


@admin.register(City)
class CityAdmin(KKAdmin):
    list_display = ["name_en", "name_hi", "slug", "is_live"]
    prepopulated_fields = {"slug": ["name_en"]}


@admin.register(Area)
class AreaAdmin(KKAdmin):
    list_display = ["name_en", "name_hi", "city", "provider_count", "map_link", "is_active"]
    list_filter = ["city", "is_active"]
    list_editable = ["is_active"]
    search_fields = ["name_en", "name_hi"]
    prepopulated_fields = {"slug": ["name_en"]}
    fieldsets = [
        ("Name", {"fields": [("name_hi", "name_en"), ("city", "slug"), "is_active"]}),
        ("Location on the map", {
            "fields": [("lat", "lon")],
            "description": "Open Google Maps, long-press the centre of the mohalla and copy the two numbers. "
                           "Used to show the nearest workers first.",
        }),
    ]

    @display(description="Map")
    def map_link(self, obj):
        return format_html(
            '<a href="https://www.google.com/maps?q={},{}" target="_blank" rel="noopener" '
            'class="text-primary-600 font-medium">Open map ↗</a>', obj.lat, obj.lon)

    @display(description="Workers")
    def provider_count(self, obj):
        return obj.providers.count()


class SubCategoryInline(KKTabularInline):
    model = SubCategory
    extra = 0
    verbose_name = "type of work"
    verbose_name_plural = "Types of work (shown as filters)"


class RateItemInline(KKTabularInline):
    model = RateItem
    extra = 0
    verbose_name = "rate"
    verbose_name_plural = "Rate list (shown on the service page)"


@admin.register(Category)
class CategoryAdmin(KKAdmin):
    list_display = ["name_en", "name_hi", "live_providers", "sort_order", "is_active"]
    list_editable = ["sort_order", "is_active"]
    prepopulated_fields = {"slug": ["name_en"]}
    inlines = [SubCategoryInline, RateItemInline]

    @display(description="Live workers", label=True)
    def live_providers(self, obj):
        return obj.providers.filter(status="live").count()
