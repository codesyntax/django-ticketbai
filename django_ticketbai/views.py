import json
from pytbai import TBai
from decimal import Decimal
from django.shortcuts import render
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django_ticketbai.utils.invoice import (
    calculate_serial_code,
    get_prev_invoice,
    store_invoice,
)
from .models import Config, Invoice, InvoiceLine


TICKETBAI_CONF = getattr(settings, "TICKETBAI_CONF", None)

# TODO: TPV connection and TBai creation
def send_and_store_invoice(request):
    if not TICKETBAI_CONF:
        return None
    config = Config.objects.filter(is_active=True).first()
    serial_code = calculate_serial_code()
    num = 0

    prev_invoice = get_prev_invoice()
    if prev_invoice:
        num = prev_invoice.num + 1
    tbai = TBai(TICKETBAI_CONF)
    invoice = tbai.create_invoice(
        serial_code, num, "description", simplified="S"
    )
    for line in lines:
        invoice.create_line(
            "First product", Decimal("1"), Decimal("200"), Decimal("20")
        )

    result = tbai.sign_and_send(config.pks12.name, config.password)
    invoice_struct = json.load(tbai.get_json())
    store_invoice(invoice_struct, result)
    return True
