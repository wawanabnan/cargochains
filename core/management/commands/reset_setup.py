from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model

from core.models.setup import SetupState
from core.models.company import CompanyProfile


class Command(BaseCommand):
    help = "Reset initial setup state for testing (DEV only)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Allow run even if DEBUG=False")
        parser.add_argument("--delete-users", action="store_true", help="Delete all users (dangerous)")
        parser.add_argument("--delete-company", action="store_true", help="Delete CompanyProfile data")

    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts["force"]:
            raise CommandError("Refusing to run reset_setup because DEBUG=False. Use --force if you really want.")

        if opts["delete_company"]:
            CompanyProfile.objects.all().delete()
            self.stdout.write(self.style.WARNING("Deleted CompanyProfile rows."))

        SetupState.objects.all().delete()
        self.stdout.write(self.style.WARNING("Deleted SetupState rows (wizard will appear again)."))

        if opts["delete_users"]:
            User = get_user_model()
            User.objects.all().delete()
            self.stdout.write(self.style.WARNING("Deleted ALL users."))

        self.stdout.write(self.style.SUCCESS("Reset complete. Next migrate/post_migrate will recreate initial admin if no users exist."))
