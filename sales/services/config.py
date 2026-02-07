# sales/services/config.py
from typing import Dict, Any
from sales.models import SalesConfig


def get_sales_config() -> SalesConfig | None:
    """
    Single-row sales configuration.
    """
    return SalesConfig.objects.first()


def get_sales_defaults(*, target: str = "job_order") -> Dict[str, Any]:
    """
    Return defaults from SalesConfig for forms/documents.
    target: 'job_order' | 'quotation'
    """
    cfg = get_sales_config()
    if not cfg:
        return {}

    data: Dict[str, Any] = {
        "customer_note": (cfg.customer_note or "").strip(),
        "term_conditions": (cfg.term_conditions or "").strip(),
        "sales_fee_percent": str(cfg.sales_fee_percent or "0.00"),
        "quotation_valid_days": int(cfg.quotation_valid_days or 0),
        "default_currency": cfg.default_currency_id,
    }

    # signature config (kalau field ada di form)
    if target == "quotation":
        data["signature_source"] = getattr(cfg, "quotation_signature_source", None)
        data["signature_user"] = getattr(cfg, "quotation_signature_user_id", None)
    else:
        data["signature_source"] = getattr(cfg, "joborder_signature_source", None)
        data["signature_user"] = getattr(cfg, "joborder_signature_user_id", None)

    return data
