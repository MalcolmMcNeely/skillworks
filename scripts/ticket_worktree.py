#
# Make and remove the throwaway worktree one job of a spec loop is built in.
#
#   uv run scripts/ticket_worktree.py open  <checkout> <spec> <job>
#   uv run scripts/ticket_worktree.py close <checkout> <spec> <job>
#   uv run scripts/ticket_worktree.py plan  <checkout> <spec> <job>
#   uv run scripts/ticket_worktree.py keep  <checkout> <spec>
#
# A job is one ticket, or the drift check at the end. It gets a worktree and a
# branch of its own, cut from the newest `origin/main`, and both go when it passes.
# The checkout is only ever what they are cut from, so the developer keeps it, on
# any branch, with any edits in it, for the whole run.
#
# A branch here is not the branch this repo says it does without. Git will not check
# `main` out twice, so a worktree needs one, and it never leaves the machine: the
# job pushes to `main` and the branch goes with the worktree.
#
# `open` prints the worktree's path on stdout and nothing else, so the driver can
# read it. Everything else it says goes to stderr.
#
# `plan` prints the path and the branch a job would get, tab separated, and makes neither.
#
# `close` removes the worktree and the branch a job still has, and refuses a job that
# has neither.
#
# Worktrees are grouped by spec, so `keep` takes the whole group a stopped run left
# behind: each job's uncommitted work is committed, its branch is renamed out of the
# way so the job can be opened again, and the worktree goes.
#
# `keep` prints one line per job, tab separated: the job, the branch it is kept on,
# and `held` if the worktree had uncommitted changes or `clean` if it had none.
#
# Every path this prints has forward slashes, because a caller in a shell puts it
# straight back on a command line.

import sys
from pathlib import Path
from typing import NamedTuple

from fetch_origin import fetch_origin
from runner import Subprocess
from stop import Stop, is_a_number, misuse, refusal

USAGE = (
    "usage: uv run scripts/ticket_worktree.py open|close|plan <checkout> <spec> <job>\n"
    "       uv run scripts/ticket_worktree.py keep <checkout> <spec>\n"
)


class Command(NamedTuple):
    names_a_job: bool
    do: object


# One table, read by the check and by the run, so the two cannot drift apart.
COMMANDS = {
    "open": Command(True, lambda worktrees, job: worktrees.open_job(job)),
    "close": Command(True, lambda worktrees, job: worktrees.close_job(job)),
    "plan": Command(True, lambda worktrees, job: worktrees.plan_job(job)),
    "keep": Command(False, lambda worktrees, job: worktrees.keep_group()),
}

# A job names a folder and a branch, so anything else escapes the group or breaks the ref.
JOB_LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"

# Named in full, because the way out it offers is read after a cd somewhere else.
SELF = Path(__file__).resolve().as_posix()


def arguments(argv):
    command = argv[0] if len(argv) > 0 else ""
    checkout = argv[1] if len(argv) > 1 else ""
    spec = argv[2] if len(argv) > 2 else ""
    job = argv[3] if len(argv) > 3 else ""

    if not checkout:
        raise misuse(USAGE)
    if not is_a_number(spec):
        raise misuse(USAGE)
    if command not in COMMANDS:
        raise misuse(USAGE)
    if COMMANDS[command].names_a_job:
        if not job or any(c not in JOB_LETTERS for c in job):
            raise misuse(USAGE)
    elif job:
        raise misuse(USAGE)
    return command, checkout, spec, job


def as_git_path(repo):
    return repo.as_posix() if isinstance(repo, Path) else str(repo)


# Git answers with forward slashes on Windows, so the two are compared as paths and never as text.
def same_place(said, tree):
    try:
        return Path(said).resolve() == tree.resolve()
    except OSError:
        return False


