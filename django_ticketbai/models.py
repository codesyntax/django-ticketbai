# -*- coding: utf-8 -*-
from pytbai.definitions import DEFAULT_VAT, N
from django.db import models
from django.utils.translation import gettext as _


class Invoice(models.Model):
    serial_code = models.CharField(max_length=255)
    num = models.IntegerField()
    description = models.CharField(max_length=255)
    simplified = models.CharField(max_length=2, default=DEFAULT_VAT)
    substitution = models.CharField(max_length=2, default=N)
    vat_regime = models.CharField(max_length=2, default=N)
    expedition_date = models.DateField()
    expedition_time = models.TimeField()
    transaction_date = models.DateField()

    def __str__(self):
        return "{}/{}".format(self.serial_code, self.num)

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
