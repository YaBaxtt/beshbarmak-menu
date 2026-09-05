from django import template


register = template.Library()


@register.filter
def price(value):
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return value
