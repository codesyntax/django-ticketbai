# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import json
from pytbai.definitions import DEFAULT_VAT, N, DEFAULT_VAT_RATE, S1, L11
from django.db import models
from django.utils.translation import gettext as _
from .validators import validate_pdf_extension, validate_pks_extension
from django.conf import settings


User = settings.AUTH_USER_MODEL
VAT_TYPE_CHOICES = ((row, row) for row in L11)
LANGUAGE_CODE = getattr(settings, "LANGUAGE_CODE", "en")


class Config(models.Model):
    logo = models.CharField(max_length=150, null=True, blank=True, verbose_name=_("Logo"), help_text=_("Relative path to the logo"))
    prefix = models.CharField(max_length=5, verbose_name=_("Prefix"))
    suffix = models.CharField(
        max_length=5, null=True, blank=True, verbose_name=_("Suffix")
    )
    pks12 = models.FileField(
        upload_to="certs",
        null=True,
        blank=True,
        verbose_name=_("Certificate"),
        validators=[validate_pks_extension],
    )
    password = models.CharField(
        max_length=200, null=True, blank=True, verbose_name=_("Password")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    def save(self, *args, **kwargs):
        super(Config, self).save(*args, **kwargs)

    def __str__(self):
        return "{}-YYYY{}".format(
            self.prefix, self.suffix and "-{}".format(self.suffix) or ""
        )

    class Meta:
        verbose_name = _("Configuration")
        verbose_name_plural = _("Configurations")


class Invoice(models.Model):
    serial_code = models.CharField(
        max_length=20, verbose_name=_("Serial code")
    )
    num = models.IntegerField(verbose_name=_("Number"))
    description = models.CharField(
        max_length=255, verbose_name=_("Description")
    )
    simplified = models.CharField(
        max_length=2, default=N, verbose_name=_("Simplified")
    )
    substitution = models.CharField(
        max_length=2, default=N, verbose_name=_("Substitution")
    )
    email = models.EmailField(null=True, blank=True, verbose_name=_("Email"))
    vat_regime = models.CharField(
        max_length=2, default=DEFAULT_VAT, verbose_name=_("VAT regime")
    )
    total_amount = models.DecimalField(
        default=0,
        max_digits=7,
        decimal_places=2,
        verbose_name=_("Total amount"),
    )
    vat_breakdown = models.TextField(verbose_name=_("VAT breakdown"))
    expedition_date = models.DateField(verbose_name=_("Expedition date"))
    expedition_time = models.TimeField(verbose_name=_("Expedition time"))
    transaction_date = models.DateField(verbose_name=_("Transaction date"))
    tbai_code = models.CharField(
        max_length=40, null=True, blank=True, verbose_name=_("TicketBai code")
    )
    csv_code = models.CharField(
        max_length=40, null=True, blank=True, verbose_name=_("CSV")
    )
    signature_value = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("Signature Value"),
    )
    signedxml = models.TextField(
        null=True, blank=True, verbose_name=_("Signed XML")
    )
    errorxml = models.TextField(
        null=True, blank=True, verbose_name=_("Error XML")
    )
    pdf = models.FileField(
        upload_to="ticketbai",
        null=True,
        blank=True,
        verbose_name=_("PDF file"),
        validators=[validate_pdf_extension],
    )
    pre_invoice = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        verbose_name=_("Previous invoice"),
        on_delete=models.SET_NULL,
    )
    lang = models.CharField(max_length=3, default=LANGUAGE_CODE)

    def get_name(self):
        return "{}/{}".format(self.serial_code, self.num)

    get_name.short_description = _("Serie")

    def get_pdf_name(self):
        return "{}_{}".format(self.serial_code, self.num)

    def get_lines(self):
        return self.lines.all()

    def get_vat_breakdown(self):
        return json.loads(self.vat_breakdown)

    def save(self, *args, **kwargs):
        if self.signedxml:
            root = ET.fromstring(self.signedxml)
            signature = root.find(
                "{http://www.w3.org/2000/09/xmldsig#}Signature"
            )
            signaturevalue = signature.find(
                "{http://www.w3.org/2000/09/xmldsig#}SignatureValue"
            )
            self.signature_value = signaturevalue.text[:100]
        super(Invoice, self).save(*args, **kwargs)

    def __str__(self):
        return self.get_name()

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="lines"
    )
    description = models.CharField(
        max_length=255, verbose_name=_("Description")
    )
    quantity = models.DecimalField(
        default=0, max_digits=7, decimal_places=2, verbose_name=_("Quantity")
    )
    unit_amount = models.DecimalField(
        default=0,
        max_digits=7,
        decimal_places=2,
        verbose_name=_("Unit Amount"),
    )
    discount = models.DecimalField(
        default=0, max_digits=4, decimal_places=2, verbose_name=_("Discount")
    )
    vat_rate = models.DecimalField(
        default=DEFAULT_VAT_RATE,
        max_digits=4,
        decimal_places=2,
        verbose_name=_("VAT rate"),
    )
    vat_type = models.CharField(
        max_length=2,
        choices=VAT_TYPE_CHOICES,
        default=S1,
        verbose_name=_("VAT type"),
    )
    vat_base = models.DecimalField(
        default=0, max_digits=7, decimal_places=2, verbose_name=_("VAT base")
    )
    vat_fee = models.DecimalField(
        default=0, max_digits=7, decimal_places=2, verbose_name=_("VAT fee")
    )
    total = models.DecimalField(
        default=0, max_digits=7, decimal_places=2, verbose_name=_("Total")
    )

    def __str__(self):
        return "{} {}".format(self.invoice.get_name(), self.description)

    class Meta:
        verbose_name = _("Invoice Line")
        verbose_name_plural = _("Invoice lines")
