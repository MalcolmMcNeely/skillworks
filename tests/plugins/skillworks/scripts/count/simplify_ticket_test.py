# A simplify ticket written from the Findings lines alone, so its template costs a list of lines.

from count.simplify_ticket import simplify_ticket

PARSED = ("`src/orders/intake.py`, `parse_lines`, reuse: it splits each line by hand. Call the CSV "
          "reader.")
TAXED = "`src/orders/totals.py`, efficiency: the tax rate is read for every line. Read it once."


def test_the_title_says_the_ticket_makes_the_simplify_check_s_cleanups():
    title, _ = simplify_ticket([PARSED, TAXED])

    assert title == "TICKET: Make the cleanups the Simplify check found"


def test_the_ticket_quotes_every_finding_under_what_to_build():
    _, body = simplify_ticket([PARSED, TAXED])

    asked = body.split("## Acceptance criteria")[0]
    assert body.startswith("## What to build\n\n")
    assert "\n> " + PARSED + "\n" in asked
    assert "\n> " + TAXED + "\n" in asked


def test_each_finding_is_an_acceptance_criterion_in_its_order():
    _, body = simplify_ticket([PARSED, TAXED])

    assert body.split("## Acceptance criteria\n\n", 1)[1] == "- [ ] {}\n- [ ] {}\n".format(
        PARSED, TAXED)


def test_the_ticket_keeps_every_caller_working():
    _, body = simplify_ticket([PARSED])

    assert "leave every caller working" in body
