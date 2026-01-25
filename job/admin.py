from django.contrib import admin
from job.models.job_orders import JobOrder
from job.models.job_costs import JobCost,JobCostType
from job.models.job_fee import JobFeeLine,JobFeePeriod,JobFeePeriodStatus

@admin.register(JobOrder)
class JobOrderAdmin(admin.ModelAdmin):
    search_fields = ("job_no",)
    list_filter = ("status",)

@admin.register(JobCostType)
class JobCostTypeAdmin(admin.ModelAdmin):
    search_fields = ("code", "name")
    list_filter = ("cost_group", "requires_vendor", "is_active")


@admin.register(JobCost)
class JobCostAdmin(admin.ModelAdmin):
    list_filter = ("is_active",)
    search_fields = ("job_order__job_no", "cost_type__name")

