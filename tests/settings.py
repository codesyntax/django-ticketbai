SECRET_KEY = "django-ticketbai-tests"
DEBUG = False
USE_TZ = True
USE_I18N = True
LANGUAGE_CODE = "eu"
TIME_ZONE = "Europe/Madrid"
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_ticketbai",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

STATIC_URL = "/static/"
STATIC_ROOT = "/tmp/django-ticketbai-static"
MEDIA_URL = "/media/"
MEDIA_ROOT = "/tmp/django-ticketbai-media"

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
