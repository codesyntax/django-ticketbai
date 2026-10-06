import os
from datetime import date
from types import SimpleNamespace

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
django.setup()


@pytest.fixture
def subject():
    return {
        "name": "ACME S.L.",
        "address": "Main street 1",
        "entity_id": "B12345678",
        "qr_api": "https://tbai.egoitza.gipuzkoa.eus/qr/",
    }


@pytest.fixture
def invoice():
    """A lightweight stand-in for a stored Invoice (the PDF helpers only read attributes)."""
    line = SimpleNamespace(
        quantity="2",
        description="Service",
        unit_amount="50.00",
        discount="0",
        vat_base="100.00",
    )
    return SimpleNamespace(
        tbai_code="TBAI-B12345678-050725-abcdefghijklm-123",
        serial_code="TB-2025",
        num=1,
        total_amount="121.00",
        expedition_date=date(2025, 7, 5),
        expedition_time="12:00:00",
        lang="eu",
        get_lines=lambda: [line],
        get_vat_breakdown=lambda: [
            {"type": "S1", "rates": {"21": {"base": "100.00", "fee": "21.00"}}}
        ],
    )
