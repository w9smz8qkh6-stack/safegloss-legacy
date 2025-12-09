from django import template

register = template.Library()

@register.filter
def percent(value, maximum):
    try:
        value = float(value or 0)
        maximum = float(maximum or 1)
        return int((value / maximum) * 100)
    except Exception:
        return 0
