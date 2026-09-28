# A Name report's renames read from its text alone, so each way a line can be written costs one string.

import re
import textwrap

from conftest import PLUGIN
from count.renames import (count_renames, has_no_glossary_word, name_of, read_rename_verdicts,
                           read_renames, unmade_said)
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


def test_a_rename_is_named_by_what_comes_before_its_first_colon_without_its_marks():
    assert name_of("`Batch`: it now holds a whole run.") == "Batch"
    assert name_of("Gap and Hole: two tickets named one concept two ways.") == "Gap and Hole"
    assert name_of("**Stint**: it moved.") == "Stint"


def test_a_rename_with_no_reason_is_named_by_the_whole_line():
    assert name_of("`Batch`") == "Batch"


def test_a_rename_that_says_the_glossary_has_no_word_for_it_is_told_apart():
    assert has_no_glossary_word("Gap and Hole: two names for one thing, and no glossary word.")
    assert has_no_glossary_word("Gap and Hole: No glossary word; the code says Gap most.")
    assert not has_no_glossary_word("`Batch`: the glossary calls that a Job.")


# --- the Name re-check ----------------------------------------------------------

RENAMED = ["`Batch`: it now holds a whole run.", "Gap and Hole: two names for one thing."]


def rename_verdicts(*lines):
    return read_rename_verdicts(report("### Verdicts\n\n" + "".join(
        "- {}\n".format(line) for line in lines)))


def test_each_line_of_the_verdicts_list_is_one_rename_verdict():
    verdicts = rename_verdicts("`Batch`: Done", "Gap and Hole: Not done. Hole is still in two files.")

    assert [(verdict.item, verdict.word, verdict.reason) for verdict in verdicts] == [
        ("Batch", "Done", ""), ("Gap and Hole", "Not done", "Hole is still in two files.")]


def test_a_name_re_check_with_no_verdicts_list_reads_as_none_and_not_as_empty():
    assert read_rename_verdicts(report("Every rename is made.\n")) is None


def test_a_line_with_no_rename_verdict_is_not_one():
    assert rename_verdicts("Batch: Missing. Wrong list.", "A note.") == []


def test_every_rename_done_leaves_nothing_unmade():
    counted = count_renames(RENAMED, rename_verdicts("Batch: Done", "Gap and Hole: Done"))

    assert counted.unmade == []
    assert counted.unknown == []
    assert counted.verdicts_given == 2


def test_a_rename_not_done_is_unmade_with_its_reason():
    counted = count_renames(RENAMED, rename_verdicts("Batch: Done", "Gap and Hole: Not done. Hole."))

    assert [unmade_said(unmade) for unmade in counted.unmade] == ["Gap and Hole is Not done: Hole."]


def test_a_rename_with_no_verdict_is_unmade():
    counted = count_renames(RENAMED, rename_verdicts("Batch: Done"))

    assert [unmade_said(unmade) for unmade in counted.unmade] == ["Gap and Hole has no Verdict"]


def test_a_rename_judged_twice_is_unmade_even_when_both_say_done():
    counted = count_renames(RENAMED, rename_verdicts("Batch: Done", "Batch: Done",
                                                     "Gap and Hole: Done"))

    assert [unmade_said(unmade) for unmade in counted.unmade] == ["Batch has 2 Verdicts: Done, Done"]


def test_a_verdict_for_a_rename_the_ticket_does_not_owe_counts_for_nothing():
    counted = count_renames(RENAMED, rename_verdicts("Batch: Done", "Gap and Hole: Done",
                                                     "Stint: Not done. Typo."))

    assert counted.unmade == []
    assert [verdict.item for verdict in counted.unknown] == ["Stint"]
    assert counted.verdicts_given == 3


# --- what spec-names is told to write ------------------------------------------

def skill_text():
    return SPEC_NAMES.read_text(encoding="utf-8")


def example_report(at=0):
    found = re.findall(r"```markdown\n(.*?)```", skill_text(), re.DOTALL)
    assert len(found) > at, "spec-names shows no example report"
    return textwrap.dedent(found[at])


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


def test_spec_names_marks_a_concept_with_no_glossary_word_in_the_words_the_loop_reads():
    assert "write `no glossary word` on the line" in skill_text()


def test_spec_names_given_a_rename_ticket_judges_only_that_tickets_renames_and_diff():
    text = skill_text()

    assert "## The Name re-check" in text
    assert "/skillworks:spec-names 42 a1b2c3d 57" in text
    assert 'git log -p --reverse --grep "^Ticket: <trailer>$" <base>..origin/<target>' in text
    assert "Do not look for new renames." in text


def test_the_name_re_check_spec_names_shows_reads_as_the_loop_counts_it():
    example = example_report(at=1)

    assert example.startswith(NAME_REPORT + "\n")
    counted = count_renames(["`Batch`: it moved.", "Gap and Hole: two names."],
                            read_rename_verdicts(example))
    assert [unmade_said(unmade) for unmade in counted.unmade] == [
        "Gap and Hole is Not done: Hole is still the name in two files."]
    assert counted.unknown == []
