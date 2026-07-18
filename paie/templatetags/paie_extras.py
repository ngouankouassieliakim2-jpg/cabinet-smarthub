from django import template

register = template.Library()


@register.filter
def espace(value):
    """Formate un nombre avec des espaces comme séparateurs de milliers : 1234567 -> 1 234 567."""
    try:
        n = round(float(value))
    except (TypeError, ValueError):
        return value
    return f"{n:,}".replace(",", " ")
@register.filter
def dict_get(d, cle):
    """Récupère d[cle] dans un template."""
    try:
        return d.get(cle, 0)
    except Exception:
        return 0