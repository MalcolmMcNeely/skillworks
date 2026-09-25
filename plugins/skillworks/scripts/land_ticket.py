#
# Land one finished ticket on main.
#
#   land-ticket <worktree> <ticket-number> [session-id]
#   land-ticket --plan
#
# Exits 0 once the ticket's commit is on the remote's main. Exits non-zero with
# the reason on stderr, having pushed nothing.
#
# `--plan` prints the steps and their checks, tab separated, and does none of them.
#
# Another loop lands its own work while a ticket is built, so a moved base is
# rebased onto, and the suite is asked again before the push.
#
# The session that built the ticket wrote one side of any conflict, so it is the
# one asked to resolve it.
#
# Env:
#   SPEC_LOOP_PERMISSION_MODE   passed to `claude -p` (default: acceptEdits)
#
# A script of its own, so the risky part can be proved against a throwaway
# repository without running a session.

import os
import re
import sys
from pathlib import Path
from typing import NamedTuple

from fetch_origin import ATTEMPTS as FETCH_ATTEMPTS
from fetch_origin import fetch_origin
from runner import Subprocess, session_changes
from stop import Stop, is_a_number, misuse, refusal
from suite import Suite

USAGE = (
    "usage: land-ticket <worktree> <ticket-number> [session-id]\n"
    "       land-ticket --plan\n"
)

# Enough for a collision with another loop, few enough that this cannot spin.
ATTEMPTS = 3

# These stay in the order the steps happen, or the plan lies about the run.
PLAN = (
    ("verify",
     "the worktree, its tree and the trailer on its commit",
     "is-a-worktree tree-clean ticket-named"),
    ("fetch",
     "git fetch origin (up to {} attempts)".format(FETCH_ATTEMPTS),
     "origin-has-main something-to-land"),
    ("rebase",
     "git rebase origin/main, when the base has moved",
     "commits-kept files-kept"),
    ("resolve",
     "the build session, when the rebase conflicts",
     "session-named no-refusal none-left-conflicting no-marker-staged rebase-carried-on"),
    ("suite",
     "the whole suite, when the base has moved",
     "suite-can-run suite-green"),
    ("push",
     "git push origin HEAD:main",
     "pushed (up to {} attempts)".format(ATTEMPTS)),
)

# A refusal is what the session declares, whatever it went on to leave in the index.
REFUSAL = re.compile(r"^[ \t]*REFUSED[ \t]*([0-9]+)", re.MULTILINE)

# A blob committed with CRLF ends its marker line in a carriage return.
MARKER = r"^(<<<<<<< |=======[[:space:]]*$|>>>>>>> )"


# No size limit is imposed, so this measure is what lets one be set from real numbers.
class Conflict(NamedTuple):
    files: int
    hunks: int
    lines: int

    def size(self):
        return "files={} hunks={} lines={}".format(self.files, self.hunks, self.lines)


def listed(said):
    return [line for line in said.split("\n") if line != ""]


