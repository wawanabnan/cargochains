# job/services/order_workflow.py
from django.db import transaction

class OrderWorkflowService:
    @staticmethod
    @transaction.atomic
    def on_ordered(job_order, user):
        # 1) lock job/order lines
        job_order.locked = True
        job_order.save(update_fields=["locked"])

        # 2) inventory reserve (opsional)
        # InventoryService.reserve(job_order)

        # 3) create invoice draft (opsional)
        # InvoiceService.create_draft_from_job(job_order, user)

        # 4) audit log
        AuditLog.objects.create(
            action="JOB_ORDERED",
            ref_type="JobOrder",
            ref_id=job_order.id,
            message=f"JobOrder {job_order.number} ordered from quotation {job_order.quotation.number}",
            created_by=user
        )
