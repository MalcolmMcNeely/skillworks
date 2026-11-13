# PR mode asks here, and only git names the default branch, so every Tracker refuses the same branches.

import os
import sys

from output.streams import speaking_any_character
from runner import Subprocess
from stop import Stop, misuse, refusal

LOOPS_OWN = "skillworks/"

WHAT_TO_DO = "Make a branch of your own, switch to it, and start again. "

USAGE = "usage: own-branch\n"


def git(runner, where, *args):
    return runner.run(["git", "-C", where] + list(args))


def default_branch(runner, where, nothing):
    named = git(runner, where, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    if named.status == 0 and named.out.strip():
        return named.out.strip().removeprefix("origin/")
    # A clone that never fetched origin/HEAD, such as one made with git remote add, can still ask origin.
    asked = git(runner, where, "ls-remote", "--symref", "origin", "HEAD")
    for line in asked.out.splitlines():
        if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
            return line[len("ref: refs/heads/"):-len("\tHEAD")]
    raise refusal("origin names no default branch, so this checkout cannot be told apart from it. Name it, "
                  "then start again:\n  git remote set-head origin --auto\n" + nothing)


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
