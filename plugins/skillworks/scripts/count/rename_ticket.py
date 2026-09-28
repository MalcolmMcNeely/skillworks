# A fixed template and no model, so the ticket that makes the renames says only what the Name check found.

from count.renames import name_of

TITLE = "TICKET: Make the renames the Name check found"


def rename_ticket(renames):
    body = ("## What to build\n\nThe Name check read the spec's diff against the glossary, and each "
            "name below says something the code no longer means. Make each rename everywhere the "
            "diff uses the name.\n\nTake the glossary's word for a concept when the glossary has "
            "one. When it has none, take the name the code and the spec use most. Edit no "
            "glossary. A new word is settled by a person.\n")
    for said in renames:
        body += "\n### {}\n\n> {}\n".format(name_of(said), said)
    body += "\n## Acceptance criteria\n\n"
    body += "".join("- [ ] {} is renamed everywhere the diff uses it.\n".format(name_of(said))
                    for said in renames)
    return TITLE, body