class Landing:
    def __init__(self, runner, worktree, ticket, session, out, err):
        self.runner = runner
        self.worktree = Path(worktree).as_posix()
        self.ticket = ticket
        self.session = session
        self.out = out
        self.err = err
        self.permission_mode = os.environ.get("SPEC_LOOP_PERMISSION_MODE", "acceptEdits")
        # None when no conflict is in hand, so a stop can tell whether it has one to record.
        self.conflict = None

    def say(self, said):
        self.out.write("ok    " + said + "\n")

    # A stop with a conflict in hand is the driver's, because a refusal records itself first.
    def die(self, said):
        if self.conflict is not None:
            self.conflict_ended("caught")
        return refusal(said)

    def conflict_ended(self, outcome):
        self.out.write("note  conflict #{} {} outcome={}\n".format(
            self.ticket, self.conflict.size(), outcome))
        self.conflict = None

    def git(self, *args, env=None):
        return self.runner.run(["git", "-C", self.worktree] + [str(a) for a in args], env=env)

    def read(self, said, *args):
        ran = self.git(*args)
        if ran.status != 0:
            raise self.die("#{} {}. Nothing was pushed.".format(self.ticket, said))
        return ran.out

    def measure(self, conflicted):
        files = 0
        hunks = 0
        counted = 0
        for name in conflicted:
            files += 1
            # A modify/delete conflict leaves a file with no marker in it, and so does a binary one.
            path = Path(self.worktree) / name
            if not path.is_file():
                continue
            with path.open(encoding="utf-8", errors="replace", newline="") as file:
                text = file.read()
            in_hunk = False
            # The base section is not a side, so the count is the same in any conflict style.
            side = False
            for line in text.split("\n"):
                line = line.rstrip("\r")
                if line.startswith("<<<<<<< "):
                    in_hunk = True
                    side = True
                    hunks += 1
                elif not in_hunk:
                    continue
                elif line.startswith("|||||||"):
                    side = False
                elif line == "=======":
                    side = True
                elif line.startswith(">>>>>>> "):
                    in_hunk = False
                elif side:
                    counted += 1
        return Conflict(files, hunks, counted)

    def unmerged(self):
        return listed(self.git("diff", "--name-only", "--diff-filter=U").out)

    # The suite says a great deal, and only a failure is worth reading.
    def run_suite(self):
        outcome = Suite(self.runner, self.worktree).run()
        # A suite that never started says nothing about the ticket, so it is named apart.
        if not outcome.ready:
            raise self.die(
                "#{} could not be proved on the new base, because the suite could not start. "
                "Nothing was pushed. The reason was: {}".format(self.ticket, outcome.said))
        if not outcome.passed:
            raise self.die(
                "#{} passed on its own and then failed the suite on the new base. Nothing was "
                "pushed. The suite said:\n{}".format(self.ticket, outcome.said))

    # Read from the message, so a commit reaches its ticket with no tracker call.
    def ticket_of(self, commit):
        said = self.git("log", "-1", commit, "--format=%(trailers:key=Ticket,valueonly)").out
        named = "".join(c for c in said.split("\n")[0] if not c.isspace())
        return named[1:] if named.startswith("#") else named

    # A worktree is cut from origin/main, so the fork point is where its own commits begin.
    def ticket_commits(self):
        # A checkout with no such ref is one the fetch step turns down by name a moment later.
        base = self.git("merge-base", "HEAD", "origin/main")
        if base.status != 0:
            return listed(self.git("rev-parse", "--short", "HEAD").out)
        return listed(self.read("has commits git would not list against its base",
                                "log", "--reverse", "--format=%h", base.out.strip() + "..HEAD"))

    # The last comment is how a ticket was closed, and a tracker that will not answer says so.
    def closing_comment(self, ticket):
        ran = self.runner.run(
            ["gh", "issue", "view", ticket, "--json", "comments", "--jq",
             ".comments[-1].body"], self.worktree,
            # gh asks at a terminal, and a landing has nobody at one.
            {"GH_PROMPT_DISABLED": "1"})
        if ran.status != 0:
            return ("(The tracker would not answer for #{}, so its closing comment is "
                    "missing.)".format(ticket))
        body = ran.out.rstrip("\n")
        return body if body else "(#{} was closed with no comment.)".format(ticket)

    # The session may only refuse for want of a ticket once it has had them all.
    def other_side(self, base):
        commits = self.git("log", "--reverse", "--format=%h %s", base + "..origin/main")
        if commits.status != 0:
            return None
        said = ""
        for line in listed(commits.out):
            sha, _, subject = line.partition(" ")
            ticket = self.ticket_of(sha)
            if not ticket:
                said += ("### {} {}\n\nThis commit names no ticket. Read it with: "
                         "git show {}\n\n").format(sha, subject, sha)
                continue
            said += "### {} {}, from ticket #{}\n\nHow #{} was closed:\n\n{}\n\n".format(
                sha, subject, ticket, ticket, self.closing_comment(ticket))
        return said

    def resolve_prompt(self, base, conflicted):
        rest = self.other_side(base)
        if rest is None:
            return None
        return (
            "/skillworks:resolve-conflict\n\n"
            "Ticket #{t} was rebased onto the newest origin/main and stopped on a conflict.\n"
            "Its worktree is {w}, and the rebase is open in it.\n\n"
            "## The conflicting files\n\n{f}\n\n"
            "## The other side\n\nThese landed on main while #{t} was being built.\n\n{r}"
        ).format(t=self.ticket, w=self.worktree, f="\n".join(conflicted), r=rest)

    def resolve_call(self, prompt):
        return self.runner.run(
            ["claude", "-p", prompt, "--resume", self.session,
             "--permission-mode", self.permission_mode],
            self.worktree,
            session_changes())

    def resolve_conflict(self, base, refused):
        conflicted = self.unmerged()
        if not conflicted:
            raise self.die(
                "#{t} stopped its rebase in {w} with no conflicting file in it, so there is "
                "nothing to resolve. Nothing was pushed.\ngit said:\n{g}".format(
                    t=self.ticket, w=self.worktree, g=refused))

        # Measured before the session is asked, so a conflict that goes nowhere is still counted.
        self.conflict = self.measure(conflicted)

        if not self.session:
            raise self.die(
                "#{t} conflicts with what landed on main while it was being built, and no session "
                "was named to resolve it. The rebase is still open in {w}, and nothing was pushed. "
                "Put it back with: git -C {w} rebase --abort\ngit said:\n{g}".format(
                    t=self.ticket, w=self.worktree, g=refused))

        self.say("#{} conflicts with the other side. Session {} wrote its side, so it resolves it."
                 .format(self.ticket, self.session))

        prompt = self.resolve_prompt(base, conflicted)
        if prompt is None:
            raise self.die("#{} could not gather the other side to hand over. Nothing was pushed."
                           .format(self.ticket))

        ran = self.resolve_call(prompt)
        said = (ran.out + ran.err).rstrip("\n")
        if ran.status != 0:
            raise self.die(
                "#{t} handed its conflict to session {s}, which exited non-zero. The rebase is "
                "still open in {w}, and nothing was pushed. It said:\n{m}".format(
                    t=self.ticket, s=self.session, w=self.worktree, m=said))

        rule = REFUSAL.search(said)
        if rule:
            self.conflict_ended("refused")
            raise self.die(
                "#{t} came back from session {s}, which refused under rule {r}. The rebase is "
                "still open in {w}, and nothing was pushed. The session said:\n{m}".format(
                    t=self.ticket, s=self.session, r=rule.group(1), w=self.worktree, m=said))

        # Leaving the conflict standing is a refusal too, and one that named no rule may be broken.
        left = self.unmerged()
        if left:
            self.conflict_ended("refused")
            raise self.die(
                "#{t} came back from session {s}, which named no rule, with these files still "
                "conflicting:\n{l}\nThe rebase is still open in {w}, and nothing was pushed. The "
                "session said:\n{m}".format(
                    t=self.ticket, s=self.session, l="\n".join(left), w=self.worktree, m=said))

        # A commit is made of the index, so the index is what is read here.
        for name in conflicted:
            # A hunk can be settled by removing the file, and then there is nothing to read.
            if self.git("cat-file", "-e", ":" + name).status != 0:
                continue
            if self.git("grep", "--cached", "-q", "-E", MARKER, "--", name).status == 0:
                raise self.die(
                    "#{t} staged {f} with a conflict marker still in it, so the resolution is "
                    "half finished. The rebase is still open in {w}, and nothing was pushed. The "
                    "session said:\n{m}".format(t=self.ticket, f=name, w=self.worktree, m=said))

        carried = self.git("rebase", "--continue", env={"GIT_EDITOR": "true"})
        if carried.status != 0:
            # One call resolves one commit, so a ticket whose next commit conflicts stops here.
            later = self.unmerged()
            if later:
                # The run stopped before anything could say the first resolution was any good.
                self.conflict_ended("caught")
                self.conflict = self.measure(later)
                raise self.die(
                    "#{t} resolved its first conflict and a later commit of its own conflicted as "
                    "well. Only the first is handed over, so the rebase is still open in {w}, and "
                    "nothing was pushed. Put it back with: git -C {w} rebase --abort".format(
                        t=self.ticket, w=self.worktree))
            raise self.die(
                "#{t} resolved its conflicting files and the rebase would not carry on. The "
                "rebase is still open in {w}, and nothing was pushed. git said:\n{g}".format(
                    t=self.ticket, w=self.worktree, g=(carried.out + carried.err).rstrip("\n")))

        self.say("#{} resolved its conflict in session {}".format(self.ticket, self.session))

    # A rebase that quietly dropped the work would otherwise push an empty success.
    def survived(self, mine, before):
        landed = self.read("has commits git would not count against the new base",
                           "rev-list", "--count", "origin/main..HEAD").strip()
        if landed != mine:
            raise self.die(
                "#{t} had {m} commit(s) before the rebase and has {l} on the new base. The rebase "
                "dropped work, and nothing was pushed. Get it back with: git -C {w} reset --hard "
                "ORIG_HEAD".format(t=self.ticket, m=mine, l=landed, w=self.worktree))

        # A resolution that takes the other side wholesale keeps the commit and loses the file.
        here = listed(self.read("has files git would not list against the new base",
                                "diff", "--name-only", "origin/main", "HEAD"))
        missing = "".join("\n  " + name for name in before if name not in here)
        if missing:
            raise self.die(
                "#{t} changed these files before the rebase and no longer changes them on the new "
                "base:{f}\nThe rebase dropped work, and nothing was pushed. Get it back with: "
                "git -C {w} reset --hard ORIG_HEAD".format(
                    t=self.ticket, f=missing, w=self.worktree))

    def rebase_onto_main(self, base):
        mine = self.read("has commits git would not count against its base",
                         "rev-list", "--count", base + "..HEAD").strip()
        mine_files = listed(self.read("has files git would not list against its base",
                                      "diff", "--name-only", base, "HEAD"))

        said = self.git("rebase", "origin/main")
        if said.status != 0:
            self.resolve_conflict(base, (said.out + said.err).rstrip("\n"))

        self.survived(mine, mine_files)

        commit = self.git("rev-parse", "--short", "HEAD").out.strip()
        self.say("#{} rebased onto {} as {}".format(
            self.ticket, self.git("rev-parse", "--short", "origin/main").out.strip(), commit))

        # A merge that resolves with no conflict can still break the program.
        self.run_suite()
        self.say("#{} passed the suite on the new base".format(self.ticket))

        # Every check the resolution had to pass is behind it, so the outcome is settled.
        if self.conflict is not None:
            self.conflict_ended("resolved")
        return commit

    def verify(self):
        if self.git("rev-parse", "--git-dir").status != 0:
            raise self.die(self.worktree + " is not a git worktree. Nothing was pushed.")

        # A commit does not carry unfinished work, so pushing would leave it behind.
        if self.git("status", "--porcelain").out.strip():
            raise self.die("#{} has uncommitted changes in {}. Nothing was pushed.".format(
                self.ticket, self.worktree))

        # A commit with no trailer can never be traced back, and a ticket can make more than one.
        for sha in self.ticket_commits():
            named = self.ticket_of(sha)
            if not named:
                raise self.die(
                    "commit {} carries no 'Ticket: #{}' trailer, so it could never be traced "
                    "back. Nothing was pushed.".format(sha, self.ticket))
            if named != self.ticket:
                raise self.die("commit {} names ticket #{}, and this is #{}. Nothing was pushed."
                               .format(sha, named, self.ticket))

    def land(self):
        self.verify()
        commit = self.git("rev-parse", "--short", "HEAD").out.strip()

        attempt = 1
        while True:
            if not fetch_origin(self.runner, self.worktree, self.err):
                raise self.die("#{} could not fetch from origin. Nothing was pushed."
                               .format(self.ticket))
            if self.git("rev-parse", "--verify", "--quiet", "origin/main").status != 0:
                raise self.die("origin has no main branch. Nothing was pushed.")

            # A ticket already on main has nothing to land, and a push would call that a success.
            if not self.git("rev-list", "-1", "origin/main..HEAD").out.strip():
                raise self.die("#{} is already on main and has nothing left to land. Nothing was "
                               "pushed.".format(self.ticket))

            # An unmoved base is one the finishing step's own test run still answers for.
            base = self.git("merge-base", "HEAD", "origin/main").out.strip()
            if base != self.git("rev-parse", "origin/main").out.strip():
                commit = self.rebase_onto_main(base)

            pushed = self.git("push", "--quiet", "origin", "HEAD:main")
            if pushed.status == 0:
                self.say("#{} landed on main as {}".format(self.ticket, commit))
                return

            if attempt >= ATTEMPTS:
                raise self.die(
                    "#{t} was refused {a} times. Another loop keeps winning the race, or the "
                    "remote turns the commit down. The last try said:\n{m}".format(
                        t=self.ticket, a=ATTEMPTS, m=(pushed.out + pushed.err).rstrip("\n")))
            attempt += 1


def main(argv, runner, out, err):
    try:
        worktree = argv[0] if len(argv) > 0 else ""
        ticket = argv[1] if len(argv) > 1 else ""
        session = argv[2] if len(argv) > 2 else ""

        if worktree == "--plan":
            for step in PLAN:
                out.write("\t".join(step) + "\n")
            return 0
        if not worktree or not is_a_number(ticket):
            raise misuse(USAGE)

        Landing(runner, worktree, ticket, session, out, err).land()
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    # Windows adds a carriage return, which the driver would read as part of the plan.
    sys.stdout.reconfigure(newline="\n")
    sys.stderr.reconfigure(newline="\n")
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr))
