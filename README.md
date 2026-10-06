![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-ticketbai)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/codesyntax/django-ticketbai/python-package.yml)
![PyPI - Version](https://img.shields.io/pypi/v/django-ticketbai)

# django-ticketbai

django-ticketbai allows to create, manage, store and send TicketBai invoices to the Basque tax authorities.

## Requirements

- Python 3.11 or newer
- Django 4.2 or 5.2

## Installation

```bash
pip install django-ticketbai
```

Add the app to `INSTALLED_APPS` and run its migrations:

```python
INSTALLED_APPS = [
    # ...
    "django_ticketbai",
]
```

```bash
python manage.py migrate django_ticketbai
```

## Configuration

Two things have to be configured:

| Data | Where |
| --- | --- |
| Issuer and software data | the `TICKETBAI_CONF` setting |
| Invoice series and signing certificate | the `Config` model (editable in the admin) |

### The `TICKETBAI_CONF` setting

`TICKETBAI_CONF` is a dictionary with two mandatory sections, `subject` (the
issuer of the invoices) and `software` (the TicketBai software declaration).
It is passed as-is to [`pytbai`](https://github.com/codesyntax/pytbai), so its
structure is the one `pytbai.TBai` expects:

```json
{
  "subject": {
    "entity_id": "B12345678",
    "name": "ACME S.L.",
    "address": "Main street 1",
    "territory": "Gipuzkoa"
  },
  "software": {
    "license": "TBAIGIPRE00000000001",
    "dev_entity": "B00000000",
    "soft_name": "django-ticketbai",
    "soft_version": "1.0"
  }
}
```

In your Django settings:

```python
TICKETBAI_CONF = {
    "subject": {
        "entity_id": "B12345678",
        "name": "ACME S.L.",
        "address": "Main street 1",
        "territory": "Gipuzkoa",
    },
    "software": {
        "license": "TBAIGIPRE00000000001",
        "dev_entity": "B00000000",
        "soft_name": "django-ticketbai",
        "soft_version": "1.0",
    },
}
```

#### `subject`

| Key | Required | Default | Description |
| --- | --- | --- | --- |
| `entity_id` | yes | – | Tax id (NIF) of the issuer |
| `name` | yes | – | Name of the issuer |
| `address` | no | `None` | Address shown in the invoice PDF |
| `territory` | no | `"Gipuzkoa"` | `Araba`, `Bizkaia` or `Gipuzkoa` |
| `multi_recipient` | no | `"N"` | `S` (yes) or `N` (no) |
| `external_invoice` | no | `"N"` | `N`, `T` or `D`, see `pytbai.definitions.L4` |

#### `software`

| Key | Required | Default | Description |
| --- | --- | --- | --- |
| `license` | yes | – | TicketBai licence of the software |
| `dev_entity` | yes | – | Tax id (NIF) of the software developer |
| `soft_name` | yes | – | Name of the software |
| `soft_version` | yes | – | Version of the software |

#### Notes

- Do **not** add `env` to `TICKETBAI_CONF`: `django-ticketbai` sets it
  automatically.
- Test or production endpoint is chosen with the `DEBUG` setting:
  `DEBUG = True` sends the invoices to the testing environment and
  `DEBUG = False` to the production one. Make sure `DEBUG` is `False` in
  production, otherwise the invoices are not sent to the Basque tax
  authorities but to the test service.
- The models are registered in the Django admin only when the
  `TICKETBAI_CONF` setting is defined.
- The bundled test view (`django_ticketbai.views.test_send_and_store_invoice`)
  answers `KO` when the setting is missing.

### The `Config` model

The `Config` model holds the data that can change between installations, and it
is meant to be edited in the Django admin:

| Field | Description |
| --- | --- |
| `prefix`, `suffix` | Invoice series |
| `pks12` | PKCS#12 (`.p12`) certificate used to sign the invoices |
| `password` | Password of the certificate |
| `logo` | Optional logo shown in the invoice PDF |
| `is_active` | Only the active configuration is used |

At least one active `Config` object is required before creating an invoice.

## Usage

```python
from django.conf import settings

from django_ticketbai.utils.invoice import create_one_line_simplified_invoice

invoice = create_one_line_simplified_invoice(
    settings.TICKETBAI_CONF,
    "Simplified invoice",  # invoice description
    "customer@example.com",  # recipient email
    "Product",  # line description
    "1",  # quantity
    "200",  # unit price
)
```

The invoice is signed with the certificate of the active `Config`, stored, and
sent to the corresponding endpoint. The signature of the previous invoice is
chained automatically. The PDF is stored in the `pdf` field of the invoice.
