# core/services/core_settings.py
from core.models.settings  import CoreSetting

def get_setting(category, code, default=None):

    obj = CoreSetting.objects.filter(category=category, code=code).first()

    if not obj:
        return default

    # ✅ untuk TinyMCE (HTML panjang)
    if obj.text_value not in (None, ""):
        return obj.text_value

    if obj.int_value is not None:
        return obj.int_value
    if obj.char_value not in (None, ""):
        return obj.char_value
    return default


import json

def get_setting_json(category, code, default=None):
    """
    Ambil setting yang isinya JSON (di char_value / text_value).
    Return dict/list sesuai JSON. Kalau invalid -> default.
    """
    raw = get_setting(category, code, None)
    if raw in (None, ""):
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default



def apply_sales_defaults(initial: dict):
    initial.setdefault("currency_code", get_setting("sales", "default_currency_code", "IDR"))
    initial.setdefault("valid_days", get_setting("sales", "quote_valid_day", 30))
    initial.setdefault("sales_fee_percent", get_setting("sales", "sales_fee_percent", "0.00"))
    initial.setdefault("tax_id", get_setting("sales", "default_sales_tax"))
    initial.setdefault("customer_note", get_setting("sales", "customer_notes", ""))
    initial.setdefault("sla_text", get_setting("sales", "sla", ""))
    return initial


def set_setting(category, code, *, int_value=None, char_value=None, text_value=None):
    obj, _ = CoreSetting.objects.get_or_create(category=category, code=code)
    if int_value is not None or int_value is None:
        obj.int_value = int_value
    if char_value is not None or char_value is None:
        obj.char_value = char_value
    if text_value is not None or text_value is None:
        obj.text_value = text_value
    obj.save()
    return obj


from datetime import timedelta
from django.utils import timezone

def calc_valid_until(category="sales", code_days="quote_valid_day", base_date=None):
    """
    Return date atau None.
    - days <= 0 -> None
    - base_date None -> today
    """
    from core.services.core_settings import get_setting  # kalau file sama, hapus import ini
    days = int(get_setting(category, code_days, 0) or 0)
    if days <= 0:
        return None
    d = base_date or timezone.localdate()
    return d + timedelta(days=days)
