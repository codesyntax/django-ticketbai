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

LANGUAGE_CODE = getattr(settings, "LANGUAGE_CODE", "en")


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


def store_invoice(tbai, tbai_invoice, lang, prev_invoice=None, email=None):
    tbai_json = json.loads(tbai.get_json(tbai_invoice))
    invoice_json = tbai_json["invoice"]
    subject_json = tbai_json["subject"]
    lines = invoice_json.pop("lines")
    invoice = Invoice(**invoice_json)
    invoice.lang = lang
    if email:
        invoice.email = email
    invoice.vat_breakdown = json.dumps(invoice_json["vat_breakdown"])
    invoice.save()
    for line in lines:
        invoiceline = InvoiceLine(**line)
        invoiceline.invoice = invoice
        invoiceline.save()

    if prev_invoice:
        invoice.pre_invoice = prev_invoice
        invoice.save()

    invoice = Invoice.objects.get(id=invoice.id)
    invoice.save()
    return invoice

def sign_invoice(tbai, invoice, prev_invoice, tbai_invoice, config):
    prev_inv_fp = get_invoice_fingerprint(prev_invoice)
    invoice.signedxml = tbai.sign(
        tbai_invoice,
        "{}/{}".format(settings.MEDIA_ROOT, config.pks12.name),
        config.password,
        prev_inv_fp,
    )
    invoice.save()
    tbai_json = json.loads(tbai.get_json(tbai_invoice))
    subject_json = tbai_json["subject"]
    invoice.tbai_code = create_tbai_code(invoice, subject_json)
    invoice.save()
    return invoice

def store_pdf(tbai, invoice, tbai_invoice, config):
    tbai_json = json.loads(tbai.get_json(tbai_invoice))
    subject_json = tbai_json["subject"]
    pdf = build_pdf(invoice, subject_json, config)
    invoice.pdf = ContentFile(pdf, "{}.pdf".format(invoice.get_pdf_name()))
    invoice.save()
    return invoice

def send_invoice(tbai, invoice, config):
    result = tbai.send(
        invoice.signedxml,
        "{}/{}".format(settings.MEDIA_ROOT, config.pks12.name),
        config.password,
    )

    if result["status"] == 200:
        invoice.csv_code = result["CSV"]
    else:
        invoice.errorxml = result["ErrorXML"]
    invoice.save()
    return invoice


def create_one_line_simplified_invoice(
    TICKETBAI_CONF,
    invoice_description,
    email,
    line_description,
    unit,
    price,
    discount=0,
    vat=21,
    vat_included=False,
    lang=LANGUAGE_CODE,
):
    config = Config.objects.filter(is_active=True).first()
    prev_invoice = get_prev_invoice()
    serial_code = calculate_serial_code()
    num = calculate_num(serial_code, None, prev_invoice)

    if settings.DEBUG:
        env="DEV"
    else:
        env="PROD"
    
    tbai = TBai(TICKETBAI_CONF, env=env)
    tbai_invoice = tbai.create_invoice(
        serial_code, num, invoice_description, simplified="S"
    )
    tbai_invoice.create_line(
        description=line_description, quantity=Decimal(unit), amount=Decimal(price), discount=Decimal(discount), vat_rate=Decimal(vat), vat_included=vat_included
    )

    invoice = store_invoice(tbai, tbai_invoice, lang, prev_invoice, email)
    invoice = sign_invoice(tbai, invoice, prev_invoice, tbai_invoice, config)
    invoice = store_pdf(tbai, invoice, tbai_invoice, config)
    invoice = send_invoice(tbai, invoice, config)

    return invoice
