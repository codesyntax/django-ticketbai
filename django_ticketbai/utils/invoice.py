from django.conf import settings
import crc8
import json
from django.core.files.base import ContentFile
from django.utils import timezone
from django_ticketbai.models import Config, Invoice, InvoiceLine
from django_ticketbai.utils.pdf import build_pdf
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from pytbai import TBai
from decimal import Decimal
from django_ticketbai.models import Config


def calculate_serial_code():
    config = Config.objects.filter(is_active=True).first()
    year = timezone.now().year
    suffix = config.suffix
    if suffix:
        suffix = "-{}".format(suffix)
    else:
        suffix = ""
    return "{}-{}{}".format(config.prefix, year, suffix)


def calculate_num(serial_code, num, prev_invoice):
    num = 1
    if prev_invoice and str(prev_invoice.expedition_date.year) in serial_code:
        num = prev_invoice.num + 1
    return num


def get_prev_invoice():
    invoice = (
        Invoice.objects.filter(signature_value__isnull=False)
        .exclude(signature_value__iexact="")
        .order_by("-id")
        .first()
    )
    return invoice


def get_invoice_fingerprint(prev_invoice):
    if not prev_invoice:
        return None
    return {
        "serial_code": prev_invoice.serial_code,
        "num": str(prev_invoice.num),
        "expedition_date": prev_invoice.expedition_date.strftime("%d-%m-%Y"),
        "signature_value": prev_invoice.signature_value,
    }


def create_tbai_code(invoice, subject):
    tbai_code = "TBAI-{}-{}-{}-".format(
        subject["entity_id"],
        invoice.expedition_date.strftime("%d%m%y"),
        invoice.signature_value[:13],
    )
    hash = crc8.crc8()
    hash.update(tbai_code.encode("utf-8"))
    tbai_code += "{}".format(str(int(hash.hexdigest(), 16)).rjust(3, "0"))
    return tbai_code


def store_invoice(tbai_struct, result, email=None):
    invoice_struct = tbai_struct["invoice"]
    subject_struct = tbai_struct["subject"]
    lines = invoice_struct.pop("lines")
    invoice = Invoice(**invoice_struct)
    if email:
        invoice.email = email
    invoice.vat_breakdown = json.dumps(invoice_struct["vat_breakdown"])
    invoice.save()
    for line in lines:
        invoiceline = InvoiceLine(**line)
        invoiceline.invoice = invoice
        invoiceline.save()

    if result["TBAI_ID"]:
        invoice.csv_code = result["CSV"]
        invoice.signedxml = result["SignedXML"]
        invoice.tbai_code = result["TBAI_ID"]
        invoice.save()
        pdf = build_pdf(invoice, subject_struct)
        invoice.pdf = ContentFile(pdf, "{}.pdf".format(invoice.get_pdf_name()))
    else:
        invoice.errorxml = result["ResponseXML"]
    invoice.save()
    return invoice


def create_one_line_simplified_invoice(
    TICKETBAI_CONF,
    invoice_description,
    email,
    line_description,
    unit,
    price,
    vat,
):
    config = Config.objects.filter(is_active=True).first()
    prev_invoice = get_prev_invoice()
    serial_code = calculate_serial_code()
    num = calculate_num(serial_code, None, prev_invoice)
    prev_inv_fp = get_invoice_fingerprint(prev_invoice)

    tbai = TBai(TICKETBAI_CONF)
    invoice = tbai.create_invoice(
        serial_code, num, invoice_description, simplified="S"
    )
    invoice.create_line(
        line_description, Decimal(unit), Decimal(price), Decimal(vat)
    )

    result = tbai.sign_and_send(
        invoice,
        "{}/{}".format(settings.MEDIA_ROOT, config.pks12.name),
        config.password,
        prev_inv_fp,
    )

    tbai_struct = json.loads(tbai.get_json(invoice))
    stored_invoice = store_invoice(tbai_struct, result, email)
    if prev_invoice:
        stored_invoice.pre_invoice = prev_invoice
        stored_invoice.save()
    return True
