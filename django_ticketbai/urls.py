from django.urls import path
from .views import send_and_store_invoice

urlpatterns = [
    path(
        "test/<str:description>",
        send_and_store_invoice,
        name="ticketbai-test",
    ),
    path(
        "test/<str:description>/<int:num>",
        send_and_store_invoice,
        name="ticketbai-test",
    ),
]
