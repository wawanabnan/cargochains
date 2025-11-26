from django import template
register = template.Library()

@register.filter
def split(value, sep=","):
    if value is None:
        return []
    return [x.strip() for x in str(value).split(sep)]
