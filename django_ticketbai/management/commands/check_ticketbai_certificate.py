from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

from django_ticketbai.models import Config
from django_ticketbai.utils.certificate import DEFAULT_WARNING_DAYS

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check the expiry date of the active TicketBAI client certificate."

    def add_arguments(self, parser):
        parser.add_argument(
            "--warn-days",
            type=int,
            default=None,
            help="Warn when the certificate expires in this many days.",
        )
        parser.add_argument(
            "--fail-on",
            choices=("expired", "expiring"),
            default=None,
            help="Exit with an error for an expired or expiring certificate.",
        )
        parser.add_argument(
            "--email",
            action="append",
            default=None,
            help="Email address to notify. May be repeated.",
        )

    def handle(self, *args, **options):
        warn_days = options["warn_days"]
        if warn_days is None:
            warn_days = getattr(
                settings,
                "TICKETBAI_CERTIFICATE_WARNING_DAYS",
                DEFAULT_WARNING_DAYS,
            )

        recipients = options["email"]
        if recipients is None:
            configured = getattr(settings, "TICKETBAI_CERTIFICATE_ALERT_EMAILS", None)
            if configured is None:
                recipients = []
                for entry in getattr(settings, "ADMINS", []):
                    if isinstance(entry, str):
                        email = entry
                    elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                        email = entry[1]
                    else:
                        continue
                    if email:
                        recipients.append(email)
            else:
                recipients = configured
        if isinstance(recipients, str):
            recipients = [recipients]

        alerts = []
        for config in Config.objects.filter(is_active=True):
            info = config.certificate_info(warn_days=warn_days)
            if info.status not in ("expired", "expiring"):
                continue

            if info.status == "expired":
                message = "TicketBAI certificate for config %s expired on %s" % (
                    config.pk,
                    info.not_after.date(),
                )
                self.stdout.write(self.style.ERROR(message))
                logger.error(message)
            else:
                message = (
                    "TicketBAI certificate for config %s expires in %s days (%s)"
                    % (config.pk, info.days_left, info.not_after.date())
                )
                self.stdout.write(self.style.WARNING(message))
                logger.warning(message)
            alerts.append((config, info, message))

        if alerts and recipients:
            subject = "[TicketBAI] Client certificate needs attention"
            body = "\n".join(message for _, _, message in alerts)
            try:
                send_mail(
                    subject,
                    body,
                    getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"),
                    recipients,
                    fail_silently=False,
                )
            except Exception:
                logger.exception("Could not send TicketBAI certificate alert")

        fail_on = options["fail_on"]
        if fail_on == "expired" and any(
            info.status == "expired" for _, info, _ in alerts
        ):
            raise CommandError("Expired TicketBAI client certificate")
        if fail_on == "expiring" and alerts:
            raise CommandError("TicketBAI client certificate expires soon")
