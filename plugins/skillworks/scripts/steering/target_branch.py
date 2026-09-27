# One reader, so no script keeps its own idea of the Target branch.

import json
import sys
from pathlib import Path

from stop import Stop, refusal

LOOP_FILE = "docs/agents/loop.json"
SPEC_MODE = "spec"
BRANCH_HEADING = "## Branch"


def target_setting(top):
    path = Path(top) / LOOP_FILE
    if not path.is_file():
        raise refusal("{} is missing. Run seed-steering to write it.".format(LOOP_FILE))
    settings = json.loads(path.read_text(encoding="utf-8"))
    if "target-branch" not in settings:
        raise refusal("{} names no target-branch. Add one, such as \"target-branch\": \"main\".".format(LOOP_FILE))
    return settings["target-branch"]


def in_spec_mode(top):
    return target_setting(top) == SPEC_MODE


def target_branch(top, spec=None):
    named = target_setting(top)
    if named != SPEC_MODE:
        return named
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


def main(argv, out, err):
    try:
        out.write(target_setting(argv[0]) + "\n")
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    # Windows adds a carriage return, which the preflight would read as part of the branch name.
    sys.stdout.reconfigure(newline="\n")
    sys.stderr.reconfigure(newline="\n")
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))
