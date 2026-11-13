# PR mode asks here and not in each Tracker, so every Tracker refuses the same branches.

import os
import sys

from branches.default_branch import default_branch
from output.streams import speaking_any_character
from runner import Subprocess
from stop import Stop, misuse, refusal

LOOPS_OWN = "skillworks/"

WHAT_TO_DO = "Make a branch of your own, switch to it, and start again. "

USAGE = "usage: own-branch\n"


def git(runner, where, *args):
    return runner.run(["git", "-C", where] + list(args))


def own_branch(runner, where, nothing):
    branch = git(runner, where, "branch", "--show-current").out.strip()
    if not branch:
        raise refusal("this checkout is on no branch. " + WHAT_TO_DO + nothing)
    if branch.startswith(LOOPS_OWN):
        raise refusal("this checkout is on {}, and a branch under {} belongs to the loop. {}{}".format(
            branch, LOOPS_OWN, WHAT_TO_DO, nothing))
    if branch == default_branch(runner, where, nothing):
        raise refusal("this checkout is on {0}, and {0} is the default branch. {1}{2}".format(
            branch, WHAT_TO_DO, nothing))
    return branch


def main(argv, runner, out, err, where=None):
    where = where or os.getcwd()
    try:
        if argv:
            raise misuse(USAGE)
        out.write(own_branch(runner, where, "Nothing was written.") + "\n")
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1]))
