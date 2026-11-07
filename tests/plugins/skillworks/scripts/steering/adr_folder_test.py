import pytest

from conftest import ROOT
from steering.adr_folder import DOMAIN_FILE, adr_folder
from stop import REFUSED, Stop

PROSE = "# Domain Docs\n\nRead the ADRs in the folder `adr-folder` names.\n\n"


def given_domain(top, text):
    path = top / DOMAIN_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def refused(top):
    with pytest.raises(Stop) as stopped:
        adr_folder(top)
    assert stopped.value.status == REFUSED
    return stopped.value.said


def test_the_folder_the_setting_names_is_read(tmp_path):
    given_domain(tmp_path, PROSE + "```yaml\nadr-folder: docs/architecture-decision-log\n```\n")

    assert adr_folder(tmp_path) == "docs/architecture-decision-log"


def test_a_quoted_folder_is_read_without_its_quotes(tmp_path):
    given_domain(tmp_path, PROSE + "```yaml\nadr-folder: \"decisions\"\n```\n")

    assert adr_folder(tmp_path) == "decisions"


def test_the_block_at_the_end_is_read_and_an_example_above_it_is_not(tmp_path):
    given_domain(tmp_path, PROSE + "```yaml\nadr-folder: example/adr\n```\n\nMore prose.\n\n"
                 "```yaml\nadr-folder: docs/adr\n```\n")

    assert adr_folder(tmp_path) == "docs/adr"


def test_a_missing_domain_docs_file_refuses_and_names_setup(tmp_path):
    said = refused(tmp_path)

    assert DOMAIN_FILE in said
    assert "/skillworks:skillworks-setup" in said


def test_domain_docs_with_no_block_refuse_and_name_setup(tmp_path):
    given_domain(tmp_path, PROSE)

    said = refused(tmp_path)

    assert "adr-folder" in said
    assert "/skillworks:skillworks-setup" in said


def test_a_block_with_no_adr_folder_refuses_and_names_setup(tmp_path):
    given_domain(tmp_path, PROSE + "```yaml\nother: value\n```\n")

    said = refused(tmp_path)

    assert "names no adr-folder" in said
    assert "/skillworks:skillworks-setup" in said


@pytest.mark.parametrize("value", ["", "  ", '""', "''"])
def test_an_empty_adr_folder_refuses_and_names_setup(tmp_path, value):
    given_domain(tmp_path, PROSE + "```yaml\nadr-folder:" + value + "\n```\n")

    said = refused(tmp_path)

    assert "names an empty adr-folder" in said
    assert "/skillworks:skillworks-setup" in said


def test_this_repo_keeps_its_adrs_in_docs_adr():
    assert adr_folder(ROOT) == "docs/adr"
