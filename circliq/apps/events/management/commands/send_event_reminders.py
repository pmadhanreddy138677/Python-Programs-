from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.events.models import Event, EventRegistration, EventSave
from apps.notifications.services import notify


class Command(BaseCommand):
    help = "Send reminders for events starting within the next 24 hours (run hourly, e.g. via Windows Task Scheduler or cron)."

    def handle(self, *args, **opts):
        now = timezone.now()
        soon = Event.objects.filter(start_at__gt=now, start_at__lte=now + timedelta(hours=24))
        sent = 0
        for model in (EventRegistration, EventSave):
            for row in model.objects.filter(event__in=soon, reminded=False).select_related("event", "user"):
                e = row.event
                when = timezone.localtime(e.start_at).strftime("%a %d %b, %I:%M %p")
                notify(row.user, "event", f"Reminder: {e.title}", f"Starts {when} at {e.venue}", f"/app/events/{e.pk}/")
                row.reminded = True
                row.save(update_fields=["reminded"])
                sent += 1
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} reminder(s)."))
