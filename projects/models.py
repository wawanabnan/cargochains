
from django.db import models
from django.utils import timezone
from core.utils import get_next_number


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ProjectStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    IN_PROGRESS = "in_progress", "In Progress"
    ON_HOLD = "on_hold", "On Hold"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class ProjectCategory(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "projects_categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(TimeStampedModel):
    number = models.CharField(max_length=50, unique=True, null=True, blank=True, editable=False)
    ref_number = models.CharField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(ProjectCategory, on_delete=models.PROTECT, related_name="projects")
    status = models.CharField(max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.PLANNED)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "projects"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["start_date"]),
            models.Index(fields=["number"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.number or '—'} {self.name}"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = get_next_number(app_label="projects", code="PROJECT", today=timezone.localdate())
        super().save(*args, **kwargs)


class CostCategory(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "projects_cost_categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProjectCost(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="costs")
    category = models.ForeignKey(CostCategory, on_delete=models.PROTECT, related_name="costs")
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency_code = models.CharField(max_length=3, default="IDR")
    cost_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    ref = models.CharField(max_length=100, null=True, blank=True)
    attachment = models.FileField(upload_to="projects/costs/%Y/%m/", null=True, blank=True)


    class Meta:
        db_table = "projects_costs"
        indexes = [
            models.Index(fields=["project", "category"]),
            models.Index(fields=["cost_date"]),
        ]
        ordering = ["-cost_date", "-created_at"]

    def __str__(self):
        return f"{self.title} ({self.amount} {self.currency_code})"
