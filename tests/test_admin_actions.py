from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib import admin, messages

from django_ticketbai.admin import InvoiceAdmin
from django_ticketbai.models import Invoice
from django_ticketbai.utils.certificate import CertificateInfo


class FakeQuerySet:
    def __init__(self, items):
        self.items = items

    def filter(self, *args, **kwargs):
        return self

    def exclude(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def __iter__(self):
        return iter(self.items)


def make_admin():
    model_admin = InvoiceAdmin(Invoice, admin.site)
    model_admin.message_user = Mock()
    model_admin.log_change = Mock()
    return model_admin


def config_with(status="valid"):
    return SimpleNamespace(
        pk=1,
        certificate_info=Mock(
            return_value=CertificateInfo(
                status=status,
                not_after=None,
                days_left=100 if status == "valid" else 10,
            )
        ),
    )


def invoice(**kwargs):
    defaults = {
        "pk": 1,
        "csv_code": None,
        "signedxml": "<xml/>",
        "errorxml": None,
        "email": "customer@example.com",
        "tbai_code": "TBAI-1",
        "expedition_date": "2026-01-22",
        "total_amount": "22.00",
        "get_name": lambda: "TK-2026-GOI/1",
        "get_pdf_name": lambda: "TK-2026-GOI_1",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_admin_exposes_actions_and_status_columns():
    model_admin = admin.site._registry[Invoice]

    assert "send_status" in model_admin.list_display
    assert "has_pdf" in model_admin.list_display
    assert "retry_send" in model_admin.actions
    assert "regenerate_pdf" in model_admin.actions
    assert "resend_email" in model_admin.actions
    assert str(model_admin.send_status(invoice())) == "Pending"
    assert str(model_admin.send_status(invoice(errorxml="error"))) == "Error"
    assert str(model_admin.send_status(invoice(csv_code="CSV"))) == "Sent"
    assert model_admin.has_pdf(invoice(pdf="x")) is True
    assert model_admin.has_pdf(invoice(pdf=None)) is False


def test_retry_send_sends_pending_invoice():
    model_admin = make_admin()
    pending = invoice()
    config = config_with()

    def fake_send(tbai, target, target_config):
        target.csv_code = "CSV-1"
        return target

    with (
        patch(
            "django_ticketbai.admin.Config.objects.filter",
            return_value=SimpleNamespace(first=lambda: config),
        ),
        patch("django_ticketbai.admin.TBai"),
        patch("django_ticketbai.admin.send_invoice", side_effect=fake_send) as send,
    ):
        model_admin.retry_send(SimpleNamespace(), FakeQuerySet([pending]))

    send.assert_called_once()
    assert pending.csv_code == "CSV-1"
    model_admin.message_user.assert_any_call(
        SimpleNamespace(), "1 invoice(s) sent to TicketBAI.", messages.SUCCESS
    )


def test_retry_send_stops_when_certificate_is_expired():
    model_admin = make_admin()
    pending = invoice()
    config = config_with(status="expired")

    with (
        patch(
            "django_ticketbai.admin.Config.objects.filter",
            return_value=SimpleNamespace(first=lambda: config),
        ),
        patch("django_ticketbai.admin.TBai"),
        patch("django_ticketbai.admin.send_invoice") as send,
    ):
        model_admin.retry_send(SimpleNamespace(), FakeQuerySet([pending]))

    send.assert_not_called()
    assert model_admin.message_user.call_args.args[2] == messages.ERROR


def test_regenerate_pdf_uses_existing_invoice():
    model_admin = make_admin()
    target = invoice(pdf=Mock())
    config = config_with()

    with (
        patch(
            "django_ticketbai.admin.Config.objects.filter",
            return_value=SimpleNamespace(first=lambda: config),
        ),
        patch("django_ticketbai.admin.TBai") as tbai,
        patch("django_ticketbai.admin.build_pdf", return_value=b"%PDF-1.7"),
    ):
        tbai.return_value.subject.get_dict.return_value = {"name": "ACME"}
        model_admin.regenerate_pdf(SimpleNamespace(), FakeQuerySet([target]))

    target.pdf.save.assert_called_once()
    assert target.pdf.save.call_args.kwargs["save"] is True


def test_resend_email_only_attaches_the_pdf_and_sends():
    model_admin = make_admin()
    pdf = Mock()
    pdf.name = "ticketbai/TK-2026-GOI_1.pdf"
    pdf.read.return_value = b"%PDF-1.7"
    target = invoice(csv_code="CSV-1", pdf=pdf)

    with patch("django_ticketbai.admin.EmailMessage") as email_message:
        model_admin.resend_email(SimpleNamespace(), FakeQuerySet([target]))

    email_message.return_value.attach.assert_called_once()
    email_message.return_value.send.assert_called_once()
    pdf.close.assert_called_once()
