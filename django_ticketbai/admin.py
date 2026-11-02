from django.contrib import admin, messages
from django.conf import settings
from django.utils.html import format_html
from django.utils.translation import gettext as _
from .models import Invoice, InvoiceLine, Config
from .forms import ConfigForm


class ConfigAdmin(admin.ModelAdmin):
    list_display = ("__str__", "is_active", "certificate_state")
    list_display_links = ("__str__",)
    readonly_fields = ("certificate_state",)
    fieldsets = (
        (
            _("Invoice serial code"),
            {"fields": ("prefix", "suffix", "logo")},
        ),
        (
            _("Certificate"),
            {"fields": ("pks12", "password", "certificate_state")},
        ),
    )
    form = ConfigForm

    @admin.display(description=_("Certificate status"))
    def certificate_state(self, obj):
        info = obj.certificate_info()
        if info.status == "expired":
            return format_html(
                '<span style="color:#b00020;font-weight:bold">{}</span>',
                _("Expired on %(date)s") % {"date": info.not_after.date()},
            )
        if info.status == "expiring":
            return format_html(
                '<span style="color:#b36b00;font-weight:bold">{}</span>',
                _("%(days)s days left") % {"days": info.days_left},
            )
        if info.status == "valid":
            return format_html(
                "{}",
                _("Valid until %(date)s") % {"date": info.not_after.date()},
            )
        return _("Unknown")

    def changelist_view(self, request, extra_context=None):
        for config in Config.objects.filter(is_active=True):
            info = config.certificate_info()
            if info.status == "expired":
                messages.error(
                    request,
                    _(
                        "The TicketBAI client certificate for %(config)s expired "
                        "on %(date)s. Sending invoices will fail until it is renewed."
                    )
                    % {"config": config, "date": info.not_after.date()},
                )
            elif info.status == "expiring":
                messages.warning(
                    request,
                    _(
                        "The TicketBAI client certificate for %(config)s expires "
                        "in %(days)s days, on %(date)s."
                    )
                    % {
                        "config": config,
                        "days": info.days_left,
                        "date": info.not_after.date(),
                    },
                )
        return super().changelist_view(request, extra_context)


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


if hasattr(settings, "TICKETBAI_CONF"):
    admin.site.register(Config, ConfigAdmin)
    admin.site.register(Invoice, InvoiceAdmin)
