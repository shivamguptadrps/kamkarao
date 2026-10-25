from django.conf import settings
from django.core.files.storage import FileSystemStorage, storages
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import LazyObject
from django.utils.text import slugify
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from apps.core.images import optimize_image
from apps.core.models import Area, Category, City, SubCategory
from apps.core.phone import masked_phone, normalize_phone, pretty_phone


class PrivateStorage(LazyObject):
    """ID photos: a private S3 bucket if configured, else a folder the web server never serves."""

    def _setup(self):
        if "private" in settings.STORAGES:
            self._wrapped = storages["private"]
        else:
            self._wrapped = FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT, base_url=None)


private_storage = PrivateStorage()


class Provider(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        LIVE = "live", _("Live")
        PAUSED = "paused", _("Paused")
        BLOCKED = "blocked", _("Blocked")

    class Range(models.TextChoices):
        NEARBY = "nearby", _("Nearby only")
        CITY = "city", _("All of the city")

    class IdType(models.TextChoices):
        AADHAAR = "aadhaar", _("Aadhaar (masked)")
        VOTER = "voter", _("Voter ID")
        DL = "dl", _("Driving licence")
        PAN = "pan", _("PAN card")
        OTHER = "other", _("Other government ID")

    class Gender(models.TextChoices):
        MALE = "m", _("Male")
        FEMALE = "f", _("Female")
        OTHER = "o", _("Other")

    # Who
    name_hi = models.CharField(_("name (Hindi)"), max_length=120)
    name_en = models.CharField(_("name (English)"), max_length=120)
    phone = models.CharField(_("mobile number"), max_length=10, unique=True)
    whatsapp = models.CharField(_("WhatsApp number"), max_length=10, blank=True,
                                help_text=_("Leave empty if same as mobile"))
    gender = models.CharField(max_length=1, choices=Gender.choices, default=Gender.MALE)
    photo = models.ImageField(_("profile photo"), upload_to="providers/", blank=True)
    bio_hi = models.CharField(_("short intro (Hindi)"), max_length=220, blank=True)
    bio_en = models.CharField(_("short intro (English)"), max_length=220, blank=True)

    # What and where
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="providers")
    subcategories = models.ManyToManyField(SubCategory, blank=True, related_name="providers")
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="providers")
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="providers",
                             verbose_name=_("home mohalla"))
    service_range = models.CharField(_("travels to"), max_length=10, choices=Range.choices,
                                     default=Range.CITY)
    experience_years = models.PositiveSmallIntegerField(_("years of experience"), default=1)
    available_today = models.BooleanField(_("available today"), default=True)

    # Verification (done in person by the field team)
    id_type = models.CharField(_("ID seen"), max_length=10, choices=IdType.choices, blank=True)
    id_last4 = models.CharField(_("last 4 digits of ID"), max_length=4, blank=True)
    id_photo = models.ImageField(_("ID photo (private)"), upload_to="ids/", storage=private_storage,
                                 blank=True)
    phone_verified = models.BooleanField(_("phone verified by OTP"), default=False)
    consent_given = models.BooleanField(_("consent recorded"), default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    onboarded_by = models.CharField(_("field person"), max_length=80, blank=True)

    # Status and quality
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    status_note = models.CharField(max_length=200, blank=True)
    is_featured = models.BooleanField(_("featured (paid top slot)"), default=False)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)
    jobs_done = models.PositiveIntegerField(default=0)
    missed_streak = models.PositiveSmallIntegerField(default=0)
    admin_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("provider")
        verbose_name_plural = _("providers")
        ordering = ["-is_featured", "-rating_avg", "name_en"]

    def __str__(self):
        return f"{self.name_en} ({self.category})"

    @property
    def name(self):
        return self.name_en if (get_language() or "hi").startswith("en") else self.name_hi

    @property
    def first_name(self):
        return self.name.split(" ")[0]

    @property
    def bio(self):
        return self.bio_en if (get_language() or "hi").startswith("en") else self.bio_hi

    @property
    def initials(self):
        return "".join(w[0] for w in self.name_en.split()[:2]).upper()

    @property
    def is_verified(self):
        return bool(self.id_type and self.phone_verified)

    @property
    def is_new(self):
        return self.rating_count < settings.NEW_PROVIDER_MIN_RATINGS

    @property
    def wa_number(self):
        return self.whatsapp or self.phone

    @property
    def phone_pretty(self):
        return pretty_phone(self.phone)

    @property
    def phone_masked(self):
        return masked_phone(self.phone)

    @property
    def slug(self):
        return slugify(self.name_en) or "provider"

    def get_absolute_url(self):
        return reverse("provider_detail", kwargs={"pk": self.pk, "slug": self.slug})

    def answer_rate(self):
        """Share of followed-up leads where the provider picked up. None until there is enough data."""
        from apps.leads.models import Lead

        known = self.leads.exclude(outcome=Lead.Outcome.UNKNOWN)
        total = known.count()
        if total < 5:
            return None
        missed = known.filter(outcome=Lead.Outcome.NO_ANSWER).count()
        return round(100 * (total - missed) / total)

    def clean(self):
        from django.core.exceptions import ValidationError

        try:
            self.phone = normalize_phone(self.phone)
            if self.whatsapp:
                self.whatsapp = normalize_phone(self.whatsapp)
        except ValidationError as e:
            raise ValidationError({"phone": e.messages})
        if self.id_last4 and not self.id_last4.isalnum():
            raise ValidationError({"id_last4": _("Only the last 4 characters of the ID.")})
        if self.status == self.Status.LIVE and not (self.consent_given and self.phone_verified):
            raise ValidationError(_("Record consent and verify the phone before making a profile live."))

    def save(self, *args, **kwargs):
        optimize_image(self.photo, max_width=480)
        optimize_image(self.id_photo, max_width=1200)
        if self.id_type and self.phone_verified and not self.verified_at:
            self.verified_at = timezone.now()
        super().save(*args, **kwargs)


class JoinRequest(models.Model):
    """'Join as provider' form on the site. A callback request, never a live profile."""

    name = models.CharField(_("name"), max_length=120)
    phone = models.CharField(_("mobile number"), max_length=10)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    other_work = models.CharField(_("other work"), max_length=120, blank=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    handled = models.BooleanField(_("called back"), default=False)
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("join request")
        verbose_name_plural = _("join requests")
        ordering = ["handled", "-created_at"]

    def __str__(self):
        return f"{self.name} {self.phone}"
