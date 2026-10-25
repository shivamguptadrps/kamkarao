import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def normalize_phone(value: str) -> str:
    """Return a 10-digit Indian mobile number or raise ValidationError."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise ValidationError(_("Enter a valid 10-digit mobile number."))
    return digits


def pretty_phone(digits: str) -> str:
    return f"+91 {digits[:5]} {digits[5:]}"


def masked_phone(digits: str) -> str:
    return f"+91 {digits[:2]}XXX XXX{digits[-2:]}"
