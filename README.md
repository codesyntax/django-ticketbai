![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-ticketbai)
![Django versions](https://img.shields.io/badge/django-5.2%20%7C%206.0%20%7C%206.1-0C4B33)
![Status](https://img.shields.io/badge/status-stable-brightgreen)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/codesyntax/django-ticketbai/python-package.yml)
![PyPI - Version](https://img.shields.io/pypi/v/django-ticketbai)

# django-ticketbai

django-ticketbai allows to create, manage, store and send TicketBai invoices to the Basque tax authorities.

## Requirements

- Python 3.11 or newer
- Django 5.2, 6.0 or 6.1

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
| `pks12` | PKCS#12 (`.p12`) **client certificate** used to sign and send the invoices |
| `password` | Password of the certificate |
| `logo` | Optional logo shown in the invoice PDF |
| `is_active` | Only the active configuration is used |

At least one active `Config` object is required before creating an invoice.

### Certificate expiry monitoring

The `pks12` file is the client certificate used for the mutual-TLS connection
to the TicketBAI service.  When it expires, sending invoices fails with a TLS
error even if the service itself is available.

`django-ticketbai` can warn about this before it happens:

- The `Config` admin lists the certificate state and shows a warning on the
  changelist when the active certificate is expired or about to expire.
- `send_invoice` checks the certificate before contacting the authority.  An
  expired certificate is stored in `Invoice.errorxml` and no network request is
  made.
- The `check_ticketbai_certificate` management command can be run from cron or
  a scheduler.

Both settings are optional.  The warning threshold defaults to **30 days**.
The alert recipients default to the email addresses in Django's `ADMINS`
setting; set `TICKETBAI_CERTIFICATE_ALERT_EMAILS` explicitly to use another
list, or to `[]` to disable email alerts:

```python
# Optional: defaults to 30.
TICKETBAI_CERTIFICATE_WARNING_DAYS = 30

# Optional: defaults to settings.ADMINS.
TICKETBAI_CERTIFICATE_ALERT_EMAILS = ["operations@example.com"]
```

Run the check daily:

```bash
python manage.py check_ticketbai_certificate --fail-on expired
```

`--fail-on expired` exits with an error when the certificate has expired, so
the monitoring system also sees the failure.  Use `--fail-on expiring` to fail
for both expired and soon-to-expire certificates.  Add `--email` to notify
additional addresses, or `--warn-days` to override the configured threshold.

Example cron entry:

```cron
0 8 * * * cd /path/to/project && python manage.py check_ticketbai_certificate --fail-on expired
```

The command never prints or stores the certificate password or private key.

### Invoice admin actions

The `Invoice` changelist includes these actions:

- **Retry TicketBAI send**: sends invoices that have signed XML but no CSV.
  It processes them in invoice order, skips invoices that were already sent,
  checks the certificate first and stops at the first rejection. It never
  creates a new invoice.
- **Regenerate PDF**: builds the PDF from an existing signed invoice when the
  PDF file is missing. It does not re-sign or renumber the invoice.
- **Resend TicketBAI email**: sends the PDF to `Invoice.email`, but only when
  the invoice has a CSV (accepted by TicketBAI) and a PDF. This prevents
  sending an unaccepted ticket to a customer.

The changelist also has **TicketBAI status** (Sent/Error/Pending) and **Has
PDF** filters, and searches by email, TicketBAI code and CSV.

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
