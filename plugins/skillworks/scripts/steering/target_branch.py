# One reader, so no script keeps its own idea of the Target branch.

import json
import sys
from pathlib import Path

from stop import Stop, refusal
from tracker.files import Files
from tracker.github import GitHub

LOOP_FILE = "docs/agents/loop.json"
SPEC_MODE = "spec"

TRACKERS = ("github", "files")


def settings(top):
    path = Path(top) / LOOP_FILE
    if not path.is_file():
        raise refusal("{} is missing. Run seed-steering to write it.".format(LOOP_FILE))
    return json.loads(path.read_text(encoding="utf-8"))


def target_setting(top):
    held = settings(top)
    if "target-branch" not in held:
        raise refusal("{} names no target-branch. Add one, such as \"target-branch\": \"main\".".format(LOOP_FILE))
    return held["target-branch"]


def tracker_setting(top):
    held = settings(top)
    named = ", ".join(TRACKERS)
    if "tracker" not in held:
        raise refusal("{} names no tracker. Add one, such as \"tracker\": \"github\". It can be: {}.".format(
            LOOP_FILE, named))
    if held["tracker"] not in TRACKERS:
        raise refusal("{} names the tracker {}, which the loop does not know. It can be: {}.".format(
            LOOP_FILE, json.dumps(held["tracker"]), named))
    return held["tracker"]


def tracker_for(runner, top, spec=None):
    where = Path(top).as_posix()
    if tracker_setting(top) == "github":
        return GitHub(runner, where)
    named = target_setting(top)
    return Files(runner, where, None if named == SPEC_MODE else named, spec)


def in_spec_mode(top):
    return target_setting(top) == SPEC_MODE


def target_branch(top):
    named = target_setting(top)
    if named == SPEC_MODE:
        raise refusal("{} says spec, so each spec names its own Target branch, and no spec was given to read it from.".format(LOOP_FILE))
    return named


# A script knows the spec's number and not its body, so the Tracker is asked, and only in spec mode.
def target_branch_for(runner, top, spec, tracker=None):
    if spec is None or not in_spec_mode(top):
        return target_branch(top)
    tracker = tracker or tracker_for(runner, top, spec)
    return tracker.branch_of(spec)


READERS = {"target-branch": target_setting, "tracker": tracker_setting}


def main(argv, out, err):
    try:
        read = READERS[argv[1]] if len(argv) > 1 else target_setting
        out.write(read(argv[0]) + "\n")
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    # Windows adds a carriage return, which the preflight would read as part of the branch name.
    sys.stdout.reconfigure(newline="\n")
    sys.stderr.reconfigure(newline="\n")
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))
