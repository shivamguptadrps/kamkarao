import secrets

from django.conf import settings
from django.db import models, transaction
from django.db.models import Avg, Count
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Customer
from apps.core.models import Area, Category
from apps.providers.models import Provider


def _token():
    return secrets.token_urlsafe(9)


class Lead(models.Model):
    """One customer revealing one provider's number. The core business metric."""

    class Mode(models.TextChoices):
        CALL = "call", _("Call")
        WHATSAPP = "wa", _("WhatsApp")

    class Outcome(models.TextChoices):
        UNKNOWN = "unknown", _("Not followed up yet")
        DONE = "done", _("Work done")
        NO_ANSWER = "no_answer", _("Provider did not answer")
        NO_SHOW = "no_show", _("Provider did not come")
        PRICE = "price", _("Price too high")
        CANCELLED = "cancelled", _("Customer cancelled")

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="leads")
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="leads")
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    mode = models.CharField(max_length=4, choices=Mode.choices, default=Mode.CALL)
    outcome = models.CharField(max_length=12, choices=Outcome.choices, default=Outcome.UNKNOWN,
                               db_index=True)
    token = models.CharField(max_length=20, unique=True, default=_token)
    followup_sent = models.BooleanField(_("rating link sent"), default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("lead")
        verbose_name_plural = _("leads")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer} → {self.provider}"

    def rating_url(self):
        return settings.SITE_URL + reverse("rate", kwargs={"token": self.token})

    def followup_whatsapp_url(self):
        from urllib.parse import quote

        text = (
            f"नमस्ते! KamKarao से आपने कल {self.provider.name_hi} से संपर्क किया था। "
            f"क्या काम हो गया? 1 मिनट में बताइए: {self.rating_url()}"
        )
        return f"https://wa.me/91{self.customer.phone}?text={quote(text)}"

    @transaction.atomic
    def set_outcome(self, outcome):
        """Record what happened and apply the auto-pause rule for missed calls."""
        self.outcome = outcome
        self.save(update_fields=["outcome"])
        p = Provider.objects.select_for_update().get(pk=self.provider_id)
        if outcome == self.Outcome.NO_ANSWER:
            p.missed_streak += 1
            if p.missed_streak >= settings.AUTO_PAUSE_MISSED_LEADS and p.status == Provider.Status.LIVE:
                p.status = Provider.Status.PAUSED
                p.status_note = "Auto-paused: missed %d leads in a row" % p.missed_streak
        elif outcome in (self.Outcome.DONE, self.Outcome.PRICE, self.Outcome.CANCELLED):
            p.missed_streak = 0
        if outcome == self.Outcome.DONE:
            p.jobs_done = p.leads.filter(outcome=self.Outcome.DONE).count()
        p.save(update_fields=["missed_streak", "status", "status_note", "jobs_done"])


class Rating(models.Model):
    """Only a customer with a recorded lead can rate, once per lead."""

    lead = models.OneToOneField(Lead, on_delete=models.CASCADE, related_name="rating")
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="ratings")
    stars = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    text = models.CharField(_("review"), max_length=400, blank=True)
    is_approved = models.BooleanField(_("show review text"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("rating")
        verbose_name_plural = _("ratings")
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        refresh_provider_rating(self.provider)


def refresh_provider_rating(provider):
    agg = provider.ratings.aggregate(avg=Avg("stars"), n=Count("id"))
    provider.rating_avg = round(agg["avg"] or 0, 2)
    provider.rating_count = agg["n"]
    provider.save(update_fields=["rating_avg", "rating_count"])


class Complaint(models.Model):
    class Reason(models.TextChoices):
        OVERCHARGE = "overcharge", _("Asked for more money")
        UNFINISHED = "unfinished", _("Left work unfinished")
        BEHAVIOUR = "behaviour", _("Bad behaviour")
        THEFT = "theft", _("Theft or damage")
        OTHER = "other", _("Something else")

    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="complaints")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(_("contact number"), max_length=10, blank=True)
    reason = models.CharField(max_length=12, choices=Reason.choices)
    details = models.TextField(_("what happened"), max_length=1000, blank=True)
    is_upheld = models.BooleanField(_("upheld after hearing both sides"), default=False)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("complaint")
        verbose_name_plural = _("complaints")
        ordering = ["resolved", "-created_at"]


class WorkRequest(models.Model):
    """'काम बताओ': the customer describes the job and the team finds someone by hand."""

    class When(models.TextChoices):
        NOW = "now", _("Right now, urgent")
        TODAY = "today", _("Any time today")
        TOMORROW = "tomorrow", _("Tomorrow")
        WEEK = "week", _("This week")

    class Status(models.TextChoices):
        NEW = "new", _("New")
        MATCHED = "matched", _("Provider arranged")
        CLOSED = "closed", _("Closed")

    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(_("mobile number"), max_length=10)
    description = models.CharField(_("what work"), max_length=400)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    when = models.CharField(max_length=10, choices=When.choices, default=When.TODAY)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW, db_index=True)
    assigned_provider = models.ForeignKey(Provider, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("work request")
        verbose_name_plural = _("work requests (काम बताओ)")
        ordering = ["-created_at"]

    @property
    def number(self):
        return f"KK-{1000 + self.pk}"
