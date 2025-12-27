from django.db import models
from django.utils import timezone
from accounting.models.chart import Account
from django.core.exceptions import ValidationError


class AccountingSettings(models.Model):
    class PostingPolicy(models.TextChoices):
        OPEN_IF_MISSING = "open_if_missing", "Allow posting if no period lock exists (missing = OPEN)"
        STRICT_REQUIRE  = "strict_require",  "Allow posting only when period explicitly OPEN (missing = BLOCK)"

    active_fiscal_year = models.PositiveIntegerField(default=timezone.now().year)
    posting_policy = models.CharField(
        max_length=32,
        choices=PostingPolicy.choices,
        default=PostingPolicy.OPEN_IF_MISSING,
    )

    default_ar_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Default Accounts Receivable for Sales Invoice",
    )
    default_sales_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Default Sales Revenue for Sales Invoice",
    )
    default_tax_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Default Output Tax Payable for Sales Invoice",
    )

    default_cash_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Default Cash/Bank account for receipts/payments",
    )

    default_pph_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Account for PPH withholding on customer receipts (PPH ikut payment)",
    )

    def clean(self):
        fields = (
            "default_ar_account",
            "default_sales_account",
            "default_tax_account",
            "default_cash_account",
            "default_pph_account",
        )

        errors = {}
        for f in fields:
            acc = getattr(self, f, None)
            if acc:
                if not acc.is_active:
                    errors[f] = "Account harus aktif."
                if not acc.is_postable:
                    errors[f] = "Account harus postable (bukan group/header)."

        if errors:
            raise ValidationError(errors)



    def save(self, *args, **kwargs):
        self.pk = 1  # singleton: hanya 1 row
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def get_active_year(cls) -> int:
        return cls.get_solo().active_fiscal_year

    @classmethod
    def get_posting_policy(cls) -> str:
        return cls.get_solo().posting_policy

    def __str__(self):
        return f"Accounting Settings (FY: {self.active_fiscal_year})"
