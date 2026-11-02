from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from cryptography.hazmat.primitives.serialization import pkcs12

CertificateStatus = Literal["valid", "expiring", "expired", "unknown"]
DEFAULT_WARNING_DAYS = 30


@dataclass(frozen=True)
class CertificateInfo:
    status: CertificateStatus
    not_after: datetime | None = None
    days_left: int | None = None
    subject: str | None = None
    issuer: str | None = None
    error: str | None = None


def _read_file(file_field) -> bytes:
    if file_field is None:
        raise ValueError("No certificate file configured")
    if hasattr(file_field, "open"):
        file_field.open("rb")
        try:
            return file_field.read()
        finally:
            file_field.close()
    return file_field.read()


def inspect_certificate(
    file_field,
    password: str | None,
    warn_days: int = 30,
    now: datetime | None = None,
) -> CertificateInfo:
    """Inspect the client certificate stored in a ``Config`` instance.

    Only the public certificate is returned.  The private key is never exposed
    or logged, and the PKCS#12 password is only used in memory.
    """
    try:
        data = _read_file(file_field)
        password_bytes = password.encode("utf-8") if password else None
        _, certificate, _ = pkcs12.load_key_and_certificates(data, password_bytes)
        if certificate is None:
            return CertificateInfo(status="unknown", error="No certificate found")

        not_after = getattr(certificate, "not_valid_after_utc", None)
        if not_after is None:
            not_after = certificate.not_valid_after.replace(tzinfo=timezone.utc)

        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        days_left = (not_after - now).days

        if not_after <= now:
            status = "expired"
        elif days_left <= warn_days:
            status = "expiring"
        else:
            status = "valid"

        return CertificateInfo(
            status=status,
            not_after=not_after,
            days_left=days_left,
            subject=certificate.subject.rfc4514_string(),
            issuer=certificate.issuer.rfc4514_string(),
        )
    except Exception as exc:  # wrong password, unreadable file, invalid PKCS#12...
        return CertificateInfo(status="unknown", error=str(exc))
