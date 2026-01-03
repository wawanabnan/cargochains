
from django.core.management.base import BaseCommand
from django.utils import timezone
from projects.models import Project
from core.utils.numbering import get_next_number


class Command(BaseCommand):
    help = "Isi field 'number' untuk Project yang masih NULL."

    def handle(self, *args, **opts):
        today = timezone.localdate()
        qs = Project.objects.filter(number__isnull=True)
        n = 0
        for p in qs:
            p.number = get_next_number("projects", "PROJECT", today=today)
            p.save(update_fields=["number"])
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Filled {n} project numbers"))
