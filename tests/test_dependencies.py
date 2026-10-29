"""Guard rails for the dependency constraints.

Regression tests for the signing-stack constraints: pytbai 1.8 moves to
signxml 5.2, cryptography 46.0.6+ and lxml 6.1+, and drops pyOpenSSL.
"""

import inspect
from importlib.metadata import PackageNotFoundError, requires, version

import pytest

pytest.importorskip("packaging")

from packaging.requirements import Requirement  # noqa: E402
from packaging.version import Version  # noqa: E402


def _requires(distribution):
    try:
        return [Requirement(r) for r in (requires(distribution) or [])]
    except PackageNotFoundError:
        pytest.skip(f"{distribution} is not installed")


def _requirement(distribution, name):
    return [r for r in _requires(distribution) if r.name.lower() == name]


def test_pytbai_allows_signxml_5_2():
    for req in _requirement("pytbai", "signxml"):
        assert req.specifier.contains(
            Version("5.2.0")
        ), f"signxml 5.2.0 blocked by {req}"


def test_pytbai_allows_cryptography_50():
    for req in _requirement("pytbai", "cryptography"):
        assert req.specifier.contains(
            Version("50.0.2")
        ), f"cryptography 50.0.2 blocked by {req}"


def test_pytbai_does_not_require_pyopenssl():
    assert _requirement("pytbai", "pyopenssl") == []


def test_installed_signxml_satisfies_pytbai():
    installed = Version(version("signxml"))

    for req in _requirement("pytbai", "signxml"):
        assert installed in req.specifier


def test_pytbai_crypto_does_not_use_the_removed_openssl_pkcs12_api():
    """``OpenSSL.crypto.load_pkcs12`` was removed in pyOpenSSL 24."""
    pytest.importorskip("pytbai.utils.crypto")
    import pytbai.utils.crypto as crypto

    source = inspect.getsource(crypto)

    assert "from OpenSSL" not in source
    assert "load_pkcs12" not in source
    assert "pkcs12" in source


def test_django_ticketbai_requires_a_pytbai_with_the_relaxed_caps():
    requirements = _requirement("django-ticketbai", "pytbai")
    if not requirements:
        pytest.skip("django-ticketbai does not declare pytbai")

    installed = Version(version("pytbai"))

    for req in requirements:
        assert installed in req.specifier
    # 1.8.0 moved to signxml 5.2 / cryptography 50 / lxml 6 and dropped
    # pyOpenSSL.
    assert any(req.specifier.contains(Version("1.8.0")) for req in requirements)
