from django.urls import path
from .views import test_send_and_store_invoice,show_pdf_html

urlpatterns = [
    path(
        "test",
        test_send_and_store_invoice,
        name="ticketbai-test",
    ),
    path(
        "show-pdf-html/<int:invoice_id>/",
        show_pdf_html,
        name="ticketbai-show-pdf-html",
    ),
]
