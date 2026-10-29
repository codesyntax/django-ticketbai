from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError
from requests.exceptions import SSLError

from django_ticketbai.utils.invoice import (
    calculate_num,
    create_tbai_code,
    get_invoice_fingerprint,
    send_invoice,
)
from django_ticketbai.validators import validate_pdf_extension, validate_pks_extension


def test_get_invoice_fingerprint_without_previous_invoice():
    assert get_invoice_fingerprint(None) is None


def test_get_invoice_fingerprint():
    previous = SimpleNamespace(
        serial_code="TB-2025",
        num=7,
        expedition_date=date(2025, 7, 5),
        signature_value="AbCdEfGhIj",
    )

    assert get_invoice_fingerprint(previous) == {
        "serial_code": "TB-2025",
        "num": "7",
        "expedition_date": "05-07-2025",
        "signature_value": "AbCdEfGhIj",
    }


def test_create_tbai_code():
    invoice = SimpleNamespace(
        expedition_date=date(2025, 7, 5),
        signature_value="0123456789abcdef",
    )

    code = create_tbai_code(invoice, {"entity_id": "F20704375"})

    assert code.startswith("TBAI-F20704375-050725-0123456789abc-")
    crc = code.rsplit("-", 1)[1]
    assert crc.isdigit()
    assert len(crc) == 3


def test_create_tbai_code_is_deterministic():
    invoice = SimpleNamespace(
        expedition_date=date(2025, 7, 5),
        signature_value="0123456789abcdef",
    )

    assert create_tbai_code(invoice, {"entity_id": "F20704375"}) == create_tbai_code(
        invoice, {"entity_id": "F20704375"}
    )


def test_calculate_num_without_previous_invoice():
    assert calculate_num("TB-2025", 1, None) == 1


def test_calculate_num_increments_the_previous_invoice_of_the_same_year():
    previous = SimpleNamespace(num=4, expedition_date=date(2025, 1, 2))

    assert calculate_num("TB-2025", 1, previous) == 5


def test_calculate_num_restarts_for_another_year():
    previous = SimpleNamespace(num=4, expedition_date=date(2024, 1, 2))

    assert calculate_num("TB-2025", 1, previous) == 1


def test_validate_pdf_extension_accepts_pdf():
    validate_pdf_extension(SimpleNamespace(name="invoice.pdf"))


def test_validate_pdf_extension_rejects_other_extensions():
    with pytest.raises(ValidationError):
        validate_pdf_extension(SimpleNamespace(name="invoice.txt"))


def test_validate_pks_extension_accepts_p12():
    validate_pks_extension(SimpleNamespace(name="/media/certs/cert.p12"))


def test_validate_pks_extension_rejects_other_extensions():
    with pytest.raises(ValidationError):
        validate_pks_extension(SimpleNamespace(name="/media/certs/cert.pem"))


def test_send_invoice_stores_the_csv_on_success():
    invoice = SimpleNamespace(
        pk=42, signedxml="<xml/>", csv_code=None, errorxml=None, save=Mock()
    )
    config = SimpleNamespace(
        pks12=SimpleNamespace(name="certs/cert.p12"), password="secret"
    )
    tbai = SimpleNamespace(
        send=Mock(return_value={"status": 200, "CSV": "CSV-1", "ErrorXML": None})
    )

    result = send_invoice(tbai, invoice, config)

    assert result is invoice
    assert invoice.csv_code == "CSV-1"
    invoice.save.assert_called_once_with()


def test_send_invoice_logs_and_stores_request_errors(caplog):
    invoice = SimpleNamespace(
        pk=42, signedxml="<xml/>", csv_code=None, errorxml=None, save=Mock()
    )
    config = SimpleNamespace(
        pks12=SimpleNamespace(name="certs/cert.p12"), password="secret"
    )
    tbai = SimpleNamespace(send=Mock(side_effect=SSLError("certificate verify failed")))

    with pytest.raises(SSLError):
        send_invoice(tbai, invoice, config)

    assert invoice.errorxml == "certificate verify failed"
    invoice.save.assert_called_once_with(update_fields=["errorxml"])
    assert "TicketBAI send failed for invoice 42" in caplog.text


def test_send_invoice_logs_the_error_payload_when_the_service_rejects_it(caplog):
    invoice = SimpleNamespace(
        pk=42, signedxml="<xml/>", csv_code=None, errorxml=None, save=Mock()
    )
    config = SimpleNamespace(
        pks12=SimpleNamespace(name="certs/cert.p12"), password="secret"
    )
    tbai = SimpleNamespace(
        send=Mock(
            return_value={
                "status": 500,
                "CSV": None,
                "ErrorXML": "connection error",
            }
        )
    )

    send_invoice(tbai, invoice, config)

    assert invoice.errorxml == "connection error"
    assert "TicketBAI send failed for invoice 42" in caplog.text
    invoice.save.assert_called_once_with()
