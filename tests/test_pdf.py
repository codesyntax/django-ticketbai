"""Tests for the PDF generation (templates + QR code + weasyprint).

These are the tests that catch the weasyprint/pydyf incompatibility that broke
PDF generation while ``weasyprint`` was pinned to 59.0.
"""

import base64
from types import SimpleNamespace

from django.test import override_settings
from PIL import Image

from django_ticketbai.utils.pdf import (
    build_pdf,
    create_qr_base64,
    get_crc8_url,
    get_css_string,
    get_html_string,
)


def test_get_crc8_url_appends_a_three_digit_crc():
    url = get_crc8_url("https://example.com/qr?a=1")

    assert url.startswith("https://example.com/qr?a=1&cr=")
    crc = url.rsplit("cr=", 1)[1]
    assert crc.isdigit()
    assert len(crc) == 3


def test_get_crc8_url_is_stable():
    assert get_crc8_url("https://example.com/qr") == get_crc8_url(
        "https://example.com/qr"
    )


def test_create_qr_base64_returns_a_jpeg(invoice, subject):
    qr = base64.b64decode(create_qr_base64(invoice, subject))

    assert qr.startswith(b"\xff\xd8")  # JPEG SOI marker
    assert qr.endswith(b"\xff\xd9")  # JPEG EOI marker


def test_get_css_string_returns_css():
    assert "{" in get_css_string()


def test_get_html_string_renders_the_invoice(invoice, subject):
    html = get_html_string(invoice, subject)

    assert "ACME S.L." in html
    assert "Main street 1" in html
    assert "IFZ: B12345678" in html
    assert "TB-2025/1" in html
    assert "121.00" in html
    assert "TBAI-B12345678-050725-abcdefghijklm-123" in html


def test_get_html_string_embeds_the_qr_code(invoice, subject):
    html = get_html_string(invoice, subject)

    assert 'src="data:image/jpeg;base64,' in html


def test_get_html_string_without_subject_address(invoice):
    """The address is optional in TICKETBAI_CONF."""
    subject = {
        "name": "ACME S.L.",
        "entity_id": "B12345678",
        "qr_api": "https://tbai.egoitza.gipuzkoa.eus/qr/",
    }

    assert "IFZ: B12345678" in get_html_string(invoice, subject)


def test_build_pdf_returns_a_pdf(invoice, subject):
    pdf = build_pdf(invoice, subject, SimpleNamespace(logo=None))

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_build_pdf_with_logo(invoice, subject, tmp_path):
    Image.new("RGB", (400, 120), "white").save(str(tmp_path / "logo.png"))

    with override_settings(STATIC_ROOT=str(tmp_path)):
        pdf = build_pdf(invoice, subject, SimpleNamespace(logo="logo.png"))

    assert pdf.startswith(b"%PDF")
