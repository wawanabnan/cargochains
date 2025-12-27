from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from accounting.models.chart import Account
from accounting.models.settings import AccountingSettings


@require_GET
@login_required
def account_autocomplete(request):
    q = (request.GET.get("q") or "").strip()
    active_year = AccountingSettings.get_active_year()

    qs = (
        Account.objects
        .filter(chart_year=active_year, is_active=True, is_postable=True)
        .order_by("code")
    )

    if q:
        qs = qs.filter(code__icontains=q) | qs.filter(name__icontains=q)

    data = [
        {"id": a.id, "label": f"{a.code} - {a.name}", "value": f"{a.code} - {a.name}"}
        for a in qs[:30]
    ]
    return JsonResponse(data, safe=False)
