# A commit is the spec's only by its Ticket: trailer, so a hand commit with none is never read.

import io
import os
import sys
import time

from fetch_origin import fetch_origin
from runner import Subprocess
from stop import Stop, is_a_number, misuse, refusal
from tracker.publish import opened

USAGE = "usage: spec-commits <spec> <base-commit>\n"

# Characters no commit hash or trailer holds, so the log splits cleanly.
FIELD = "\x1f"
RECORD = "\x1e"


def branch_read(tracker, spec):
    return tracker.target or tracker.branch_of(spec)


def fetched(tracker, branch, wait):
    said = io.StringIO()
    if not fetch_origin(tracker.runner, tracker.where, branch, said, wait):
        raise refusal("origin/{} could not be fetched, so there is nothing to read. git "
                      "said:\n{}".format(branch, said.getvalue().rstrip("\n")))


def git(tracker, *args):
    return tracker.runner.run(["git", "-C", tracker.where] + list(args))


def checked_base(tracker, base):
    found = git(tracker, "rev-parse", "--verify", "--quiet", base + "^{commit}")
    if found.status != 0:
        raise refusal("{} is not a commit in this repo.".format(base))
    return found.out.strip()


def after(tracker, base, branch):
    said = git(tracker, "log", "--reverse",
               "--format=%H" + FIELD + "%(trailers:key=Ticket,valueonly,separator=%x1f)" + RECORD,
               "{}..origin/{}".format(base, branch))
    if said.status != 0:
        raise refusal("git would not list the commits after {} on origin/{}. git said:\n{}".format(
            base, branch, (said.out + said.err).rstrip("\n")))
    commits = []
    for record in said.out.split(RECORD):
        fields = record.strip("\n").split(FIELD)
        if fields[0]:
            commits.append((fields[0], {value.strip() for value in fields[1:] if value.strip()}))
    return commits


# Kept apart from main so the driver can count what a check reads and what it leaves out.
def spec_commits(tracker, spec, base, wait, branch=None):
    branch = branch or branch_read(tracker, spec)
    fetched(tracker, branch, wait)
    base = checked_base(tracker, base)
    named = {tracker.trailer(ticket) for ticket in tracker.tickets(spec)}
    kept, left = [], []
    for commit, trailers in after(tracker, base, branch):
        (kept if trailers & named else left).append(commit)
    return kept, left


def shown(tracker, commit):
    said = git(tracker, "show", "--no-color", "--no-ext-diff", "--format=medium", "--patch", commit)
    if said.status != 0:
        raise refusal("git would not show {}. git said:\n{}".format(
            commit, (said.out + said.err).rstrip("\n")))
    return said.out


def main(argv, runner, out, err, wait, where=None):
    where = where or os.getcwd()
    try:
        if len(argv) != 2 or not is_a_number(argv[0]) or not argv[1]:
            raise misuse(USAGE)
        spec = str(int(argv[0]))
        tracker = opened(runner, where, spec, wait)
        kept, _ = spec_commits(tracker, spec, argv[1], wait)
        out.write("\n".join(shown(tracker, commit).rstrip("\n") + "\n" for commit in kept))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    # Windows adds a carriage return, which a check reads as part of the patch.
    sys.stdout.reconfigure(newline="\n", encoding="utf-8")
    sys.stderr.reconfigure(newline="\n")
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, time.sleep, sys.argv[1]))
