# The Gap ticket written from the spec's text and the report's text alone, so its template costs two strings.

from count.gap_ticket import NOT_JUDGED_ONCE, gap_ticket
from count.gaps import count_verdicts
from count.items import read_items
from count.verdicts import read_verdicts

SPEC = ("## User Stories\n\n1. As a team member, I want a count.\n2. As a team member, I want a stop.\n\n"
        "## Implementation Decisions\n\n1. The count is pure.\n\n"
        "## Surfaces\n\n- **The user docs** (`docs/usage/`): the count is described.\n")


def written_for(*lines):
    report = "## Drift report\n\n### Verdicts\n\n" + "".join("- {}\n".format(line) for line in lines)
    return gap_ticket(count_verdicts(read_items(SPEC), read_verdicts(report).verdicts).gaps)


def section(body, heading):
    return body.split(heading + "\n", 1)[1].split("\n## ", 1)[0]


def test_the_title_says_the_ticket_builds_the_drift_checks_gaps():
    title, _ = written_for("S1: Missing", "S2: Done", "D1: Done", "The user docs: In step")

    assert title == "TICKET: Build the Gaps the drift check found"


def test_a_gap_quotes_the_items_spec_text_its_verdict_and_the_reason():
    _, body = written_for("S1: Done", "S2: Missing. No code stops.", "D1: Done",
                          "The user docs: In step")

    built = section(body, "## What to build")
    assert "### S2\n\n> As a team member, I want a stop.\n\nVerdict: Missing. No code stops.\n" in built
    assert "S1" not in built


def test_a_gap_with_no_reason_quotes_its_verdict_alone():
    _, body = written_for("S1: Done", "S2: Done", "D1: Partial", "The user docs: In step")

    assert "### D1\n\n> The count is pure.\n\nVerdict: Partial\n" in body


def test_a_surface_out_of_step_is_quoted_by_its_bold_name():
    _, body = written_for("S1: Done", "S2: Done", "D1: Done",
                          "The user docs: Out of step. It lacks the stop.")

    assert ("### The user docs\n\n> **The user docs** (`docs/usage/`): the count is described.\n\n"
            "Verdict: Out of step. It lacks the stop.\n") in body


def test_an_item_with_no_verdict_asks_for_a_check_before_a_build():
    _, body = written_for("S1: Done", "D1: Done", "The user docs: In step")

    assert "### S2\n\n> As a team member, I want a stop.\n\n{}\n".format(NOT_JUDGED_ONCE) in body
    assert NOT_JUDGED_ONCE == ("The drift check did not judge this exactly once. Check it, and "
                               "build it if it is not there.")


def test_an_item_judged_twice_asks_for_a_check_before_a_build():
    _, body = written_for("S1: Done", "S1: Missing. Not there.", "S2: Done", "D1: Done",
                          "The user docs: In step")

    assert "### S1\n\n> As a team member, I want a count.\n\n{}\n".format(NOT_JUDGED_ONCE) in body


def test_the_acceptance_criteria_are_the_gap_items_in_the_specs_order():
    _, body = written_for("The user docs: Out of step. Short.", "D1: Missing", "S2: Done")

    assert section(body, "## Acceptance criteria").strip("\n").split("\n") == [
        "- [ ] S1: As a team member, I want a count.",
        "- [ ] D1: The count is pure.",
        "- [ ] The user docs: **The user docs** (`docs/usage/`): the count is described.",
    ]
