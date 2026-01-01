from typing import Final
from sales.models import Invoice


class InvoicePolicy:
    """
    Policy layer for Invoice:
    - workflow rules (status-based)
    - permission rules (Django admin permissions)
    Stateless, pure logic.
    """

    # =========================
    #   WORKFLOW RULES
    # =========================
    EDITABLE_STATUSES: Final[set[str]] = {Invoice.ST_DRAFT}
    CONFIRMABLE_STATUSES: Final[set[str]] = {Invoice.ST_DRAFT}
    PAYABLE_STATUSES: Final[set[str]] = {Invoice.ST_SENT}

    # =========================
    #   PERMISSIONS (Admin)
    # =========================
    PERM_EDIT: Final[str] = "sales.change_invoice"
    PERM_CONFIRM: Final[str] = "sales.confirm_invoice"
    PERM_PAY: Final[str] = "sales.receive_payment"

    # =========================
    #   INTERNAL HELPERS
    # =========================
    @staticmethod
    def _has_perm(user, perm: str) -> bool:
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.has_perm(perm))
        )

    # =========================
    #   PUBLIC CHECKS
    # =========================
    @classmethod
    def can_edit(cls, inv: Invoice, user) -> bool:
        return (
            inv.status in cls.EDITABLE_STATUSES
            and cls._has_perm(user, cls.PERM_EDIT)
        )

    @classmethod
    def can_confirm(cls, inv: Invoice, user) -> bool:
        return (
            inv.status in cls.CONFIRMABLE_STATUSES
            and not inv.journal_id
            and cls._has_perm(user, cls.PERM_CONFIRM)
        )

    @classmethod
    def can_receive_payment(cls, inv: Invoice, user) -> bool:
        return (
            inv.status in cls.PAYABLE_STATUSES
            and cls._has_perm(user, cls.PERM_PAY)
        )
