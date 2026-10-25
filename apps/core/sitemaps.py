from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.providers.models import Provider

from .models import Category, City


class StaticSitemap(Sitemap):
    i18n = True
    changefreq = "weekly"

    def items(self):
        return ["home", "work_request", "join"]

    def location(self, item):
        return reverse(item)


class CategorySitemap(Sitemap):
    i18n = True
    changefreq = "daily"
    priority = 0.9

    def items(self):
        city = City.objects.filter(is_live=True).first()
        if not city:
            return []
        return [(city, c) for c in Category.objects.filter(is_active=True)]

    def location(self, item):
        city, cat = item
        return reverse("category_list", kwargs={"city_slug": city.slug, "slug": cat.slug})


class ProviderSitemap(Sitemap):
    i18n = True
    changefreq = "weekly"

    def items(self):
        return Provider.objects.filter(status=Provider.Status.LIVE)

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {"static": StaticSitemap, "services": CategorySitemap, "providers": ProviderSitemap}
