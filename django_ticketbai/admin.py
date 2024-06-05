from django.contrib import admin
from django.conf import settings
from .models import Invoice, InvoiceLine, Config
from .forms import ConfigForm
from django.utils.translation import gettext as _


class ConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            _("Invoice serial code"),
            {"fields": ("prefix", "suffix", "logo")},
        ),
        (
            _("Certificate"),
            {"fields": ("pks12", "password")},
        ),
    )
    form = ConfigForm


class InvoiceLines(admin.TabularInline):
    model = InvoiceLine
    exclude = ["vat_type", "vat_fee"]


class InvoiceAdmin(admin.ModelAdmin):
    def has_signature(self, obj):
        return obj.signature_value and True or False

    has_signature.short_description = _("Has signature  ")
    has_signature.boolean = True

    list_display = (
        "expedition_date",
        "get_name",
        "email",
        "simplified",
        "substitution",
        "vat_regime",
        "total_amount",
        "has_signature",
        "pre_invoice",
    )
    list_display_links = ("expedition_date", "get_name")
    ordering = ("-expedition_date",)
    search_fields = ["serial_code", "num"]
    raw_id_fields = ["pre_invoice"]
    inlines = [
        InvoiceLines,
    ]

    fieldsets = (
        (
            _("Basic"),
            {
                "fields": (
                    "serial_code",
                    "num",
                    "description",
                    "total_amount",
                    "vat_breakdown",
                    "email",
                    "lang",
                )
            },
        ),
        (
            _("Dates"),
            {
                "fields": (
                    ("expedition_date", "expedition_time"),
                    "transaction_date",
                )
            },
        ),
        (
            _("Detail"),
            {
                "fields": (
                    "simplified",
                    "substitution",
                    "vat_regime",
                )
            },
        ),
        (
            "TicketBai",
            {
                "fields": (
                    "tbai_code",
                    "csv_code",
                    "signature_value",
                    "pre_invoice",
                    "pdf",
                    "signedxml",
                    "errorxml",
                )
            },
        ),
    )

    # def has_add_permission(self, request, obj=None):
    #     return False

    # def has_delete_permission(self, request, obj=None):
    #     return False


if hasattr(settings, 'TICKETBAI_CONF'):
    admin.site.register(Config, ConfigAdmin)
    admin.site.register(Invoice, InvoiceAdmin)
