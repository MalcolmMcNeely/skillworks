# A report's Verdicts read from its text alone, so each way a line can be written costs one string.

import re
import textwrap

from conftest import PLUGIN
from count.verdicts import read_verdicts

SPEC_DRIFT = PLUGIN / "skills" / "spec-drift" / "SKILL.md"


def report(*sections):
    return "## Drift report\n\n" + "\n".join(sections) + "\nThe prose follows.\n"


def judged(read):
    return [(verdict.item, verdict.word, verdict.reason) for verdict in read.verdicts]


def test_each_line_of_the_verdicts_list_is_one_verdict():
    read = read_verdicts(report("### Verdicts\n\n- S1: Done\n- D1: Missing. No code reads it.\n"))

    assert judged(read) == [("S1", "Done", ""), ("D1", "Missing", "No code reads it.")]


def test_a_surface_is_judged_by_its_name_and_its_two_word_verdicts():
    read = read_verdicts(report("### Verdicts\n\n- The user docs: Out of step. It lacks the stop.\n"
                                "- The README: In step\n"))

    assert judged(read) == [("The user docs", "Out of step", "It lacks the stop."),
                            ("The README", "In step", "")]


def test_a_reason_after_a_dash_or_a_colon_is_read_the_same():
    read = read_verdicts(report("### Verdicts\n\n- S1: Partial — the log is short.\n"
                                "- S2: Contradicts: it closes the spec.\n"))

    assert judged(read) == [("S1", "Partial", "the log is short."),
                            ("S2", "Contradicts", "it closes the spec.")]


def test_a_reason_that_runs_onto_a_second_line_is_kept_whole():
    read = read_verdicts(report("### Verdicts\n\n- S1: Partial. The log\n  is short.\n"))

    assert judged(read) == [("S1", "Partial", "The log is short.")]


def test_an_item_written_in_bold_or_as_code_is_read_by_its_name():
    read = read_verdicts(report("### Verdicts\n\n- **S1**: Done\n- `D1`: Done\n"))

    assert [verdict.item for verdict in read.verdicts] == ["S1", "D1"]


def test_a_surface_whose_name_holds_a_colon_is_read_up_to_its_verdict():
    read = read_verdicts(report("### Verdicts\n\n- Docs: the loop: In step\n"))

    assert judged(read) == [("Docs: the loop", "In step", "")]


def test_a_line_that_names_no_verdict_is_not_a_verdict():
    read = read_verdicts(report("### Verdicts\n\n- S1: Great work\n- S2: Done\n"))

    assert [verdict.item for verdict in read.verdicts] == ["S2"]


def test_the_list_ends_at_the_next_heading():
    read = read_verdicts(report("### Verdicts\n\n- S1: Done\n", "### Surfaces\n\n- S2: Done\n"))

    assert [verdict.item for verdict in read.verdicts] == ["S1"]


def test_a_report_with_no_verdicts_list_has_none_to_read():
    read = read_verdicts(report("Everything is done.\n"))

    assert read.verdicts is None


def test_an_empty_verdicts_list_is_a_list_with_nothing_in_it():
    read = read_verdicts(report("### Verdicts\n\nNothing to judge.\n"))

    assert read.verdicts == []


def test_each_unrequested_item_is_read_on_its_own():
    read = read_verdicts(report("### Verdicts\n\n- S1: Done\n",
                                "### Unrequested\n\n- A helper that trims logs.\n- A retry.\n"))

    assert read.unrequested == ["A helper that trims logs.", "A retry."]


def test_an_unrequested_list_that_says_none_holds_nothing():
    read = read_verdicts(report("### Verdicts\n\n- S1: Done\n", "### Unrequested\n\n- None\n"))

    assert read.unrequested == []


def test_a_report_with_no_unrequested_list_has_nothing_unrequested():
    read = read_verdicts(report("### Verdicts\n\n- S1: Done\n"))

    assert read.unrequested == []


def test_a_report_read_back_without_its_heading_is_read_the_same():
    read = read_verdicts("### Verdicts\n\n- S1: Done\n")

    assert judged(read) == [("S1", "Done", "")]


# --- what spec-drift is told to write ------------------------------------------

def skill_text():
    return SPEC_DRIFT.read_text(encoding="utf-8")


def example_report():
    found = re.search(r"```markdown\n(.*?)```", skill_text(), re.DOTALL)
    assert found, "spec-drift shows no example report"
    return textwrap.dedent(found.group(1))


def test_spec_drift_names_the_verdicts_list_and_the_unrequested_list():
    text = skill_text()

    assert "`### Verdicts`" in text
    assert "`### Unrequested`" in text
    assert "`- <item>: <Verdict>`" in text
    for word in ("Done", "Partial", "Missing", "Contradicts", "In step", "Out of step"):
        assert "**{}**".format(word) in text


def test_spec_drift_says_every_verdict_but_done_and_in_step_carries_a_reason():
    assert "every Verdict other than Done or In step" in skill_text()


def test_the_report_spec_drift_shows_reads_as_the_loop_reads_it():
    read = read_verdicts(example_report())

    assert judged(read) == [
        ("S1", "Done", ""),
        ("S2", "Partial", "The stop line names the Contradicts but not the Gaps beside it."),
        ("D1", "Missing", "No code reads the report's Verdicts."),
        ("D2", "Contradicts", "The driver closes the spec when a Gap is left."),
        ("The user docs", "Out of step", "`the-loop.md` does not say what a Gap is."),
    ]
    assert read.unrequested == ["A helper that trims the log's lines to 80 characters."]
