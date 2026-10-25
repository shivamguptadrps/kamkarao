"""Who shows up for a customer, and in what order."""
from dataclasses import dataclass

from django.conf import settings

from apps.core.geo import km_between

from .models import Provider


@dataclass
class Filters:
    sub: int | None = None
    today: bool = False
    verified: bool = False
    rated: bool = False
    female: bool = False
    sort: str = "near"

    @classmethod
    def from_request(cls, request):
        g = request.GET
        sub = g.get("sub")
        return cls(
            sub=int(sub) if sub and sub.isdigit() else None,
            today=g.get("today") == "1",
            verified=g.get("verified") == "1",
            rated=g.get("rated") == "1",
            female=g.get("female") == "1",
            sort=g.get("sort") if g.get("sort") in {"near", "rating", "exp"} else "near",
        )

    @property
    def active_count(self):
        return sum([bool(self.sub), self.today, self.verified, self.rated, self.female])


def ranked_providers(category, city, area, f: Filters):
    qs = (
        Provider.objects.filter(status=Provider.Status.LIVE, category=category, city=city)
        .select_related("area", "category")
        .prefetch_related("subcategories")
    )
    if f.sub:
        qs = qs.filter(subcategories__id=f.sub)
    if f.today:
        qs = qs.filter(available_today=True)
    if f.verified:
        qs = qs.exclude(id_type="").filter(phone_verified=True)
    if f.rated:
        qs = qs.filter(rating_avg__gte=4.5, rating_count__gte=settings.NEW_PROVIDER_MIN_RATINGS)
    if f.female:
        qs = qs.filter(gender=Provider.Gender.FEMALE)

    results = []
    for p in qs.distinct():
        if area is not None:
            p.distance_km = km_between(area.lat, area.lon, p.area.lat, p.area.lon)
            if p.service_range == Provider.Range.NEARBY and p.distance_km > settings.NEARBY_ONLY_KM:
                continue
            p.same_area = p.area_id == area.id
        else:
            p.distance_km = None
            p.same_area = False
        results.append(p)

    def score_rating(p):
        # New providers sit in the middle rather than at the bottom.
        return float(p.rating_avg) if not p.is_new else 4.0

    if f.sort == "rating":
        results.sort(key=lambda p: (-score_rating(p), -p.rating_count))
    elif f.sort == "exp":
        results.sort(key=lambda p: -p.experience_years)
    else:
        results.sort(key=lambda p: (
            not p.is_featured,
            p.distance_km if p.distance_km is not None else 0,
            -score_rating(p),
        ))
    return results
