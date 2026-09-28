DRIFT_REPORT = "## Drift report"

NAME_REPORT = "## Name report"

FLAKES = "## Flakes"


def listed(said):
    return [line for line in said.split("\n") if line != ""]
