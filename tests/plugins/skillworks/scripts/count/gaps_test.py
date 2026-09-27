# The count read from the spec's text and the report's text alone, so each kind of Gap costs two strings.

from count.gaps import count_verdicts, gap_said
from count.items import read_items
from count.verdicts import read_verdicts

SPEC = ("## User Stories\n\n1. As a team member, I want a count.\n2. As a team member, I want a stop.\n\n"
        "## Implementation Decisions\n\n1. The count is pure.\n\n"
        "## Surfaces\n\n- **The user docs** (`docs/usage/`): the count is described.\n")

ALL_DONE = {"S1": "Done", "S2": "Done", "D1": "Done", "The user docs": "In step"}


def counted(*lines):
    report = "## Drift report\n\n### Verdicts\n\n" + "".join("- {}\n".format(line) for line in lines)
    return count_verdicts(read_items(SPEC), read_verdicts(report).verdicts)


def lines_but(**given):
    judged = dict(ALL_DONE, **{name.replace("_", " "): said for name, said in given.items()})
    return ["{}: {}".format(name, said) for name, said in judged.items() if said is not None]


def gaps(count):
    return [gap_said(gap) for gap in count.gaps]


def test_every_verdict_done_or_in_step_leaves_no_gap():
    count = counted(*lines_but())

    assert count.gaps == []
    assert count.contradicts == []
    assert count.unknown == []


def test_a_missing_item_is_a_gap_with_its_reason():
    count = counted(*lines_but(S2="Missing. No code stops."))

    assert gaps(count) == ["S2 is Missing: No code stops."]


def test_a_partial_item_is_a_gap():
    count = counted(*lines_but(D1="Partial. Half of it."))

    assert gaps(count) == ["D1 is Partial: Half of it."]


def test_a_surface_out_of_step_is_a_gap():
    count = counted(*lines_but(The_user_docs="Out of step. It lacks the stop."))

    assert gaps(count) == ["The user docs is Out of step: It lacks the stop."]


def test_a_gap_with_no_reason_is_named_all_the_same():
    count = counted(*lines_but(S1="Missing"))

    assert gaps(count) == ["S1 is Missing"]


def test_an_item_with_no_verdict_is_a_gap():
    count = counted(*lines_but(S2=None))

    assert gaps(count) == ["S2 has no Verdict"]


def test_an_item_judged_twice_is_a_gap_that_names_both_verdicts():
    count = counted(*lines_but(), "S1: Missing. It is not there.")

    assert gaps(count) == ["S1 has 2 Verdicts: Done, Missing"]


def test_the_gaps_come_in_the_order_the_spec_holds_its_items():
    count = counted(*reversed(lines_but(S1="Missing", D1="Partial", The_user_docs=None)))

    assert [gap.item.name for gap in count.gaps] == ["S1", "D1", "The user docs"]


def test_a_gap_keeps_the_items_spec_text():
    count = counted(*lines_but(S2="Missing"))

    assert count.gaps[0].item.text == "As a team member, I want a stop."


def test_a_verdict_naming_no_item_of_the_spec_is_set_aside_and_counts_nothing():
    count = counted(*lines_but(), "S9: Missing. Nothing.")

    assert count.gaps == []
    assert [verdict.item for verdict in count.unknown] == ["S9"]


def test_a_contradicts_is_held_apart_from_the_gaps():
    count = counted(*lines_but(D1="Contradicts. It closes the spec.", S2="Missing"))

    assert [(verdict.item, verdict.reason) for verdict in count.contradicts] == [
        ("D1", "It closes the spec.")]
    assert gaps(count) == ["S2 is Missing"]


def test_a_count_says_how_many_verdicts_it_read():
    count = counted(*lines_but(), "S1: Done", "S9: Done")

    assert count.verdicts_given == 6
