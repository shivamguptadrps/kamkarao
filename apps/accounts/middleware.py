from django.utils import timezone

from .models import Customer

SESSION_KEY = "customer_id"


class CustomerMiddleware:
    """Attach `request.customer` when the visitor has verified their phone."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.customer = None
        cid = request.session.get(SESSION_KEY)
        if cid:
            customer = Customer.objects.filter(pk=cid, is_blocked=False).first()
            if customer:
                request.customer = customer
                today = timezone.now().date()
                if not customer.last_seen_at or customer.last_seen_at.date() != today:
                    customer.last_seen_at = timezone.now()
                    customer.save(update_fields=["last_seen_at"])
            else:
                request.session.pop(SESSION_KEY, None)
        return self.get_response(request)


def login_customer(request, customer):
    request.session.cycle_key()
    request.session[SESSION_KEY] = customer.pk
    request.customer = customer


def logout_customer(request):
    area = request.session.get("area_id")
    request.session.flush()
    if area:
        request.session["area_id"] = area
    request.customer = None
