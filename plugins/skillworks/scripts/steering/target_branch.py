# One reader, so no script keeps its own idea of the Target branch.

import json
from pathlib import Path

from steering.steering_file import LOOP_FILE, steering_root
from stop import refusal
from tracker.files import Files
from tracker.github import GitHub

PR_MODE = "pr"
# Read as a branch name, an old "spec" would land every ticket on a branch called spec.
OLD_SPEC_VALUE = "spec"

TRACKERS = ("github", "files")


def settings(top):
    path = steering_root(top) / LOOP_FILE
    if not path.is_file():
        raise refusal("{} is missing. Run seed-steering to write it.".format(LOOP_FILE))
    return json.loads(path.read_text(encoding="utf-8"))


def target_setting(top):
    held = settings(top)
    if "target-branch" not in held:
        raise refusal("{} names no target-branch. Add one, such as \"target-branch\": \"main\".".format(LOOP_FILE))
    if held["target-branch"] == OLD_SPEC_VALUE:
        raise refusal("{} says \"target-branch\": \"spec\", and spec mode is now PR mode. To go on, "
                      "write \"target-branch\": \"pr\" in {}.".format(LOOP_FILE, LOOP_FILE))
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


def tracker_for(runner, top, spec=None, clock=None):
    where = Path(top).as_posix()
    named = target_setting(top)
    target = None if named == PR_MODE else named
    if tracker_setting(top) == "github":
        return GitHub(runner, where, target=target)
    return Files(runner, where, target, spec, clock)


def in_pr_mode(top):
    return target_setting(top) == PR_MODE


def target_branch(top):
    named = target_setting(top)
    if named == PR_MODE:
        raise refusal("{} says pr, so each spec names its own Target branch, and no spec was given to read it from.".format(LOOP_FILE))
    return named


# A script knows the spec's number and not its body, so the Tracker is asked, and only in PR mode.
def target_branch_for(runner, top, spec, tracker=None):
    if spec is None or not in_pr_mode(top):
        return target_branch(top)
    tracker = tracker or tracker_for(runner, top, spec)
    return tracker.branch_of(spec)
