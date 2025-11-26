# sales/templatetags/querystring.py
from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def qs_update(context, request, **kwargs):
    """
    Pemakaian di template:
    {% qs_update request 'sort'='number' 'dir'='asc' %}
    -> menghasilkan URL saat ini dengan querystring yang di-update.
    """
    params = request.GET.copy()
    for k, v in kwargs.items():
        if v in (None, ""):
            params.pop(k, None)
        else:
            params[k] = v
    base = request.path
    qs = params.urlencode()
    return f"{base}?{qs}" if qs else base
