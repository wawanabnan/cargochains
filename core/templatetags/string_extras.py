# core/templatetags/string_extras.py
from django import template

register = template.Library()

@register.filter
def startswith(value, prefix):
    """
    Usage:
      {{ some_string|startswith:"abc" }}
    Returns True/False.
    Aman kalau value None.
    """
    if value is None:
        return False
    return str(value).startswith(str(prefix))


@register.filter
def endswith(value, suffix):
    """
    Bonus: kalau butuh.
    """
    if value is None:
        return False
    return str(value).endswith(str(suffix))
