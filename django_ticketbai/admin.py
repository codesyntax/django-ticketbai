from django.conf import settings
from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.db.models import Q
from django.utils.html import format_html
from django.utils.translation import gettext as _
from pytbai import TBai

from .forms import ConfigForm
from .models import Config, Invoice, InvoiceLine
from .utils.invoice import send_invoice
from .utils.pdf import build_pdf


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


class TicketBaiStatusFilter(admin.SimpleListFilter):
    title = _("TicketBAI status")
    parameter_name = "tbai_status"

    def lookups(self, request, model_admin):
        return (
            ("sent", _("Sent")),
            ("error", _("Error")),
            ("pending", _("Pending")),
        )

    def queryset(self, request, queryset):
        no_csv = Q(csv_code__isnull=True) | Q(csv_code="")
        no_error = Q(errorxml__isnull=True) | Q(errorxml="")
        if self.value() == "sent":
            return queryset.exclude(no_csv)
        if self.value() == "error":
            return queryset.filter(no_csv).exclude(no_error)
        if self.value() == "pending":
            return queryset.filter(no_csv, no_error)
        return queryset


class HasPdfFilter(admin.SimpleListFilter):
    title = _("Has PDF")
    parameter_name = "has_pdf"

    def lookups(self, request, model_admin):
        return (("yes", _("Yes")), ("no", _("No")))

    def queryset(self, request, queryset):
        no_pdf = Q(pdf__isnull=True) | Q(pdf="")
        if self.value() == "yes":
            return queryset.exclude(no_pdf)
        if self.value() == "no":
            return queryset.filter(no_pdf)
        return queryset


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
        "send_status",
        "has_pdf",
        "has_signature",
        "pre_invoice",
    )
    list_display_links = ("expedition_date", "get_name")
    list_filter = (TicketBaiStatusFilter, HasPdfFilter)
    ordering = ("-expedition_date",)
    search_fields = ["serial_code", "num", "email", "tbai_code", "csv_code"]
    actions = ("retry_send", "regenerate_pdf", "resend_email")
    raw_id_fields = ["pre_invoice"]
    inlines = [
        InvoiceLines,
    ]

    @admin.display(description=_("TicketBAI"))
    def send_status(self, obj):
        if obj.csv_code:
            return _("Sent")
        if obj.errorxml:
            return _("Error")
        return _("Pending")

    @admin.display(boolean=True, description=_("PDF"))
    def has_pdf(self, obj):
        return bool(obj.pdf)

    def _active_config(self, request):
        config = Config.objects.filter(is_active=True).first()
        if config is None:
            self.message_user(
                request,
                _("There is no active TicketBAI configuration."),
                messages.ERROR,
            )
            return None
        return config

    @admin.action(description=_("Retry TicketBAI send"), permissions=["change"])
    def retry_send(self, request, queryset):
        config = self._active_config(request)
        if config is None:
            return
        info = config.certificate_info()
        if info.status in ("expired", "unknown"):
            self.message_user(
                request,
                _(
                    "TicketBAI certificate is not usable (%(status)s); "
                    "sending was not attempted."
                )
                % {"status": info.status},
                messages.ERROR,
            )
            return
        if info.status == "expiring":
            self.message_user(
                request,
                _("The TicketBAI certificate expires in %(days)s days.")
                % {"days": info.days_left},
                messages.WARNING,
            )

        invoices = list(
            queryset.filter(Q(csv_code__isnull=True) | Q(csv_code=""))
            .exclude(Q(signedxml__isnull=True) | Q(signedxml=""))
            .order_by("id")
        )
        if not invoices:
            self.message_user(
                request,
                _("No pending invoices with signed XML were selected."),
                messages.WARNING,
            )
            return

        try:
            tbai = TBai(
                settings.TICKETBAI_CONF,
                env="DEV" if settings.DEBUG else "PROD",
            )
        except Exception as exc:
            self.message_user(request, str(exc), messages.ERROR)
            return

        sent = 0
        for invoice in invoices:
            try:
                send_invoice(tbai, invoice, config)
            except Exception as exc:
                self.log_change(request, invoice, _("TicketBAI retry failed"))
                self.message_user(
                    request,
                    _("Invoice %(invoice)s failed: %(error)s")
                    % {"invoice": invoice.pk, "error": exc},
                    messages.ERROR,
                )
                break
            if not invoice.csv_code:
                self.log_change(request, invoice, _("TicketBAI retry failed"))
                self.message_user(
                    request,
                    _("Invoice %(invoice)s was not accepted: %(error)s")
                    % {
                        "invoice": invoice.pk,
                        "error": invoice.errorxml or _("unknown error"),
                    },
                    messages.ERROR,
                )
                break
            sent += 1
            self.log_change(request, invoice, _("TicketBAI retry succeeded"))

        if sent:
            self.message_user(
                request,
                _("%(count)s invoice(s) sent to TicketBAI.") % {"count": sent},
                messages.SUCCESS,
            )

    @admin.action(description=_("Regenerate PDF"), permissions=["change"])
    def regenerate_pdf(self, request, queryset):
        config = self._active_config(request)
        if config is None:
            return
        try:
            tbai = TBai(
                settings.TICKETBAI_CONF,
                env="DEV" if settings.DEBUG else "PROD",
            )
            subject = tbai.subject.get_dict()
        except Exception as exc:
            self.message_user(request, str(exc), messages.ERROR)
            return

        invoices = list(
            queryset.filter(Q(pdf__isnull=True) | Q(pdf=""))
            .exclude(Q(signedxml__isnull=True) | Q(signedxml=""))
            .order_by("id")
        )
        if not invoices:
            self.message_user(
                request,
                _("No invoices without a PDF were selected."),
                messages.WARNING,
            )
            return

        generated = 0
        for invoice in invoices:
            try:
                pdf = build_pdf(invoice, subject, config)
                invoice.pdf.save(
                    "{}.pdf".format(invoice.get_pdf_name()),
                    ContentFile(pdf),
                    save=True,
                )
            except Exception as exc:
                self.message_user(
                    request,
                    _("Invoice %(invoice)s PDF failed: %(error)s")
                    % {"invoice": invoice.pk, "error": exc},
                    messages.ERROR,
                )
                continue
            generated += 1
            self.log_change(request, invoice, _("TicketBAI PDF regenerated"))

        if generated:
            self.message_user(
                request,
                _("%(count)s PDF(s) regenerated.") % {"count": generated},
                messages.SUCCESS,
            )

    @admin.action(description=_("Resend TicketBAI email"), permissions=["change"])
    def resend_email(self, request, queryset):
        invoices = list(
            queryset.exclude(Q(csv_code__isnull=True) | Q(csv_code=""))
            .exclude(Q(pdf__isnull=True) | Q(pdf=""))
            .exclude(Q(email__isnull=True) | Q(email=""))
            .order_by("id")
        )
        if not invoices:
            self.message_user(
                request,
                _("No sent invoices with a PDF and recipient email were selected."),
                messages.WARNING,
            )
            return

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
        if not from_email:
            from_email = "noreply@localhost"
        sent = 0
        for invoice in invoices:
            subject = _("TicketBAI invoice %(invoice)s") % {
                "invoice": invoice.get_name()
            }
            body = _(
                "Hello,\n\n"
                "Attached is the TicketBAI invoice for your purchase.\n\n"
                "Invoice: %(invoice)s\n"
                "Date: %(date)s\n"
                "Total: %(total)s\n"
                "CSV: %(csv)s\n"
                "TicketBAI code: %(code)s\n"
            ) % {
                "invoice": invoice.get_name(),
                "date": invoice.expedition_date,
                "total": invoice.total_amount,
                "csv": invoice.csv_code,
                "code": invoice.tbai_code or "",
            }
            message = EmailMessage(subject, body, from_email, [invoice.email])
            try:
                invoice.pdf.open("rb")
                try:
                    message.attach(
                        invoice.pdf.name.rsplit("/", 1)[-1],
                        invoice.pdf.read(),
                        "application/pdf",
                    )
                finally:
                    invoice.pdf.close()
                message.send()
            except Exception as exc:
                self.message_user(
                    request,
                    _("Invoice %(invoice)s email failed: %(error)s")
                    % {"invoice": invoice.pk, "error": exc},
                    messages.ERROR,
                )
                continue
            sent += 1
            self.log_change(request, invoice, _("TicketBAI email resent"))

        if sent:
            self.message_user(
                request,
                _("%(count)s TicketBAI email(s) resent.") % {"count": sent},
                messages.SUCCESS,
            )

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
