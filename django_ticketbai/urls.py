from django.urls import path
from .views import test_send_and_store_invoice

urlpatterns = [
    path(
        "test",
        test_send_and_store_invoice,
        name="ticketbai-test",
    ),
]
