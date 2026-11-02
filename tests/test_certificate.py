from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from django_ticketbai.utils.certificate import inspect_certificate


def make_p12(not_before, not_after, password="secret"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "TicketBAI test")]
    )
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        b"test",
        key,
        certificate,
        None,
        serialization.BestAvailableEncryption(password.encode()),
    )


def p12_field(data):
    return SimpleNamespace(read=lambda: data)


def test_inspect_certificate_valid():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    data = make_p12(now - timedelta(days=1), now + timedelta(days=90))

    info = inspect_certificate(p12_field(data), "secret", warn_days=30, now=now)

    assert info.status == "valid"
    assert info.days_left == 90
    assert info.not_after.date() == (now + timedelta(days=90)).date()
    assert info.error is None


def test_inspect_certificate_expiring():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    data = make_p12(now - timedelta(days=1), now + timedelta(days=10))

    info = inspect_certificate(p12_field(data), "secret", warn_days=30, now=now)

    assert info.status == "expiring"
    assert info.days_left == 10


def test_inspect_certificate_expired():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    data = make_p12(now - timedelta(days=10), now - timedelta(days=1))

    info = inspect_certificate(p12_field(data), "secret", warn_days=30, now=now)

    assert info.status == "expired"
    assert info.days_left == -1


def test_inspect_certificate_unknown_on_wrong_password():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    data = make_p12(now - timedelta(days=1), now + timedelta(days=90))

    info = inspect_certificate(p12_field(data), "wrong", now=now)

    assert info.status == "unknown"
    assert info.error


def test_inspect_certificate_unknown_without_file():
    info = inspect_certificate(None, "secret")

    assert info.status == "unknown"
    assert info.error == "No certificate file configured"
