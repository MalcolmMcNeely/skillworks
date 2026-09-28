# A fixed template and no model, so the ticket that builds the Gaps says only what the count found.

TITLE = "TICKET: Build the Gaps the drift check found"

NOT_JUDGED_ONCE = ("The drift check did not judge this exactly once. Check it, and build it if it "
                   "is not there.")


def owed(gap):
    if len(gap.judged) != 1:
        return NOT_JUDGED_ONCE
    verdict = gap.judged[0]
    return "Verdict: " + verdict.word + (". " + verdict.reason if verdict.reason else "")


def gap_ticket(gaps):
    body = ("## What to build\n\nThe drift check judged each item below against the spec, and the "
            "spec is owed it. Build each one.\n")
    for gap in gaps:
        body += "\n### {}\n\n> {}\n\n{}\n".format(gap.item.name, gap.item.text, owed(gap))
    body += "\n## Acceptance criteria\n\n"
    body += "".join("- [ ] {}: {}\n".format(gap.item.name, gap.item.text) for gap in gaps)
    return TITLE, body
