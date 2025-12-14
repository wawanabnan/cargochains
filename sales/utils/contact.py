from typing import Optional
from partners.models import Partner

def get_sales_contact(customer: Partner) -> Optional[Partner]:
    """
    Ambil 1 contact person untuk Sales (Quotation/SO).
    - prioritas: contact yang is_sales_contact=True
    - fallback: contact pertama (kalau ada)
    """
    if not customer:
        return None

    qs = customer.contacts.all()  # related_name="contacts" dari field company=self
    c = qs.filter(is_sales_contact=True).order_by("id").first()
    return c or qs.order_by("id").first()


def get_billing_contact(customer: Partner) -> Optional[Partner]:
    """
    Ambil 1 contact person untuk Billing (Invoice).
    - prioritas: is_billing_contact=True
    - fallback: is_sales_contact=True
    - fallback: contact pertama
    """
    if not customer:
        return None

    qs = customer.contacts.all()
    c = qs.filter(is_billing_contact=True).order_by("id").first()
    if c:
        return c

    c = qs.filter(is_sales_contact=True).order_by("id").first()
    return c or qs.order_by("id").first()
