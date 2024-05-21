from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
import json
from django_ticketbai.models import Config, Invoice
from django_ticketbai.utils.invoice import create_one_line_simplified_invoice
from django_ticketbai.utils.pdf import get_css_string, get_html_string
from pytbai import TBai
from weasyprint import HTML, CSS

TICKETBAI_CONF = getattr(settings, "TICKETBAI_CONF", None)


def test_send_and_store_invoice(request):
    if not TICKETBAI_CONF:
        return JsonResponse({"response": "KO", "test": "KO"}, status=200)
    create_one_line_simplified_invoice(
        TICKETBAI_CONF,
        "Simplified invoice",
        "uodriozola@codesyntax.com",
        "Product description",
        "1",
        "200",
        "20",
    )
    return JsonResponse({"response": "OK", "test": "OK"}, status=201)


def show_pdf_html(request, invoice_id):
    config = Config.objects.filter(is_active=True).first()
    invoice = get_object_or_404(Invoice, id=invoice_id)
    tbai = TBai(TICKETBAI_CONF)
    tbai_json = json.loads(tbai.get_json())
    css = get_css_string()
    html = get_html_string(invoice, tbai_json["subject"], config.logo, css)
    return HttpResponse(html)