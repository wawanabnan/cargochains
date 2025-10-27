# shipments/templatetags/shipment_extras.py
from django import template

register = template.Library()

@register.filter
def split(value, sep=","):
    """
    Memecah string jadi list berdasarkan separator.
    Contoh: "A,B,C"|split:"," → ["A","B","C"]
    """
    if not value:
        return []
    return [v.strip() for v in value.split(sep)]

@register.filter
def index(sequence, item):
    """
    Mengembalikan index dari item di list (atau -1 jika tidak ada).
    """
    try:
        return list(sequence).index(item)
    except Exception:
        return -1
    
@register.filter
def replace(value, args):
    old, new = args.split(",", 1)
    return (value or "").replace(old, new)    

@register.filter
def humanize_status(value):
    """
    "IN_TRANSIT" -> "In Transit"
    "DRAFT" -> "Draft"
    """
    if not value:
        return ""
    return str(value).replace("_", " ").title()
