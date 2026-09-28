# Pure, so each way a Name report can write a rename is proved on a string and never on a run.

from count.verdicts import bullets, subsections_of

RENAMES = "### Renames"


# None when the report holds no Renames list, which is a different fault from an empty one.
def read_renames(report):
    held = subsections_of(report)
    if RENAMES not in held:
        return None
    return [said for said in bullets(held[RENAMES]) if said.rstrip(".") != "None"]
