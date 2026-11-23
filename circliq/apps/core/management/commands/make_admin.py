from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.institutions.models import Institution


class Command(BaseCommand):
    help = "Turn an existing account into a campus administrator (role=admin) for an institution."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--institution", help="Institution slug (default: the first active institution)")

    def handle(self, *args, **opts):
        try:
            user = User.objects.get(email__iexact=opts["email"])
        except User.DoesNotExist:
            raise CommandError(f"No account with email {opts['email']}. Register it first (or run createsuperuser).")
        qs = Institution.objects.filter(is_active=True)
        inst = qs.filter(slug=opts["institution"]).first() if opts["institution"] else qs.first()
        if inst is None:
            raise CommandError("No matching active institution.")
        user.role, user.institution, user.is_approved, user.is_email_verified, user.is_active = User.Role.ADMIN, inst, True, True, True
        user.save()
        self.stdout.write(self.style.SUCCESS(f"{user.email} is now a campus administrator for {inst.name}. Open /app/admin/ after logging in."))
