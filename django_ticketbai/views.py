from django.http import JsonResponse
from django.conf import settings
from django_ticketbai.utils.invoice import create_one_line_simplified_invoice

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
