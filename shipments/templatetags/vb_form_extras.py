from django import template

register = template.Library()

@register.filter
def get_item(obj, key):
    """
    Allow dynamic access in template:
      form|get_item:"reference_no"
    """
    try:
        return obj[key]
    except Exception:
        return None
