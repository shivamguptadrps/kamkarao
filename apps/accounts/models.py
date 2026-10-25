import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Customer(models.Model):
    """A visitor who verified their phone by OTP. No password, no Django user account."""

    phone = models.CharField(_("mobile number"), max_length=10, unique=True)
    name = models.CharField(_("name"), max_length=80, blank=True)
    is_blocked = models.BooleanField(_("blocked"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("customer")
        verbose_name_plural = _("customers")
        ordering = ["-created_at"]

    def __str__(self):
        return self.phone


class OtpCode(models.Model):
    phone = models.CharField(max_length=10, db_index=True)
    code_hash = models.CharField(max_length=64)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def _hash(phone, code):
        return hashlib.sha256(f"{settings.SECRET_KEY}:{phone}:{code}".encode()).hexdigest()

    @classmethod
    def issue(cls, phone):
        code = "".join(secrets.choice("0123456789") for _ in range(settings.OTP_LENGTH))
        cls.objects.filter(phone=phone, used=False).update(used=True)
        cls.objects.create(phone=phone, code_hash=cls._hash(phone, code))
        return code

    @classmethod
    def recently_sent(cls, phone):
        last = cls.objects.filter(phone=phone).first()
        if not last:
            return False
        return (timezone.now() - last.created_at).total_seconds() < settings.OTP_RESEND_SECONDS

    @classmethod
    def verify(cls, phone, code):
        """Return True if the code is right. Burns the code after success or too many tries."""
        otp = cls.objects.filter(phone=phone, used=False).first()
        if not otp:
            return False
        if (timezone.now() - otp.created_at).total_seconds() > settings.OTP_TTL_SECONDS:
            otp.used = True
            otp.save(update_fields=["used"])
            return False
        otp.attempts += 1
        ok = secrets.compare_digest(otp.code_hash, cls._hash(phone, code.strip()))
        if ok or otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            otp.used = True
        otp.save(update_fields=["attempts", "used"])
        return ok
