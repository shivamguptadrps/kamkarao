from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

AVATAR_GRADIENTS = [
    ("#14B8A6", "#115E59"), ("#F59E0B", "#C2410C"), ("#6366F1", "#3730A3"),
    ("#EC4899", "#9D174D"), ("#84CC16", "#3F6212"), ("#0EA5E9", "#075985"),
]

CATEGORY_ICONS = {
    "electrician": "bolt", "plumber": "droplet", "appliance": "snow", "bike": "bike",
    "carpenter": "hammer", "beauty": "sparkle", "painter": "roller",
}
CATEGORY_COLORS = {
    "electrician": "#B45309", "plumber": "#0369A1", "appliance": "#0E7490", "bike": "#4D7C0F",
    "carpenter": "#92400E", "beauty": "#BE185D", "painter": "#7C3AED",
}


@register.simple_tag
def icon(name, cls=""):
    return format_html('<svg class="icon {}" aria-hidden="true"><use href="#i-{}"></use></svg>', cls, name)


@register.filter
def cat_icon(category):
    return CATEGORY_ICONS.get(getattr(category, "icon", ""), "wrench")


@register.filter
def cat_color(category):
    return CATEGORY_COLORS.get(getattr(category, "icon", ""), "#0F766E")


@register.filter
def avatar_style(obj):
    a1, a2 = AVATAR_GRADIENTS[(getattr(obj, "pk", 0) or 0) % len(AVATAR_GRADIENTS)]
    return mark_safe(f"--a1:{a1};--a2:{a2}")


@register.filter
def km(value):
    if value is None:
        return ""
    if value < 0.3:
        return "<0.3"
    return f"{value:.1f}"


@register.filter
def stars(n):
    n = int(n or 0)
    return "★" * n + "☆" * (5 - n)


@register.simple_tag(takes_context=True)
def qs_toggle(context, key, value="1"):
    """Current querystring with one filter switched on/off (used by filter chips)."""
    q = context["request"].GET.copy()
    q.pop("partial", None)
    if q.get(key) == str(value):
        q.pop(key)
    else:
        q[key] = value
    s = q.urlencode()
    return f"?{s}" if s else "?"


@register.simple_tag(takes_context=True)
def qs_set(context, key, value=""):
    q = context["request"].GET.copy()
    q.pop("partial", None)
    if value in ("", None):
        q.pop(key, None)
    else:
        q[key] = value
    s = q.urlencode()
    return f"?{s}" if s else "?"
