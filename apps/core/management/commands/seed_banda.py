from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Area, Category, City, RateItem, SubCategory
from apps.core.seed import banda

PHOTOS = Path(__file__).resolve().parents[2] / "seed" / "photos"


class Command(BaseCommand):
    help = "Create Banda city, its mohallas and the launch services. Safe to run again."

    @transaction.atomic
    def handle(self, *args, **opts):
        city, _ = City.objects.update_or_create(slug=banda.CITY["slug"], defaults={
            k: v for k, v in banda.CITY.items() if k != "slug"})
        for slug, en, hi, lat, lon in banda.AREAS:
            Area.objects.update_or_create(city=city, slug=slug, defaults={
                "name_en": en, "name_hi": hi, "lat": lat, "lon": lon})
        for (slug, en, hi, icon, sort, tag_en, tag_hi, subs, rates) in banda.CATEGORIES:
            cat, created = Category.objects.update_or_create(slug=slug, defaults={
                "name_en": en, "name_hi": hi, "icon": icon, "sort_order": sort,
                "tagline_en": tag_en, "tagline_hi": tag_hi})
            if not cat.image and (PHOTOS / f"{icon}.jpg").exists():
                with open(PHOTOS / f"{icon}.jpg", "rb") as fh:
                    cat.image = File(fh, name=f"{slug}.jpg")  # resized to WebP on save
                    cat.save()
            for i, (s_en, s_hi) in enumerate(subs):
                SubCategory.objects.update_or_create(category=cat, name_en=s_en, defaults={
                    "name_hi": s_hi, "sort_order": i})
            for i, (r_en, r_hi, price, u_en, u_hi) in enumerate(rates):
                RateItem.objects.update_or_create(category=cat, name_en=r_en, defaults={
                    "name_hi": r_hi, "price_from": price, "unit_en": u_en, "unit_hi": u_hi, "sort_order": i})
        self.stdout.write(self.style.SUCCESS(
            f"Banda ready: {city.areas.count()} mohallas, {Category.objects.count()} services."))
