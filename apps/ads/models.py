from django.db import models
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from apps.core.images import optimize_image
from apps.core.models import Area, Category, City


class Banner(models.Model):
    """A local shop's advert. Either an uploaded image, or a text banner built from the fields."""

    class Placement(models.TextChoices):
        HOME = "home", _("Home page strip")
        LISTING = "listing", _("Inside a service listing")
        PROFILE = "profile", _("Bottom of a provider profile")

    class Theme(models.TextChoices):
        TEAL = "teal", _("Teal")
        SAFFRON = "saffron", _("Saffron")
        INDIGO = "indigo", _("Indigo")
        ROSE = "rose", _("Rose")
        SLATE = "slate", _("Slate")

    shop_name = models.CharField(_("shop name"), max_length=100)
    title_hi = models.CharField(_("headline (Hindi)"), max_length=90)
    title_en = models.CharField(_("headline (English)"), max_length=90)
    subtitle_hi = models.CharField(_("sub-line (Hindi)"), max_length=140, blank=True)
    subtitle_en = models.CharField(_("sub-line (English)"), max_length=140, blank=True)
    image = models.ImageField(_("banner image (optional)"), upload_to="banners/", blank=True,
                              help_text=_("Wide image, about 1200×400. Leave empty to show a text banner."))
    theme = models.CharField(max_length=10, choices=Theme.choices, default=Theme.TEAL)
    link = models.CharField(_("link"), max_length=300, blank=True,
                            help_text=_("tel:9876543210, https://wa.me/919876543210 or a website"))
    cta_hi = models.CharField(_("button text (Hindi)"), max_length=30, default="कॉल करें")
    cta_en = models.CharField(_("button text (English)"), max_length=30, default="Call now")

    placement = models.CharField(max_length=10, choices=Placement.choices, default=Placement.HOME)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="banners")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True,
                                 help_text=_("Show only on this service's pages (empty = all)"))
    areas = models.ManyToManyField(Area, blank=True, help_text=_("Show only to these mohallas (empty = all)"))
    starts_on = models.DateField(default=timezone.localdate)
    ends_on = models.DateField()
    is_active = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(default=0, help_text=_("Higher shows first"))
    monthly_price = models.PositiveIntegerField(_("price per month (₹)"), default=0)
    advertiser_phone = models.CharField(max_length=10, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("banner")
        verbose_name_plural = _("banners")
        ordering = ["-priority", "-starts_on"]

    def __str__(self):
        return f"{self.shop_name} ({self.get_placement_display()})"

    def _l(self, hi, en):
        return en if (get_language() or "hi").startswith("en") else hi

    @property
    def title(self):
        return self._l(self.title_hi, self.title_en)

    @property
    def subtitle(self):
        return self._l(self.subtitle_hi, self.subtitle_en)

    @property
    def cta(self):
        return self._l(self.cta_hi, self.cta_en)

    @property
    def is_running(self):
        today = timezone.localdate()
        return self.is_active and self.starts_on <= today <= self.ends_on

    def click_url(self):
        return reverse("banner_click", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        optimize_image(self.image, max_width=1200)
        super().save(*args, **kwargs)


class BannerDailyStat(models.Model):
    banner = models.ForeignKey(Banner, on_delete=models.CASCADE, related_name="stats")
    date = models.DateField(default=timezone.localdate)
    views = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("banner", "date")]
        ordering = ["-date"]

    @classmethod
    def bump(cls, banner_ids, field):
        today = timezone.localdate()
        for bid in banner_ids:
            obj, _created = cls.objects.get_or_create(banner_id=bid, date=today)
            cls.objects.filter(pk=obj.pk).update(**{field: F(field) + 1})


def banners_for(request, placement, city, category=None, area=None, limit=None):
    """Running banners for a slot, at most MAX_BANNERS_PER_PAGE, counted as one view each."""
    from django.conf import settings

    if city is None:
        return []
    today = timezone.localdate()
    qs = Banner.objects.filter(
        is_active=True, starts_on__lte=today, ends_on__gte=today, placement=placement, city=city
    )
    if category is not None:
        qs = qs.filter(models.Q(category=category) | models.Q(category__isnull=True))
    else:
        qs = qs.filter(category__isnull=True)
    banners = []
    for b in qs.prefetch_related("areas")[:10]:
        allowed = list(b.areas.all())
        if allowed and (area is None or area not in allowed):
            continue
        banners.append(b)
    banners = banners[: limit or settings.MAX_BANNERS_PER_PAGE]
    if banners and not getattr(request, "_kk_skip_views", False):
        BannerDailyStat.bump([b.pk for b in banners], "views")
    return banners
