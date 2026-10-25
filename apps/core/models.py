from django.db import models
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from .images import optimize_image


class Bilingual(models.Model):
    """Every visible name is stored in Hindi and English, never machine-translated."""

    name_hi = models.CharField(_("name (Hindi)"), max_length=120)
    name_en = models.CharField(_("name (English)"), max_length=120)

    class Meta:
        abstract = True

    @property
    def name(self):
        return self.name_en if (get_language() or "hi").startswith("en") else self.name_hi

    def __str__(self):
        return self.name_en


class City(Bilingual):
    slug = models.SlugField(unique=True)
    lat = models.FloatField()
    lon = models.FloatField()
    is_live = models.BooleanField(_("live"), default=True)

    class Meta:
        verbose_name = _("city")
        verbose_name_plural = _("cities")
        ordering = ["name_en"]


class Area(Bilingual):
    """A mohalla. One map point is enough to measure distances."""

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="areas")
    slug = models.SlugField()
    lat = models.FloatField(help_text=_("Latitude of the mohalla's centre"))
    lon = models.FloatField(help_text=_("Longitude of the mohalla's centre"))
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("mohalla")
        verbose_name_plural = _("mohallas")
        ordering = ["name_en"]
        unique_together = [("city", "slug")]


class Category(Bilingual):
    slug = models.SlugField(unique=True)
    tagline_hi = models.CharField(max_length=160, blank=True)
    tagline_en = models.CharField(max_length=160, blank=True)
    icon = models.CharField(
        max_length=30,
        default="tool",
        help_text=_("Illustration key: electrician, plumber, appliance, bike, carpenter, beauty, painter"),
    )
    image = models.ImageField(upload_to="categories/", blank=True)
    color = models.CharField(max_length=7, default="#0F766E")
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("service")
        verbose_name_plural = _("services")
        ordering = ["sort_order", "name_en"]

    @property
    def tagline(self):
        return self.tagline_en if (get_language() or "hi").startswith("en") else self.tagline_hi

    def save(self, *args, **kwargs):
        optimize_image(self.image, max_width=900)
        super().save(*args, **kwargs)


class SubCategory(Bilingual):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("sub-service")
        verbose_name_plural = _("sub-services")
        ordering = ["sort_order", "id"]


class RateItem(Bilingual):
    """Indicative price shown on the rate card, e.g. 'Fan fitting from ₹150'."""

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="rate_items")
    price_from = models.PositiveIntegerField(_("price from (₹)"))
    unit_hi = models.CharField(max_length=40, blank=True)
    unit_en = models.CharField(max_length=40, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("rate card item")
        verbose_name_plural = _("rate card items")
        ordering = ["sort_order", "id"]

    @property
    def unit(self):
        return self.unit_en if (get_language() or "hi").startswith("en") else self.unit_hi
