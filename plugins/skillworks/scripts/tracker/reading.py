DRIFT_REPORT = "## Drift report"

NAME_REPORT = "## Name report"

DEEPENING_REPORT = "## Deepening report"

SIMPLIFY_REPORT = "## Simplify report"

FLAKES = "## Flakes"


def listed(said):
    return [line for line in said.split("\n") if line != ""]
