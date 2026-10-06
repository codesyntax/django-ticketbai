"""The README documents the ``TICKETBAI_CONF`` setting (issue #5).

These tests keep the documented example in sync with what the package (and
``pytbai``) actually accepts.
"""

import json
import pathlib
import re

from pytbai import TBai

README = pathlib.Path(__file__).resolve().parent.parent / "README.md"


def readme_config():
    blocks = re.findall(
        r"```json\n(.*?)```", README.read_text(encoding="utf-8"), re.DOTALL
    )
    assert blocks, "README.md does not contain a json example of TICKETBAI_CONF"
    return json.loads(blocks[0])


def test_readme_example_config_is_accepted_by_pytbai():
    config = readme_config()

    assert set(config) == {"subject", "software"}

    tbai = TBai(config)

    assert tbai.subject.entity_id == config["subject"]["entity_id"]
    assert tbai.subject.name == config["subject"]["name"]
    assert tbai.subject.address == config["subject"]["address"]
    assert tbai.software.license == config["software"]["license"]
    assert tbai.software.dev_entity == config["software"]["dev_entity"]
    assert tbai.software.soft_name == config["software"]["soft_name"]
    assert tbai.software.soft_version == config["software"]["soft_version"]


def test_readme_example_documents_the_required_keys():
    config = readme_config()

    assert {"entity_id", "name"} <= set(config["subject"])
    assert set(config["software"]) == {
        "license",
        "dev_entity",
        "soft_name",
        "soft_version",
    }


def test_readme_does_not_tell_users_to_set_env():
    """``env`` is set by the package from ``settings.DEBUG``."""
    config = readme_config()

    assert "env" not in config["subject"]
