# A commit is the spec's only by its trailer, or by the Landed list under Sidecar Steering, so a hand commit is never read.

import io
import os
import sys
import time

from fetch_origin import fetch_origin
from output.streams import speaking_any_character
from runner import Subprocess
from sidecar.landed import Landed
from steering.steering_file import sidecar_steering
from stop import Stop, is_a_number, misuse, refusal
from tracker.publish import opened

USAGE = ("usage: spec-commits <spec> <base-commit> [<ticket>]\n"
         "       spec-commits --ticket-of <commit>\n")

TICKET_OF = "--ticket-of"

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


# Under Sidecar Steering the list names each commit's ticket, so a trailer typed by hand counts for nothing.
def with_tickets(tracker, branch, commits):
    if not sidecar_steering(tracker.where):
        return commits
    listed = Landed(tracker.runner, tracker.where).on(branch, tracker.where)
    return [(commit, {listed[commit]} if commit in listed else set()) for commit, _ in commits]


def commits_and_tickets(tracker, spec, base, wait, branch=None):
    branch = branch or branch_read(tracker, spec)
    fetched(tracker, branch, wait)
    base = checked_base(tracker, base)
    named = {tracker.commit_ticket(ticket) for ticket in tracker.tickets(spec)}
    return with_tickets(tracker, branch, after(tracker, base, branch)), named


# Kept apart from main so the driver can count what a check reads and what it leaves out.
def spec_commits(tracker, spec, base, wait, branch=None):
    commits, named = commits_and_tickets(tracker, spec, base, wait, branch)
    kept, left = [], []
    for commit, tickets in commits:
        (kept if tickets & named else left).append(commit)
    return kept, left


def shown(tracker, commit):
    said = git(tracker, "show", "--no-color", "--no-ext-diff", "--format=medium", "--patch", commit)
    if said.status != 0:
        raise refusal("git would not show {}. git said:\n{}".format(
            commit, (said.out + said.err).rstrip("\n")))
    return said.out


# The loop names a ticket as its Tracker does, `57` or `#57` with GitHub and `42/3` with files.
def ticket_named(spec, said):
    owner, _, number = said.lstrip("#").rpartition("/")
    if not is_a_number(number) or (owner and (not is_a_number(owner) or str(int(owner)) != spec)):
        raise misuse(USAGE)
    return str(int(number))


def well_formed(argv):
    return len(argv) in (2, 3) and is_a_number(argv[0]) and bool(argv[1])


# Under Sidecar Steering the commit holds no trailer, so the ticket the list names is printed above it.
def printed(tracker, commit, tickets):
    named = "".join("Ticket: {}\n".format(ticket) for ticket in sorted(tickets)) \
        if sidecar_steering(tracker.where) else ""
    return named + shown(tracker, commit).rstrip("\n") + "\n"


# A hand review has a commit and no spec, so the ticket is found from the commit alone.
def ticket_of(runner, where, commit, wait):
    found = runner.run(["git", "-C", where, "rev-parse", "--verify", "--quiet", commit + "^{commit}"])
    if found.status != 0:
        raise refusal("{} is not a commit in this repo.".format(commit))
    commit = found.out.strip()
    if not sidecar_steering(where):
        said = runner.run(["git", "-C", where, "log", "-1", commit,
                           "--format=%(trailers:key=Ticket,valueonly)"]).out
        return [line.strip() for line in said.split("\n") if line.strip()]
    landed = Landed(runner, where)
    held = [(branch, ticket) for branch, listed, ticket in landed.lines() if listed == commit]
    for branch in sorted({branch for branch, _ in held}):
        said = io.StringIO()
        if not fetch_origin(runner, where, branch, said, wait):
            raise refusal("origin/{} could not be fetched, so the list cannot be checked. git "
                          "said:\n{}".format(branch, said.getvalue().rstrip("\n")))
        landed.on(branch, where)
    return sorted({ticket for _, ticket in held})


def main(argv, runner, out, err, wait, where=None):
    where = where or os.getcwd()
    try:
        if len(argv) == 2 and argv[0] == TICKET_OF:
            out.write("".join(ticket + "\n" for ticket in ticket_of(runner, where, argv[1], wait)))
            return 0
        if not well_formed(argv):
            raise misuse(USAGE)
        spec = str(int(argv[0]))
        only = ticket_named(spec, argv[2]) if len(argv) == 3 else None
        tracker = opened(runner, where, spec)
        commits, named = commits_and_tickets(tracker, spec, argv[1], wait)
        if only is not None:
            named = {tracker.commit_ticket(only)} & named
        out.write("\n".join(printed(tracker, commit, tickets & named)
                            for commit, tickets in commits if tickets & named))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, time.sleep, sys.argv[1]))
