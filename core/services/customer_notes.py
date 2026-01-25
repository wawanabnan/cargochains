from core.models.settings import CoreSetting

def get_customer_notes():
    qs = CoreSetting.objects.filter(
        category=CoreSetting.CAT_SALES,
        code__in=["CUSTOMER_NOTES", "SLA"],
    ).only("code", "text_value")

    m = {s.code: (s.text_value or "").strip() for s in qs}

    return {
        "customer_note": m.get("CUSTOMER_NOTES", ""),
        "sla_note": m.get("SLA", ""),
    }