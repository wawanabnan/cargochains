# core/services/core_settings.py
from __future__ import annotations
from typing import Optional
from django.core.cache import cache
from core.models.settings  import CoreSetting

from datetime import timedelta
from django.utils import timezone

import json


CACHE_TTL_SECONDS = 60  # boleh 0 kalau tidak mau cache


# core/services/core_settings.py
def get_setting(category, code, default=None):
    cache_key = f"core_setting:{category.lower()}:{code.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    obj = CoreSetting.objects.filter(category__iexact=category, code__iexact=code).first()
    if not obj:
        cache.set(cache_key, default, CACHE_TTL_SECONDS)
        return default

    # urutan prioritas: text_value -> int_value -> char_value
    if obj.text_value not in (None, ""):
        val = obj.text_value
    elif obj.int_value is not None:
        val = obj.int_value
    elif obj.char_value not in (None, ""):
        val = obj.char_value
    else:
        val = default

    cache.set(cache_key, val, CACHE_TTL_SECONDS)
    return val

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

def calc_valid_until(category="sales", code_days="QUOTATION_VALID_DAY", base_date=None):
    days = int(get_setting(category, code_days, 0) or 0)
    if days <= 0:
        return None
    d = base_date or timezone.localdate()
    return d + timedelta(days=days)

def set_setting(category, code, *, int_value=None, char_value=None, text_value=None, notes=""):
    obj, created = CoreSetting.objects.get_or_create(
        category=category,
        code=code,
        defaults={"notes": notes or ""},
    )

    # update fields
    obj.int_value = int_value
    obj.char_value = char_value
    obj.text_value = text_value
    if created and not obj.notes:
        obj.notes = notes or ""
    obj.save()

    # invalidate cache
    cache_key = f"core_setting:{category.lower()}:{code.lower()}"
    cache.delete(cache_key)

    return obj

def quotation_valid_days(default: int = 14) -> int:
    """
    Global helper: ambil QUOTATION_VALID_DAY dari core_settings.
    fallback default bila tidak ada / invalid.
    """
    v = int(get_setting("sales", "QUOTATION_VALID_DAY", default) or 0)
    return v if v > 0 else default
