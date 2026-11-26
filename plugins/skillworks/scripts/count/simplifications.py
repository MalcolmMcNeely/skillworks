# Pure, so each way a Simplify report can write its Findings list is proved on a string and never on a run.

from count.verdicts import lines_under

FINDINGS = "### Findings"


def read_findings(report):
    return lines_under(report, FINDINGS)
