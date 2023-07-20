from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django_ticketbai.models import Config, Invoice, InvoiceLine
from django_ticketbai.utils.pdf import build_pdf


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


def store_invoice(tbai_struct, result, email=None):
    invoice_struct = tbai_struct["invoice"]
    lines = invoice_struct.pop("lines")
    invoice = Invoice(**invoice_struct)
    if email:
        invoice.email = email
    invoice.save()
    for line in lines:
        invoiceline = InvoiceLine(**line)
        invoiceline.invoice = invoice
        invoiceline.save()

    if result["TBAI_ID"]:
        invoice.tbai_code = result["TBAI_ID"]
        invoice.csv_code = result["CSV"]
        invoice.signedxml = result["SignedXML"]
        invoice.save()
        pdf = build_pdf(invoice, result["TBAI_ID"], tbai_struct["subject"])
        invoice.pdf = ContentFile(pdf, "{}.pdf".format(invoice.get_pdf_name()))
    else:
        invoice.errorxml = result["ResponseXML"]

    invoice.save()
    return invoice
