# One script, so the grill and to-spec bring the Steering branch along in the same steps every time.

import io
import os
import sys
import tempfile
import time
from pathlib import Path

from export.export_branch import PREFIX, STEERING
from fetch_origin import fetch_origin
from output.streams import speaking_any_character
from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: cut-target-branch\n"


# Neither branch may share a first part with an Export branch, because git cannot hold x and x/... at once.
OWN = "skillworks/"


class Cut:
    def __init__(self, runner, where, wait):
        self.runner = runner
        self.where = where
        self.wait = wait

    def git(self, *args, where=None):
        return self.runner.run(["git", "-C", where or self.where] + [str(a) for a in args])

    def must(self, why, *args, where=None):
        ran = self.git(*args, where=where)
        if ran.status != 0:
            raise refusal("{}. git said:\n{}".format(why, (ran.out + ran.err).rstrip("\n")))
        return ran.out.strip()

    def export_branch(self):
        branch = self.must("git would not name the branch this checkout is on", "branch", "--show-current")
        if not branch:
            raise refusal("this checkout is on no branch. Switch to the branch the Export writes onto, "
                          "then run cut-target-branch again. Nothing was cut.")
        if branch.startswith(OWN):
            raise refusal("this checkout is on {}, and a branch under {} belongs to the loop. Switch to the "
                          "branch the Export writes onto, then run cut-target-branch again. Nothing was "
                          "cut.".format(branch, OWN))
        return branch

    def refuse_a_cut_target(self, target):
        if self.git("rev-parse", "--verify", "--quiet", "refs/heads/" + target).status == 0:
            raise refusal("the Target branch {} is already a branch in this checkout. Switch to it and "
                          "go on there. Nothing was cut.".format(target))
        if self.git("ls-remote", "--exit-code", "--heads", "origin", "refs/heads/" + target).status == 0:
            raise refusal("the Target branch {} is already on origin. Switch to it and go on there. "
                          "Nothing was cut.".format(target))

    def fetched_steering(self):
        said = io.StringIO()
        if not fetch_origin(self.runner, self.where, STEERING, said, self.wait):
            raise refusal("origin/{} could not be fetched, and the Target branch is cut from it. Run "
                          "/skillworks:skillworks-setup to make it. Nothing was cut. git said:\n{}".format(
                              STEERING, said.getvalue().rstrip("\n")))
        return self.must("git would not read origin/" + STEERING, "rev-parse", "refs/remotes/origin/" + STEERING)

    # Rebased in a worktree of its own, so the developer's checkout and the file the grill settled stay as they are.
    def rebased(self, steering, tip):
        with tempfile.TemporaryDirectory() as scratch:
            aside = (Path(scratch) / "steering").as_posix()
            self.must("git would not open a worktree for the Steering branch",
                      "worktree", "add", "--quiet", "--detach", aside, steering)
            try:
                if self.git("rebase", "--quiet", tip, where=aside).status != 0:
                    conflicting = [name for name in self.must(
                        "git would not list the files the rebase stopped on",
                        "diff", "--name-only", "--diff-filter=U", where=aside).split("\n") if name]
                    self.git("rebase", "--abort", where=aside)
                    raise refusal("the Steering branch {} does not rebase onto {}, so nothing was pushed and "
                                  "no Target branch was cut. Mend these files on {} so they apply, push it, "
                                  "and run cut-target-branch again:\n{}".format(
                                      STEERING, tip[:12], STEERING,
                                      "\n".join("  " + name for name in conflicting)))
                return self.must("git would not read the rebased Steering branch", "rev-parse", "HEAD",
                                 where=aside)
            finally:
                self.git("worktree", "remove", "--force", aside)

    def push_steering(self, before, after):
        if after == before:
            return
        self.must("origin would not take the moved Steering branch, so no Target branch was cut",
                  "push", "--quiet", "--force-with-lease=refs/heads/{}:{}".format(STEERING, before),
                  "origin", "{}:refs/heads/{}".format(after, STEERING))
        self.must("git would not move the local " + STEERING, "update-ref", "refs/heads/" + STEERING, after)

    def run(self, out):
        branch = self.export_branch()
        target = PREFIX + branch
        self.refuse_a_cut_target(target)
        tip = self.must("git would not read the tip of " + branch, "rev-parse", "HEAD")
        before = self.fetched_steering()
        after = self.rebased(before, tip)
        self.push_steering(before, after)
        out.write("steering  {} sits on {} of {}, on origin too.\n".format(STEERING, tip[:12], branch))

        self.must("git would not cut " + target, "switch", "--quiet", "-c", target, after)
        self.must("origin would not take " + target, "push", "--quiet", "-u", "origin", target)
        out.write("target    {} is cut from {}, pushed, and checked out.\n".format(target, STEERING))


def main(argv, runner, out, err, wait=time.sleep, where=None):
    where = where or os.getcwd()
    try:
        if argv:
            raise misuse(USAGE)
        Cut(runner, where, wait).run(out)
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, time.sleep, sys.argv[1]))
