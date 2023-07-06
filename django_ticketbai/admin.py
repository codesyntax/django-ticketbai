from django.contrib import admin
from django.conf import settings
from .models import Invoice, InvoiceLine, Config
from django.utils.translation import gettext as _


class ConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            _("Invoice serial code"),
            {"fields": ("prefix", "suffix")},
        ),
        (
            _("Certificate"),
            {"fields": ("pks12", "password")},
        ),
    )


class InvoiceLines(admin.TabularInline):
    model = InvoiceLine
    exclude = ["vat_type", "vat_fee"]


class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "expedition_date",
        "get_name",
        "user",
        "simplified",
        "substitution",
        "vat_regime",
        "total_amount",
    )
    list_display_links = ("expedition_date", "get_name")
    ordering = ("-expedition_date",)
    search_fields = ["serial_code", "num"]
    inlines = [
        InvoiceLines,
    ]

    fieldsets = (
        (
            _("Basic"),
            {"fields": ("serial_code", "num", "description", "total_amount")},
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
            _("TicketBai"),
            {"fields": ("tbai_code", "csv_code", "pdf", "signedxml")},
        ),
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


if settings.TICKETBAI_CONF:
    admin.site.register(Config, ConfigAdmin)
    admin.site.register(Invoice, InvoiceAdmin)
