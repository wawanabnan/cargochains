from django import template

register = template.Library()

@register.filter
def add_error_class(field):
    css = field.field.widget.attrs.get("class", "")
    if field.errors:
        if "is-invalid" not in css:
            field.field.widget.attrs["class"] = css + " is-invalid"
    return field
