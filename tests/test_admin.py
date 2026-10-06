from django.contrib import admin

from django_ticketbai.models import Config, Invoice


def test_models_are_registered_in_the_admin():
    assert Config in admin.site._registry
    assert Invoice in admin.site._registry


def test_invoice_admin_exposes_the_lang_field():
    model_admin = admin.site._registry[Invoice]
    fields = [
        field for _, options in model_admin.fieldsets for field in options["fields"]
    ]

    assert "lang" in fields


def test_config_admin_uses_the_password_widget():
    model_admin = admin.site._registry[Config]

    assert model_admin.form is not None
    assert model_admin.form.base_fields["password"].widget.__class__.__name__ == (
        "PasswordInput"
    )
