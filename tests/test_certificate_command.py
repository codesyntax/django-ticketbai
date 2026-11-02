from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from django_ticketbai.utils.certificate import CertificateInfo


def expired_info(*args, **kwargs):
    return CertificateInfo(
        status="expired",
        not_after=datetime(2025, 4, 28, tzinfo=timezone.utc),
        days_left=-553,
    )


def expiring_info(*args, **kwargs):
    return CertificateInfo(
        status="expiring",
        not_after=datetime(2026, 11, 20, tzinfo=timezone.utc),
        days_left=18,
    )


def config_with(info):
    return SimpleNamespace(pk=1, certificate_info=info)


@override_settings(
    TICKETBAI_CERTIFICATE_ALERT_EMAILS=["ops@example.com"],
    DEFAULT_FROM_EMAIL="ticketbai@example.com",
)
def test_command_fails_and_emails_for_an_expired_certificate():
    config = config_with(expired_info)

    with (
        patch(
            "django_ticketbai.management.commands.check_ticketbai_certificate.Config.objects.filter",
            return_value=[config],
        ),
        patch(
            "django_ticketbai.management.commands.check_ticketbai_certificate.send_mail"
        ) as send_mail,
    ):
        with pytest.raises(CommandError):
            call_command("check_ticketbai_certificate", "--fail-on", "expired")

    send_mail.assert_called_once()
    assert send_mail.call_args.args[3] == ["ops@example.com"]
    assert "expired on 2025-04-28" in send_mail.call_args.args[1]


@override_settings(
    TICKETBAI_CERTIFICATE_ALERT_EMAILS=["ops@example.com"],
    DEFAULT_FROM_EMAIL="ticketbai@example.com",
)
def test_command_does_not_fail_for_an_expiring_certificate_with_fail_on_expired():
    config = config_with(expiring_info)

    with (
        patch(
            "django_ticketbai.management.commands.check_ticketbai_certificate.Config.objects.filter",
            return_value=[config],
        ),
        patch(
            "django_ticketbai.management.commands.check_ticketbai_certificate.send_mail"
        ) as send_mail,
    ):
        call_command("check_ticketbai_certificate", "--fail-on", "expired")

    send_mail.assert_called_once()
    assert "expires in 18 days" in send_mail.call_args.args[1]


def test_command_without_an_active_config_does_nothing():
    with patch(
        "django_ticketbai.management.commands.check_ticketbai_certificate.Config.objects.filter",
        return_value=[],
    ):
        call_command("check_ticketbai_certificate")


@override_settings(
    ADMINS=[("Operations", "ops@example.com")],
    DEFAULT_FROM_EMAIL="ticketbai@example.com",
)
def test_command_uses_admins_when_no_alert_recipients_are_configured():
    config = config_with(expired_info)

    with (
        patch(
            "django_ticketbai.management.commands.check_ticketbai_certificate.Config.objects.filter",
            return_value=[config],
        ),
        patch(
            "django_ticketbai.management.commands.check_ticketbai_certificate.send_mail"
        ) as send_mail,
    ):
        call_command("check_ticketbai_certificate")

    send_mail.assert_called_once()
    assert send_mail.call_args.args[3] == ["ops@example.com"]


@override_settings(
    ADMINS=[("Operations", "ops@example.com")],
    TICKETBAI_CERTIFICATE_ALERT_EMAILS=[],
    DEFAULT_FROM_EMAIL="ticketbai@example.com",
)
def test_command_allows_disabling_email_alerts_with_an_empty_list():
    config = config_with(expired_info)

    with (
        patch(
            "django_ticketbai.management.commands.check_ticketbai_certificate.Config.objects.filter",
            return_value=[config],
        ),
        patch(
            "django_ticketbai.management.commands.check_ticketbai_certificate.send_mail"
        ) as send_mail,
    ):
        call_command("check_ticketbai_certificate")

    send_mail.assert_not_called()
