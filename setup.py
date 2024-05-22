# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

try: # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError: # for pip <= 9.0.3
    from pip.req import parse_requirements

def get_requirements(source):
    try:
        install_reqs = parse_requirements(source, session=False)
    except TypeError:
        # Older version of pip.
        install_reqs = parse_requirements(source)
    try:
        requirements = [str(ir.req) for ir in install_reqs]
    except:
        requirements = [str(ir.requirement) for ir in install_reqs]
    return list(requirements)

with open("README.md") as f:
    readme = f.read()

with open("LICENSE") as f:
    license = f.read()


setup(
    name="django-ticketbai",
    version="1.0",
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
    install_requires=get_requirements('requirements.txt'),
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
