# A fixed template and no model, so a deepening ticket says only what the Deepening check found.

from count.renames import name_of

TITLE = "TICKET: Deepen "


def deepening_ticket(strong):
    body = ("## What to build\n\nThe Deepening check read the spec's commits and found the module "
            "below shallow. Make the deepening the line names, and leave every caller working. "
            "Test the deepened module through its interface.\n\n> {}\n\n"
            "## Acceptance criteria\n\n- [ ] {}\n".format(strong, strong))
    return TITLE + name_of(strong), body
