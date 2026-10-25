"""Phone + OTP login, shown in a bottom sheet the moment someone taps Call or WhatsApp."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.core.phone import normalize_phone

from .middleware import login_customer, logout_customer
from .models import Customer, OtpCode
from .sms import send_otp

SESSION_PENDING = "otp_phone"


def _safe_next(request, nxt):
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return ""


def login_sheet(request):
    """Step 1: ask for the phone number."""
    return render(request, "accounts/_login_phone.html", {
        "next": _safe_next(request, request.GET.get("next", "")),
        "reason": request.GET.get("reason", ""),
    })


@require_POST
def otp_send(request):
    nxt = _safe_next(request, request.POST.get("next", ""))
    raw = request.POST.get("phone", "")
    try:
        phone = normalize_phone(raw)
    except ValidationError as e:
        return render(request, "accounts/_login_phone.html", {"next": nxt, "error": e.messages[0], "phone": raw})
    if Customer.objects.filter(phone=phone, is_blocked=True).exists():
        return render(request, "accounts/_login_phone.html", {
            "next": nxt, "phone": raw, "error": _("This number cannot use KamKarao. Please contact support."),
        })
    if settings.OTP_PROVIDER == "none":
        # Early-stage mode: number is recorded but not verified (no SMS/WhatsApp cost, no DLT).
        customer, _created = Customer.objects.get_or_create(phone=phone)
        login_customer(request, customer)
        resp = HttpResponse("")
        if nxt:
            resp["HX-Redirect"] = nxt
        else:
            resp["HX-Refresh"] = "true"
        return resp
    dev_code = None
    if not OtpCode.recently_sent(phone):
        code = OtpCode.issue(phone)
        if not send_otp(phone, code):
            return render(request, "accounts/_login_phone.html", {
                "next": nxt, "phone": raw, "error": _("Could not send the OTP. Please try again in a minute."),
            })
        if settings.OTP_PROVIDER == "console" and settings.DEBUG:
            dev_code = code
    request.session[SESSION_PENDING] = phone
    return render(request, "accounts/_login_otp.html", {"phone": phone, "next": nxt, "dev_code": dev_code})


@require_POST
def otp_verify(request):
    phone = request.session.get(SESSION_PENDING)
    nxt = _safe_next(request, request.POST.get("next", ""))
    if not phone:
        return login_sheet(request)
    code = request.POST.get("otp", "")
    if not OtpCode.verify(phone, code):
        return render(request, "accounts/_login_otp.html", {
            "phone": phone, "next": nxt, "error": _("That OTP is not right or has expired."),
        })
    customer, _created = Customer.objects.get_or_create(phone=phone)
    login_customer(request, customer)
    request.session.pop(SESSION_PENDING, None)
    resp = HttpResponse("")
    # Reload the page (or go to `next`) so every masked number becomes visible.
    if nxt:
        resp["HX-Redirect"] = nxt
    else:
        resp["HX-Refresh"] = "true"
    return resp


@require_POST
def logout_view(request):
    logout_customer(request)
    return redirect("home")


def account(request):
    if not request.customer:
        return redirect(f"{reverse('home')}?login=1")
    leads = request.customer.leads.select_related("provider", "provider__category").prefetch_related("rating")[:50]
    return render(request, "accounts/account.html", {"leads": leads})
