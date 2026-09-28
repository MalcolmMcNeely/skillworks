# A Name report's renames read from its text alone, so each way a line can be written costs one string.

import re
import textwrap

from conftest import PLUGIN
from count.renames import read_renames
from tracker.reading import NAME_REPORT

SPEC_NAMES = PLUGIN / "skills" / "spec-names" / "SKILL.md"


def report(*sections):
    return NAME_REPORT + "\n\n" + "\n".join(sections)


def test_each_line_of_the_renames_list_is_one_rename():
    renames = read_renames(report("### Renames\n\n- `Batch`: it now holds a whole run.\n"
                                  "- Gap and Hole: two tickets named one concept two ways.\n"))

    assert renames == ["`Batch`: it now holds a whole run.",
                       "Gap and Hole: two tickets named one concept two ways."]


def test_a_rename_that_runs_onto_a_second_line_is_kept_whole():
    renames = read_renames(report("### Renames\n\n- `Batch`: it now holds\n  a whole run.\n"))

    assert renames == ["`Batch`: it now holds a whole run."]


def test_a_renames_list_that_says_none_holds_no_rename():
    assert read_renames(report("### Renames\n\n- None\n")) == []
    assert read_renames(report("### Renames\n\n- None.\n")) == []


def test_a_report_with_no_renames_list_reads_as_none_and_not_as_empty():
    assert read_renames(report("Every name is true.\n")) is None


def test_prose_below_the_list_is_not_a_rename():
    renames = read_renames(report("### Renames\n\n- `Batch`: it moved.\n\n### Notes\n\n- A note.\n"))

    assert renames == ["`Batch`: it moved."]


def test_a_report_read_back_without_its_heading_is_read_the_same():
    assert read_renames("### Renames\n\n- `Batch`: it moved.\n") == ["`Batch`: it moved."]


# --- what spec-names is told to write ------------------------------------------

def skill_text():
    return SPEC_NAMES.read_text(encoding="utf-8")


def example_report():
    found = re.search(r"```markdown\n(.*?)```", skill_text(), re.DOTALL)
    assert found, "spec-names shows no example report"
    return textwrap.dedent(found.group(1))


def test_spec_names_reads_the_diff_and_the_glossary_and_nothing_else():
    text = skill_text()

    assert "git diff <base>..origin/<target>" in text
    assert "`CONTEXT-MAP.md`" in text
    assert "Read nothing else" in text


def test_spec_names_lists_moved_names_and_concepts_named_two_ways():
    text = skill_text()

    assert "whose meaning moved" in text
    assert "two tickets named two ways" in text
    assert 'A rename is never "Optional"' in text


def test_spec_names_records_the_report_with_the_spec_under_the_heading_the_loop_reads():
    text = skill_text()

    assert "`{}`".format(NAME_REPORT) in text
    assert "`### Renames`" in text
    assert "tracker-publish names <spec> <file>" in text
    assert "comment on the spec issue" in text


def test_the_report_spec_names_shows_reads_as_the_loop_reads_it():
    example = example_report()

    assert example.startswith(NAME_REPORT + "\n")
    assert read_renames(example) == [
        "`Batch`: it now names a whole run of tickets, and the glossary calls that a Job.",
        "Gap and Hole: two tickets named one owed item two ways, and the glossary says Gap.",
    ]
