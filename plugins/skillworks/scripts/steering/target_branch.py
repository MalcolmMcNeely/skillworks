# One reader, so no script keeps its own idea of the Target branch.

import json
from pathlib import Path

from stop import refusal

LOOP_FILE = "docs/agents/loop.json"
SPEC_MODE = "spec"
BRANCH_HEADING = "## Branch"


def target_branch(top, spec=None):
    path = Path(top) / LOOP_FILE
    if not path.is_file():
        raise refusal("{} is missing. Run seed-steering to write it.".format(LOOP_FILE))
    settings = json.loads(path.read_text(encoding="utf-8"))
    if "target-branch" not in settings:
        raise refusal("{} names no target-branch. Add one, such as \"target-branch\": \"main\".".format(LOOP_FILE))
    if settings["target-branch"] != SPEC_MODE:
        return settings["target-branch"]
    if spec is None:
        raise refusal("{} says spec, so each spec names its own Target branch, and no spec was given to read it from.".format(LOOP_FILE))
    return spec_branch(spec)


def spec_branch(spec):
    lines = [line.strip() for line in spec.splitlines()]
    if BRANCH_HEADING in lines:
        below = lines[lines.index(BRANCH_HEADING) + 1:]
        named = next((line for line in below if line), "").strip("`")
        if named and not named.startswith("#"):
            return named
    raise refusal("The spec names no branch under {}. Run to-spec, which writes it, or add it by hand.".format(BRANCH_HEADING))
