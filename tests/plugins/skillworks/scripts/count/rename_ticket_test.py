# The rename ticket written from the Name report's lines alone, so its template costs one list.

from count.rename_ticket import rename_ticket

RENAMED = ["`Batch`: it now holds a whole run.", "Gap and Hole: two names for one thing."]


def test_the_title_says_the_ticket_makes_the_name_checks_renames():
    title, _ = rename_ticket(RENAMED)

    assert title == "TICKET: Make the renames the Name check found"


def test_the_ticket_holds_one_entry_for_each_rename_line_quoting_it():
    _, body = rename_ticket(RENAMED)

    assert "### Batch\n\n> `Batch`: it now holds a whole run.\n" in body
    assert "### Gap and Hole\n\n> Gap and Hole: two names for one thing.\n" in body
    assert body.count("\n### ") == 2


def test_the_acceptance_criteria_are_the_renames():
    _, body = rename_ticket(RENAMED)

    assert body.split("## Acceptance criteria\n\n", 1)[1] == (
        "- [ ] Batch is renamed everywhere the diff uses it.\n"
        "- [ ] Gap and Hole is renamed everywhere the diff uses it.\n")


def test_the_ticket_takes_the_glossary_word_and_edits_no_glossary():
    _, body = rename_ticket(RENAMED)

    assert "Take the glossary's word for a concept when the glossary has one." in body
    assert "take the name the code and the spec use most" in body
    assert "Edit no glossary." in body
