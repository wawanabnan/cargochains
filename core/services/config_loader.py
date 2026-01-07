import json
from functools import lru_cache
from django.conf import settings

@lru_cache
def load_sales_labels() -> dict:
    path = settings.BASE_DIR / "core" / "config" / "sales_labels.json"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}
