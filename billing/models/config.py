from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings


class BillingConfig(models.Model):

    # =========================
    # INVOICE TITLES
    # =========================
    invoice_title_default = models.CharField(max_length=100, default="INVOICE")
    dp_invoice_title = models.CharField(max_length=100, default="DOWN PAYMENT INVOICE")
    final_invoice_title = models.CharField(max_length=100, default="FINAL INVOICE")

    # =========================
    # DEFAULT TEXT
    # =========================
        
    default_customer_note = models.TextField(blank=True)
    default_terms_conditions = models.TextField(blank=True)
    default_footer_note = models.TextField(blank=True)


    # =========================
    # BANK INFO
    # =========================
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_name = models.CharField(max_length=150, blank=True)
    bank_account_number = models.CharField(max_length=100, blank=True)
    swift_code = models.CharField(max_length=50, blank=True)
    bank_address = models.TextField(blank=True)

    # =========================
    # SIGNATURE
    # =========================
    SIGNATURE_MANUAL = "MANUAL"
    SIGNATURE_USER = "USER"

    SIGNATURE_MODE_CHOICES = [
        (SIGNATURE_MANUAL, "Manual Upload"),
        (SIGNATURE_USER, "From System User"),
    ]

    signature_mode = models.CharField(
        max_length=10,
        choices=SIGNATURE_MODE_CHOICES,
        default=SIGNATURE_MANUAL,
    )

    # ===== Manual Mode =====
    signature_name = models.CharField(max_length=150, blank=True)
    signature_title = models.CharField(max_length=150, blank=True)
    signature_image = models.ImageField(
        upload_to="billing/signatures/",
        blank=True,
        null=True,
    )

    # ===== User Mode =====
    signature_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Select user to use their profile signature."
    )

   

    class Meta:
        db_table = "billing_config"
        verbose_name = "Billing Configuration"

    def clean(self):
        if not self.pk and BillingConfig.objects.exists():
            raise ValidationError("Only one Billing Configuration is allowed.")

    def __str__(self):
        return "Billing Configuration"

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
    

    @property
    def active_signature_name(self):
        if self.signature_mode == self.SIGNATURE_USER and self.signature_user:
            profile = getattr(self.signature_user, "profile", None)
            if profile:
                return self.signature_user.get_full_name() or self.signature_user.username
        return self.signature_name


    @property
    def active_signature_title(self):
        if self.signature_mode == self.SIGNATURE_USER and self.signature_user:
            profile = getattr(self.signature_user, "profile", None)
            if profile:
                return profile.title
        return self.signature_title


    @property
    def active_signature_image(self):
        if self.signature_mode == self.SIGNATURE_USER and self.signature_user:
            profile = getattr(self.signature_user, "profile", None)
            if profile and profile.signature:
                return profile.signature
        return self.signature_image
    

