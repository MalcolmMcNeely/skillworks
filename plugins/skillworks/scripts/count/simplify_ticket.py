# A fixed template and no model, so the simplify ticket says only what the Simplify check found.

TITLE = "TICKET: Make the cleanups the Simplify check found"


def simplify_ticket(findings):
    body = ("## What to build\n\nThe Simplify check read the spec's commits, and each line below names "
            "code harder than it has to be, and the simpler form. Make each cleanup, and leave every "
            "caller working.\n\n")
    body += "".join("> {}\n>\n".format(said) for said in findings[:-1])
    body += "> {}\n".format(findings[-1])
    body += "\n## Acceptance criteria\n\n"
    body += "".join("- [ ] {}\n".format(said) for said in findings)
    return TITLE, body
