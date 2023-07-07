# -*- coding: utf-8 -*-
from pytbai.definitions import DEFAULT_VAT, N, DEFAULT_VAT_RATE, S1, L11
from django.db import models
from django.utils.translation import gettext as _
from .validators import validate_pdf_extension, validate_pks_extension
from django.conf import settings

User = settings.AUTH_USER_MODEL
VAT_TYPE_CHOICES = ((row, row) for row in L11)


class Config(models.Model):
    prefix = models.CharField(max_length=5)
    suffix = models.CharField(max_length=5, null=True, blank=True)
    pks12 = models.FileField(
        upload_to="certs",
        null=True,
        blank=True,
        verbose_name=_("Certificate"),
        validators=[validate_pks_extension],
    )
    password = models.CharField(max_length=200, null=True, blank=True)
    is_active = models.BooleanField(default=True)

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
    serial_code = models.CharField(max_length=20)
    num = models.IntegerField()
    description = models.CharField(max_length=255)
    simplified = models.CharField(max_length=2, default=N)
    substitution = models.CharField(max_length=2, default=N)
    email = models.EmailField(null=True, blank=True)
    vat_regime = models.CharField(max_length=2, default=DEFAULT_VAT)
    total_amount = models.DecimalField(
        default=0, max_digits=7, decimal_places=2
    )
    expedition_date = models.DateField()
    expedition_time = models.TimeField()
    transaction_date = models.DateField()
    tbai_code = models.CharField(max_length=40, null=True, blank=True)
    csv_code = models.CharField(max_length=40, null=True, blank=True)
    signedxml = models.TextField(null=True, blank=True)
    errorxml = models.TextField(null=True, blank=True)
    pdf = models.FileField(
        upload_to="ticketbai",
        null=True,
        blank=True,
        verbose_name=_("PDF file"),
        validators=[validate_pdf_extension],
    )

    def get_name(self):
        return "{}/{}".format(self.serial_code, self.num)

    def __str__(self):
        return self.get_name()

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(default=0, max_digits=7, decimal_places=2)
    unit_amount = models.DecimalField(
        default=0, max_digits=7, decimal_places=2
    )
    discount = models.DecimalField(default=0, max_digits=4, decimal_places=2)
    vat_rate = models.DecimalField(
        default=DEFAULT_VAT_RATE, max_digits=4, decimal_places=2
    )
    vat_type = models.CharField(
        max_length=2, choices=VAT_TYPE_CHOICES, default=S1
    )
    vat_base = models.DecimalField(default=0, max_digits=7, decimal_places=2)
    vat_fee = models.DecimalField(default=0, max_digits=7, decimal_places=2)
    total = models.DecimalField(default=0, max_digits=7, decimal_places=2)

    def __str__(self):
        return "{} {}".format(self.invoice.get_name(), self.description)

    class Meta:
        verbose_name = _("Invoice Line")
        verbose_name_plural = _("Invoice lines")
