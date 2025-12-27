from django.db import models
from django.core.exceptions import ValidationError


class Account(models.Model):
    TYPE_CHOICES = [
        ("asset", "Asset"),
        ("liability", "Liability"),
        ("equity", "Equity"),
        ("income", "Income"),
        ("expense", "Expense"),
    ]

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    chart_year = models.PositiveIntegerField(db_index=True)


    is_postable = models.BooleanField(default=True)  # ✅ child/leaf = True, parent/group = False
    is_active = models.BooleanField(default=True)

    

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["chart_year", "code"],
                name="uniq_account_code_per_year",
            )
        ]
        ordering = ["chart_year", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


    def clean(self):
        errors = {}  # ⬅️ INI YANG KURANG TADI

        # 1) parent tidak boleh diri sendiri
        if self.parent_id and self.pk and self.parent_id == self.pk:
            errors["parent"] = "Parent tidak boleh diri sendiri."

        # 2) anti cycle (A -> B -> A)
        if self.parent_id and self.pk:
            seen = {self.pk}
            p = self.parent
            while p:
                if p.pk in seen:
                    errors["parent"] = "Parent-child cycle terdeteksi."
                    break
                seen.add(p.pk)
                p = p.parent

        # 3) child type harus sama dengan parent type
        if self.parent_id and self.parent and self.type != self.parent.type:
            errors["type"] = "Type harus sama dengan parent account."

        # 4) account yang punya child tidak boleh postable
        if self.pk and self.is_postable and self.children.exists():
            errors["is_postable"] = (
                "Account ini punya child, tidak boleh Postable. "
                "Jadikan Group (non-postable)."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # pastikan semua rule di clean() dijalankan
        self.full_clean()
        super().save(*args, **kwargs)

        # 5) enforce parent otomatis non-postable
        if self.parent_id:
            Account.objects.filter(pk=self.parent_id, is_postable=True).update(
                is_postable=False
            )

    