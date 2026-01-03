from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from .chart import Account
from accounting.services.numbering import next_journal_number  # ✅ konsisten
from accounting.services.periods import is_period_locked


class Journal(models.Model):

  
    KIND_CHOICES = [
        ("OPEN", "Opening Balance"),
        ("GJ", "General Journal"),
    ]

    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default="GJ")  # ✅ tambah ini

    number = models.CharField(max_length=30, unique=True)
    date = models.DateField(default=timezone.localdate)
    ref = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    posted = models.BooleanField(default=False)
    source_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        help_text="JOB, INV, PAY, etc"
    )
    source_ref = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        help_text="Reference number of source document"
    )
    currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )


    number = models.CharField(max_length=30, unique=True)  # JV-YYYYMM-0001 dll
    date = models.DateField(default=timezone.localdate)
    ref = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    posted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["source_type", "source_ref"]),
        ]

    def __str__(self):
        return self.number

    @property
    def total_debit(self):
        return self.lines.aggregate(s=models.Sum("debit"))["s"] or Decimal("0.00")

    @property
    def total_credit(self):
        return self.lines.aggregate(s=models.Sum("credit"))["s"] or Decimal("0.00")

    def clean(self):
        # kalau sudah posted -> tidak boleh invalid
        if self.posted and self.total_debit != self.total_credit:
            raise ValidationError("Posted journal must be balanced (debit == credit).")
        


    def save(self, *args, **kwargs):
        if self.pk:
            old = Journal.objects.get(pk=self.pk)
            if old.posted:
                raise ValidationError("Posted journal is locked and cannot be modified.")

        if self.posted and is_period_locked(self.date):
            raise ValidationError(f"Period {self.date:%Y-%m} is locked. Cannot post journal in locked period.")

        
        if not self.number:
            self.number = next_journal_number(self.date, kind=self.kind)
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.posted:
            raise ValidationError("Posted journal is locked and cannot be deleted.")
        return super().delete(*args, **kwargs)


class JournalLine(models.Model):
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    label = models.CharField(max_length=200, blank=True)
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def clean(self):
        if self.debit and self.credit:
            raise ValidationError("Journal line cannot have both debit and credit.")
        if (self.debit or 0) < 0 or (self.credit or 0) < 0:
            raise ValidationError("Debit/Credit cannot be negative.")


    def save(self, *args, **kwargs):
        if self.pk:
            old = self.__class__.objects.select_related("journal").get(pk=self.pk)
            if old.journal.posted:
                raise ValidationError("Posted journal is locked. Lines cannot be modified.")
        else:
            if self.journal and self.journal.posted:
                raise ValidationError("Posted journal is locked. Lines cannot be added.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.journal and self.journal.posted:
            raise ValidationError("Posted journal is locked. Lines cannot be deleted.")
        return super().delete(*args, **kwargs)
