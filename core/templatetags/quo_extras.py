# sales/templatetags/quo_extras.py
from django import template
register = template.Library()

@register.filter
def can_transition_to(obj, new_status):
    try:
        return obj.can_transition_to(new_status)
    except Exception:
        return False
