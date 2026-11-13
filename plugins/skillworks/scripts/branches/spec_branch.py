# PR mode makes each spec's branch here, so the developer's checkout never leaves the default branch.

import os
import sys

from branches.default_branch import default_branch
from output.streams import speaking_any_character
from runner import Subprocess
from sidecar.locator import main_checkout_of
from steering.target_branch import tracker_for
from stop import Stop, misuse, refusal

USAGE = "usage: spec-branch <name>\n"

NOTHING = "Nothing was pushed."

# Never under .claude/, because Claude Code asks before every write there and no allow rule lifts it.
GRILL = ".spec-loop/grill"


def git(runner, where, *args):
    return runner.run(["git", "-C", where] + list(args))


def refused(said):
    return refusal(said + " " + NOTHING)


def free_name(runner, top, name, default):
    if git(runner, top, "check-ref-format", "--branch", name).status != 0:
        raise refused("{} is not a name git takes for a branch.".format(name))
    if name == default:
        raise refused("{0} is the default branch, and a spec needs a branch of its own. Name another.".format(name))
    asked = git(runner, top, "ls-remote", "--heads", "origin", "refs/heads/" + name)
    if asked.status != 0:
        raise refused("origin did not answer: {}".format((asked.err or asked.out).strip()))
    if asked.out.strip():
        raise refused("{} is already on origin. Name another.".format(name))
    tracker = tracker_for(runner, top)
    problem = tracker.connect()
    if problem:
        raise refused(problem[0].upper() + problem[1:] + ".")
    held = tracker.open_spec_branches()
    if name in held:
        raise refused("Open spec {} already names {}. Name another.".format(held[name], name))
    if git(runner, top, "rev-parse", "--verify", "--quiet", "refs/heads/" + name).status == 0:
        raise refused("{} is already a branch in this clone. Name another.".format(name))


def spec_branch(runner, where, name):
    main = main_checkout_of(runner, where)
    top = main.as_posix()
    default = default_branch(runner, top, NOTHING)
    free_name(runner, top, name, default)
    grill = main / GRILL / name
    if grill.exists():
        raise refused("{} is already there. Remove it, or name another branch.".format(grill.as_posix()))
    tip = "refs/remotes/origin/" + default
    for args in (["fetch", "--quiet", "origin", "+refs/heads/{}:{}".format(default, tip)],
                 ["push", "--quiet", "origin", "{}:refs/heads/{}".format(tip, name)]):
        done = git(runner, top, *args)
        if done.status != 0:
            raise refused("git {} failed: {}".format(args[0], (done.err or done.out).strip()))
    for args in (["fetch", "--quiet", "origin", "+refs/heads/{0}:refs/remotes/origin/{0}".format(name)],
                 ["worktree", "add", "--quiet", "--track", "-b", name, grill.as_posix(), "origin/" + name]):
        done = git(runner, top, *args)
        if done.status != 0:
            raise refusal("{} is on origin, and git {} failed: {}".format(
                name, args[0], (done.err or done.out).strip()))
    return grill.as_posix()


def main(argv, runner, out, err, where=None):
    where = where or os.getcwd()
    try:
        if len(argv) != 1:
            raise misuse(USAGE)
        out.write(spec_branch(runner, where, argv[0]) + "\n")
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1]))
