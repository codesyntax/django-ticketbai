# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open("README.md") as f:
    readme = f.read()

with open("LICENSE") as f:
    license = f.read()


setup(
    name="django-ticketbai",
    version="2.2",
    description=(
        "django-ticketbai allows to create, manage, store and send TicketBai"
        " invoices to the Basque tax authorities."
    ),
    long_description=readme,
    long_description_content_type="text/markdown",
    keywords="",
    author="Urtzi Odriozola",
    author_email="uodriozola@codesyntax.com",
    url="https://github.com/codesyntax/django-ticketbai",
    license=license,
    packages=find_packages(exclude=("tests", "docs")),
    python_requires=">=3.11",
    install_requires=[
        "pytbai>=1.7.0",
        "qrcode",
        "weasyprint==63.1",
        "crc8==0.2.1",
    ],
    include_package_data = True,
    package_data={
        "django_ticketbai": ["templates/*"],
    },
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
