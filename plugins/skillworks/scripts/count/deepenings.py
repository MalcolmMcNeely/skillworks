# Pure, so each way a Deepening report can write its Strong list is proved on a string and never on a run.

from steering.yaml_block import last_yaml_span

from count.verdicts import bullets, subsections_of

STRONG = "### Strong"

LIMIT = "limit"


# None when the report holds no Strong list, which is a different fault from an empty one.
def read_strong(report):
    held = subsections_of(report)
    if STRONG not in held:
        return None
    return [said for said in bullets(held[STRONG]) if said.rstrip(".") != "None"]


# The judge ranks strongest first, so the script keeps the head and the count never trusts the judge.
def filed_within(strong, limit):
    return strong[:limit], strong[limit:]


# None when the block names no whole number, so a file the loop cannot read stops it before a Session.
def limit_in(text):
    lines = text.replace("\r\n", "\n").split("\n")
    span = last_yaml_span(lines)
    if span is None:
        return None
    for line in lines[span[0]:span[1]]:
        key, _, value = line.partition(":")
        if key.strip() == LIMIT and value.strip().isdigit():
            return int(value.strip())
    return None