class Worktrees:
    def __init__(self, runner, checkout, spec, out, err):
        self.runner = runner
        self.spec = spec
        self.out = out
        self.err = err

        if self.git(checkout, "rev-parse", "--git-dir").status != 0:
            raise refusal(str(checkout) + " is not a git worktree. Nothing was made or removed.")

        found = self.git(checkout, "rev-parse", "--show-toplevel").out.strip()
        self.checkout = Path(found)
        self.group = self.checkout / ".claude" / "worktrees" / ("spec-" + spec)

    def git(self, repo, *args, echo=False):
        ran = self.runner.run(["git", "-C", as_git_path(repo)] + list(args))
        # A path on stdout is the one thing a caller reads, so everything git says goes to stderr.
        if echo:
            self.err.write(ran.out)
            self.err.write(ran.err)
        return ran

    def tree(self, job):
        return self.group / job

    def branch(self, job):
        return "spec-loop/" + self.spec + "/" + job

    def branch_exists(self, branch):
        asked = self.git(self.checkout, "rev-parse", "--verify", "--quiet", "refs/heads/" + branch)
        return asked.status == 0

    def removal(self, job):
        return "uv run '{}' close '{}' {} {}".format(
            SELF, self.checkout.as_posix(), self.spec, job)

    # The group is the mark a loop is running, so the last job out takes it down.
    def drop_group(self):
        try:
            self.group.rmdir()
        except OSError:
            pass

    def open_job(self, job):
        tree = self.tree(job)
        branch = self.branch(job)

        if tree.exists():
            raise refusal("{} is already there. Remove it with: {}".format(
                tree.as_posix(), self.removal(job)))
        if self.branch_exists(branch):
            raise refusal("branch {} is already there. Remove it with: {}".format(
                branch, self.removal(job)))

        if not fetch_origin(self.runner, self.checkout.as_posix(), self.err):
            raise refusal("could not fetch from origin, so nothing could be cut from it.")
        if self.git(self.checkout, "rev-parse", "--verify", "--quiet", "origin/main").status != 0:
            raise refusal("origin has no main branch to cut a worktree from.")

        self.group.mkdir(parents=True, exist_ok=True)
        added = self.git(
            self.checkout, "worktree", "add", "--quiet", "-b", branch,
            tree.as_posix(), "origin/main", echo=True)
        if added.status != 0:
            raise refusal("git would not make a worktree at " + tree.as_posix() + ".")
        self.out.write(tree.as_posix() + "\n")

    def close_job(self, job):
        tree = self.tree(job)
        branch = self.branch(job)

        # Git forgets a worktree whose folder somebody deleted by hand.
        self.git(self.checkout, "worktree", "prune", echo=True)

        found = False

        # Ignored build output holds the worktree open, and the commit is already on the remote.
        if tree.exists():
            found = True
            removed = self.git(
                self.checkout, "worktree", "remove", "--force", tree.as_posix(), echo=True)
            if removed.status != 0:
                raise refusal("git would not remove the worktree at " + tree.as_posix() + ".")
        if self.branch_exists(branch):
            found = True
            if self.git(self.checkout, "branch", "--quiet", "-D", branch, echo=True).status != 0:
                raise refusal("git would not delete branch " + branch + ".")

        # A success on a name no job had would read exactly like a clean removal.
        if not found:
            raise refusal("{} of spec {} has no worktree and no branch, so nothing was removed.".format(
                job, self.spec))

        self.drop_group()
        self.err.write("ok    " + job + " left nothing behind\n")

    def plan_job(self, job):
        self.out.write(self.tree(job).as_posix() + "\t" + self.branch(job) + "\n")

    # A name no branch holds yet, so a second stopped attempt sits beside the first.
    def kept_name(self, job):
        n = 1
        while True:
            name = self.branch("{}-kept-{}".format(job, n))
            if not self.branch_exists(name):
                return name
            n += 1

    def keep_group(self):
        self.git(self.checkout, "worktree", "prune", echo=True)
        if not self.group.exists():
            return

        for tree in sorted(self.group.iterdir()):
            if not tree.is_dir():
                continue
            job = tree.name

            # A stray folder answers git about the checkout, so the work committed would be theirs.
            top = self.git(tree, "rev-parse", "--show-toplevel").out.strip()
            if not top or not same_place(top, tree):
                self.err.write(
                    "warn  {} is no worktree of its own, so it was left where it is.\n".format(
                        tree.as_posix()))
                continue

            branch = self.git(tree, "rev-parse", "--abbrev-ref", "HEAD").out.strip()
            # Work on no branch would go with the worktree, and nothing here discards work.
            if branch == "HEAD":
                self.err.write("warn  {} is on no branch, so it was left where it is.\n".format(
                    tree.as_posix()))
                continue

            state = "clean"
            if self.git(tree, "status", "--porcelain").out.strip():
                if self.git(tree, "add", "-A", echo=True).status != 0:
                    raise refusal("git would not stage what is in " + tree.as_posix()
                                 + ", so nothing was removed.")

                # A line ending alone stages to nothing, and git refuses to commit that.
                if self.git(tree, "diff", "--cached", "--quiet").status != 0:
                    state = "held"
                    committed = self.git(
                        tree, "commit", "--quiet", "-m",
                        "What a stopped attempt at " + job + " had not committed", echo=True)
                    if committed.status != 0:
                        raise refusal("git would not commit what is in " + tree.as_posix()
                                     + ", so nothing was removed.")

            removed = self.git(
                self.checkout, "worktree", "remove", "--force", tree.as_posix(), echo=True)
            if removed.status != 0:
                raise refusal("git would not remove the worktree at " + tree.as_posix()
                             + ". Branch " + branch + " holds its work.")

            kept = self.kept_name(job)
            renamed = self.git(self.checkout, "branch", "--quiet", "-m", branch, kept, echo=True)
            if renamed.status != 0:
                raise refusal("git would not rename branch " + branch
                             + ", which still holds the work of " + job + ".")

            self.out.write("{}\t{}\t{}\n".format(job, kept, state))

        self.drop_group()


def main(argv, runner, out, err):
    try:
        command, checkout, spec, job = arguments(argv)
        worktrees = Worktrees(runner, checkout, spec, out, err)
        COMMANDS[command].do(worktrees, job)
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    # Windows adds a carriage return, which goes with the path a caller reads off stdout.
    sys.stdout.reconfigure(newline="\n")
    sys.stderr.reconfigure(newline="\n")
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr))
