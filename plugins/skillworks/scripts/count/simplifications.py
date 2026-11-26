# Pure, so each way a Simplify report can write its Findings list is proved on a string and never on a run.

from steering.yaml_block import last_yaml_span

from count.verdicts import lines_under

FINDINGS = "### Findings"

ENABLED = "enabled"


def read_findings(report):
    return lines_under(report, FINDINGS)


# None when the block says neither true nor false, so a file the loop cannot read stops it before a Session.
def enabled_in(text):
    lines = text.replace("\r\n", "\n").split("\n")
    span = last_yaml_span(lines)
    if span is None:
        return None
    for line in lines[span[0]:span[1]]:
        key, _, value = line.partition(":")
        if key.strip() == ENABLED and value.strip() in ("true", "false"):
            return value.strip() == "true"
    return None
