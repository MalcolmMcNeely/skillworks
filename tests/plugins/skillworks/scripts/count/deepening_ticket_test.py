# A deepening ticket written from one Strong line alone, so its template costs one line.

from count.deepening_ticket import deepening_ticket

STRONG = ("`The order intake module`: three shallow modules each parse one part of an order. Fold "
          "them into one module whose interface takes the whole order.")


def test_the_title_names_the_module_to_deepen():
    title, _ = deepening_ticket(STRONG)

    assert title == "TICKET: Deepen The order intake module"


def test_the_ticket_quotes_the_strong_line_under_what_to_build():
    _, body = deepening_ticket(STRONG)

    assert body.startswith("## What to build\n\n")
    assert "\n> " + STRONG + "\n" in body.split("## Acceptance criteria")[0]


def test_the_acceptance_criterion_is_the_strong_line():
    _, body = deepening_ticket(STRONG)

    assert body.split("## Acceptance criteria\n\n", 1)[1] == "- [ ] " + STRONG + "\n"


def test_the_ticket_keeps_every_caller_working_and_tests_at_the_interface():
    _, body = deepening_ticket(STRONG)

    assert "leave every caller working" in body
    assert "through its interface" in body
