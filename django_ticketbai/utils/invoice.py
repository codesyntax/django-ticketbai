from django.conf import settings
from django.utils import timezone
from django_ticketbai.models import Config, Invoice, InvoiceLine


def calculate_serial_code():
    config = Config.objects.filter(is_active=True).first()
    year = timezone.now().year
    suffix = config.suffix
    if suffix:
        suffix = "-{}".format(suffix)
    else:
        suffix = ""
    return "{}-{}{}".format(config.prefix, year, suffix)


def get_prev_invoice():
    invoice = Invoice.objects.all().order_by("-id").first()
    return invoice


def store_invoice(invoice_struct, result):
