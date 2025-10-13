# sales/querysets.py
from django.db.models import QuerySet

def sales_queryset_for_user(qs: QuerySet, user):
    """
    Filter queryset SalesQuotation sesuai hak akses user.
    Kamu bisa sesuaikan logika akses di sini.
    Untuk sekarang, default-nya: kalau bukan superuser → hanya data miliknya.
    """
    if user.is_superuser:
        return qs
    return qs.filter(sales_user=user)
