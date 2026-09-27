# /// script
# dependencies = ["filelock>=3.16"]
# ///
#
# Land one finished ticket on its Target branch.
#
#   land-ticket <worktree> <ticket-number> [session-id] [--spec <spec-number>]
#   land-ticket --plan
#
# In spec mode a landing run by hand names its spec, which names the Target branch.
#
# Exits 0 once the ticket's commit is on the remote's Target branch. Exits non-zero with
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
# A landing that lost a race keeps the Turn, so no loop beats it while its suite runs.
#
# Env:
#   SPEC_LOOP_PERMISSION_MODE   passed to `claude -p` (default: acceptEdits)
#
# A script of its own, so the risky part can be proved against a throwaway
# repository without running a session.

import os
import re
import sys
import time
from pathlib import Path
from typing import NamedTuple

from filelock import FileLock, Timeout

from fetch_origin import ATTEMPTS as FETCH_ATTEMPTS
from fetch_origin import fetch_origin
from runner import Subprocess, session_changes
from steering.target_branch import in_spec_mode, target_branch_for, tracker_for
from stop import Stop, is_a_number, misuse, refusal
from suite import Suite

USAGE = (
    "usage: land-ticket <worktree> <ticket-number> [session-id] [--spec <spec-number>]\n"
    "       land-ticket --plan\n"
)

SPEC_FLAG = "--spec"

# Another loop pushing is expected, so a lost race is tried again with no cap.
LOST_RACE = ("(fetch first)", "(non-fast-forward)")

# These stay in the order the steps happen, or the plan lies about the run.
PLAN = (
    ("verify",
     "the worktree, its tree and the trailer on its commit",
     "is-a-worktree tree-clean ticket-named"),
    ("fetch",
     "git fetch origin (up to {} attempts)".format(FETCH_ATTEMPTS),
     "origin-has-target something-to-land"),
    ("rebase",
     "git rebase origin/<target>, when the base has moved",
     "commits-kept files-kept"),
    ("resolve",
     "the build session, when the rebase conflicts",
     "session-named no-refusal none-left-conflicting no-marker-staged rebase-carried-on"),
    ("suite",
     "the whole suite, when the base has moved",
     "suite-can-run suite-green"),
    ("push",
     "git push origin HEAD:<target>, again after each lost race",
     "pushed"),
    ("tell",
     "gh issue comment naming the commits that reached <target>, when the rebase replaced them",
     "commented"),
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


# The shared git folder, so every worktree of one clone meets the same Turn.
class Turn:
    def __init__(self, folder, holder):
        self.lock = FileLock(Path(folder) / "skillworks-turn")
        self.holder_path = Path(folder) / "skillworks-turn-holder"
        self.holder = holder

    @staticmethod
    def of(runner, worktree, holder):
        said = runner.run(["git", "-C", worktree, "rev-parse", "--path-format=absolute",
                           "--git-common-dir"])
        return Turn(said.out.strip(), holder)

    def take(self, waiting):
        try:
            self.lock.acquire(blocking=False)
        except Timeout:
            waiting(self.held_by())
            self.lock.acquire()
        self.holder_path.write_text(self.holder, encoding="utf-8")

    def held_by(self):
        try:
            return self.holder_path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    def let_go(self):
        self.lock.release()


class Landing:
    def __init__(self, runner, worktree, ticket, session, out, err, wait, permission_mode,
                 target=None, spec=None, tracker=None):
        self.runner = runner
        self.tracker = tracker
        self.spec = spec
        self.worktree = Path(worktree).as_posix()
        self.ticket = ticket
        self.session = session
        self.out = out
        self.err = err
        self.wait = wait
        self.permission_mode = permission_mode
        # None when no conflict is in hand, so a stop can tell whether it has one to record.
        self.conflict = None
        self.target = target

    @property
    def upstream(self):
        return "origin/" + self.target

    # A landing run by hand reads its Tracker in verify, so a stop before then has none to ask.
    @property
    def named(self):
        return self.tracker.named(self.ticket) if self.tracker else "ticket " + self.ticket

    def say(self, said):
        self.out.write("ok    " + said + "\n")

    # A stop with a conflict in hand is the driver's, because a refusal records itself first.
    def die(self, said):
        if self.conflict is not None:
            self.conflict_ended("caught")
        return refusal(said)

    def conflict_ended(self, outcome):
        self.out.write("note  conflict {} {} outcome={}\n".format(
            self.named, self.conflict.size(), outcome))
        self.conflict = None

    def git(self, *args, env=None):
        return self.runner.run(["git", "-C", self.worktree] + [str(a) for a in args], env=env)

    def read(self, said, *args):
        ran = self.git(*args)
        if ran.status != 0:
            raise self.die("{} {}. Nothing was pushed.".format(self.named, said))
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
                "{} could not be proved on the new base, because the suite could not start. "
                "Nothing was pushed. The reason was: {}".format(self.named, outcome.said))
        if not outcome.passed:
            raise self.die(
                "{} passed on its own and then failed the suite on the new base. Nothing was "
                "pushed. The suite said:\n{}".format(self.named, outcome.said))

    # Read from the message, so a commit reaches its ticket with no tracker call.
    def trailer_of(self, commit):
        said = self.git("log", "-1", commit, "--format=%(trailers:key=Ticket,valueonly)").out
        return "".join(c for c in said.split("\n")[0] if not c.isspace())

    # A worktree is cut from its Target branch, so the fork point is where its own commits begin.
    def ticket_commits(self):
        # A checkout with no such ref is one the fetch step turns down by name a moment later.
        base = self.git("merge-base", "HEAD", self.upstream)
        if base.status != 0:
            return listed(self.git("rev-parse", "--short", "HEAD").out)
        return listed(self.read("has commits git would not list against its base",
                                "log", "--reverse", "--format=%h", base.out.strip() + "..HEAD"))

    # A tracker that will not answer says so, so the session is not left guessing.
    def closing_note(self, trailer):
        body = self.tracker.closing_note(trailer)
        if body is None:
            return ("(The tracker would not answer for {}, so its Closing note is "
                    "missing.)".format(trailer))
        return body if body else "({} was closed with no comment.)".format(trailer)

    # The session may only refuse for want of a ticket once it has had them all.
    def other_side(self, base):
        commits = self.git("log", "--reverse", "--format=%h %s", base + ".." + self.upstream)
        if commits.status != 0:
            return None
        said = ""
        for line in listed(commits.out):
            sha, _, subject = line.partition(" ")
            ticket = self.trailer_of(sha)
            if not ticket:
                said += ("### {} {}\n\nThis commit names no ticket. Read it with: "
                         "git show {}\n\n").format(sha, subject, sha)
                continue
            said += "### {} {}, from ticket {}\n\nHow {} was closed:\n\n{}\n\n".format(
                sha, subject, ticket, ticket, self.closing_note(ticket))
        return said

    def resolve_prompt(self, base, conflicted):
        rest = self.other_side(base)
        if rest is None:
            return None
        return (
            "/skillworks:resolve-conflict\n\n"
            "Ticket {t} was rebased onto the newest {u} and stopped on a conflict.\n"
            "Its worktree is {w}, and the rebase is open in it.\n\n"
            "## The conflicting files\n\n{f}\n\n"
            "## The other side\n\nThese landed on {b} while {t} was being built.\n\n{r}"
        ).format(t=self.named, u=self.upstream, b=self.target, w=self.worktree,
                 f="\n".join(conflicted), r=rest)

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
                "{t} stopped its rebase in {w} with no conflicting file in it, so there is "
                "nothing to resolve. Nothing was pushed.\ngit said:\n{g}".format(
                    t=self.named, w=self.worktree, g=refused))

        # Measured before the session is asked, so a conflict that goes nowhere is still counted.
        self.conflict = self.measure(conflicted)

        if not self.session:
            raise self.die(
                "{t} conflicts with what landed on {b} while it was being built, and no session "
                "was named to resolve it. The rebase is still open in {w}, and nothing was pushed. "
                "Put it back with: git -C {w} rebase --abort\ngit said:\n{g}".format(
                    t=self.named, b=self.target, w=self.worktree, g=refused))

        self.say("{} conflicts with the other side. Session {} wrote its side, so it resolves it."
                 .format(self.named, self.session))

        prompt = self.resolve_prompt(base, conflicted)
        if prompt is None:
            raise self.die("{} could not gather the other side to hand over. Nothing was pushed."
                           .format(self.named))

        ran = self.resolve_call(prompt)
        said = (ran.out + ran.err).rstrip("\n")
        if ran.status != 0:
            raise self.die(
                "{t} handed its conflict to session {s}, which exited non-zero. The rebase is "
                "still open in {w}, and nothing was pushed. It said:\n{m}".format(
                    t=self.named, s=self.session, w=self.worktree, m=said))

        rule = REFUSAL.search(said)
        if rule:
            self.conflict_ended("refused")
            raise self.die(
                "{t} came back from session {s}, which refused under rule {r}. The rebase is "
                "still open in {w}, and nothing was pushed. The session said:\n{m}".format(
                    t=self.named, s=self.session, r=rule.group(1), w=self.worktree, m=said))

        # Leaving the conflict standing is a refusal too, and one that named no rule may be broken.
        left = self.unmerged()
        if left:
            self.conflict_ended("refused")
            raise self.die(
                "{t} came back from session {s}, which named no rule, with these files still "
                "conflicting:\n{l}\nThe rebase is still open in {w}, and nothing was pushed. The "
                "session said:\n{m}".format(
                    t=self.named, s=self.session, l="\n".join(left), w=self.worktree, m=said))

        # A commit is made of the index, so the index is what is read here.
        for name in conflicted:
            # A hunk can be settled by removing the file, and then there is nothing to read.
            if self.git("cat-file", "-e", ":" + name).status != 0:
                continue
            if self.git("grep", "--cached", "-q", "-E", MARKER, "--", name).status == 0:
                raise self.die(
                    "{t} staged {f} with a conflict marker still in it, so the resolution is "
                    "half finished. The rebase is still open in {w}, and nothing was pushed. The "
                    "session said:\n{m}".format(t=self.named, f=name, w=self.worktree, m=said))

        carried = self.git("rebase", "--continue", env={"GIT_EDITOR": "true"})
        if carried.status != 0:
            # One call resolves one commit, so a ticket whose next commit conflicts stops here.
            later = self.unmerged()
            if later:
                # The run stopped before anything could say the first resolution was any good.
                self.conflict_ended("caught")
                self.conflict = self.measure(later)
                raise self.die(
                    "{t} resolved its first conflict and a later commit of its own conflicted as "
                    "well. Only the first is handed over, so the rebase is still open in {w}, and "
                    "nothing was pushed. Put it back with: git -C {w} rebase --abort".format(
                        t=self.named, w=self.worktree))
            raise self.die(
                "{t} resolved its conflicting files and the rebase would not carry on. The "
                "rebase is still open in {w}, and nothing was pushed. git said:\n{g}".format(
                    t=self.named, w=self.worktree, g=(carried.out + carried.err).rstrip("\n")))

        self.say("{} resolved its conflict in session {}".format(self.named, self.session))

    # A rebase that quietly dropped the work would otherwise push an empty success.
    def survived(self, mine, before):
        landed = self.read("has commits git would not count against the new base",
                           "rev-list", "--count", self.upstream + "..HEAD").strip()
        if landed != mine:
            raise self.die(
                "{t} had {m} commit(s) before the rebase and has {l} on the new base. The rebase "
                "dropped work, and nothing was pushed. Get it back with: git -C {w} reset --hard "
                "ORIG_HEAD".format(t=self.named, m=mine, l=landed, w=self.worktree))

        # A resolution that takes the other side wholesale keeps the commit and loses the file.
        here = listed(self.read("has files git would not list against the new base",
                                "diff", "--name-only", self.upstream, "HEAD"))
        missing = "".join("\n  " + name for name in before if name not in here)
        if missing:
            raise self.die(
                "{t} changed these files before the rebase and no longer changes them on the new "
                "base:{f}\nThe rebase dropped work, and nothing was pushed. Get it back with: "
                "git -C {w} reset --hard ORIG_HEAD".format(
                    t=self.named, f=missing, w=self.worktree))

    def rebase_onto_target(self, base):
        mine = self.read("has commits git would not count against its base",
                         "rev-list", "--count", base + "..HEAD").strip()
        mine_files = listed(self.read("has files git would not list against its base",
                                      "diff", "--name-only", base, "HEAD"))

        said = self.git("rebase", self.upstream)
        if said.status != 0:
            self.resolve_conflict(base, (said.out + said.err).rstrip("\n"))

        self.survived(mine, mine_files)

        commit = self.git("rev-parse", "--short", "HEAD").out.strip()
        self.say("{} rebased onto {} as {}".format(
            self.named, self.git("rev-parse", "--short", self.upstream).out.strip(), commit))

        # A merge that resolves with no conflict can still break the program.
        self.run_suite()
        self.say("{} passed the suite on the new base".format(self.named))

        # Every check the resolution had to pass is behind it, so the outcome is settled.
        if self.conflict is not None:
            self.conflict_ended("resolved")
        return commit

    def verify(self):
        if self.git("rev-parse", "--git-dir").status != 0:
            raise self.die(self.worktree + " is not a git worktree. Nothing was pushed.")

        # The worktree script read the main checkout's settings, so a landing handed none reads the same ones.
        # The Tracker is read before the push, so a landing never pushes and then finds it has none.
        if not self.target or self.tracker is None:
            top = self.main_checkout()
            self.tracker = self.tracker or tracker_for(self.runner, top, self.spec)
        if not self.target:
            if self.spec is None and in_spec_mode(top):
                raise self.die(
                    "{t} cannot be landed, because in spec mode each spec names its own Target "
                    "branch and no spec was given. Nothing was pushed. Name the spec with: "
                    "land-ticket {w} {n} [session-id] --spec <spec-number>".format(
                        t=self.named, n=self.ticket, w=self.worktree))
            self.target = target_branch_for(self.runner, top, self.spec, self.tracker)

        # A commit does not carry unfinished work, so pushing would leave it behind.
        if self.git("status", "--porcelain").out.strip():
            raise self.die("{} has uncommitted changes in {}. Nothing was pushed.".format(
                self.named, self.worktree))

        # A commit with no trailer can never be traced back, and a ticket can make more than one.
        mine = self.tracker.trailer(self.ticket)
        for sha in self.ticket_commits():
            named = self.trailer_of(sha)
            if not named:
                raise self.die(
                    "commit {} carries no 'Ticket: {}' trailer, so it could never be traced "
                    "back. Nothing was pushed.".format(sha, mine))
            if named != mine:
                raise self.die("commit {} names ticket {}, and this is {}. Nothing was pushed."
                               .format(sha, named, mine))

    # Git lists the main checkout first, whichever worktree asks.
    def main_checkout(self):
        said = self.read("would not list its worktrees", "worktree", "list", "--porcelain")
        return said.split("\n")[0][len("worktree "):]

    # A waiter names the holder, so a hung suite can be found and its loop killed.
    def holder(self):
        branch = self.git("rev-parse", "--abbrev-ref", "HEAD").out.strip()
        spec = re.match(r"spec-loop/([0-9]+)/", branch)
        mine = "ticket " + self.named
        return "spec {} {}".format(self.tracker.spec_named(spec.group(1)), mine) if spec else mine

    def take(self, turn):
        def waiting(holder):
            self.out.write("note  {} waits for the Turn, which {} holds\n".format(
                self.named, holder or "another landing"))
            self.out.flush()
        turn.take(waiting)

    def land(self):
        self.verify()
        turn = Turn.of(self.runner, self.worktree, self.holder())
        try:
            self.land_on(turn)
        finally:
            turn.let_go()

    # The finishing step closed the ticket naming the commits it made, which a rebase replaces.
    def name_the_rebased(self, built):
        landed = listed(self.git("log", "--reverse", "--format=%h",
                                 "-{}".format(len(built)), "HEAD").out)
        pairs = "".join("\n- {} replaces {}".format(new, old) for old, new in zip(built, landed))
        body = ("{t} was rebased onto the newest {b} before it landed, so the commits named when "
                "it was closed are on no branch. The commits that reached {b}:\n{p}").format(
                    t=self.named, b=self.target, p=pairs)
        if not self.tracker.comment(self.ticket, body):
            # The push is done and cannot be taken back, so a lost comment is reported, not fatal.
            self.out.write("note  {} landed, and the tracker would not take the comment that "
                           "names its new commits:{}\n".format(self.named, pairs))
            return
        self.say("{} was told the commits that reached {}".format(self.named, self.target))

    def land_on(self, turn):
        commit = self.git("rev-parse", "--short", "HEAD").out.strip()
        built = self.ticket_commits()
        rebased = False

        tries = 1
        kept = False
        while True:
            if not fetch_origin(self.runner, self.worktree, self.target, self.err, self.wait):
                raise self.die("{} could not fetch {} from origin. Nothing was pushed."
                               .format(self.named, self.target))
            if self.git("rev-parse", "--verify", "--quiet", self.upstream).status != 0:
                raise self.die("origin has no {} branch. Nothing was pushed.".format(self.target))

            # A ticket already on its Target branch would push nothing and call that a success.
            if not self.git("rev-list", "-1", self.upstream + "..HEAD").out.strip():
                raise self.die("{} is already on {} and has nothing left to land. Nothing was "
                               "pushed.".format(self.named, self.target))

            # An unmoved base is one the finishing step's own test run still answers for.
            base = self.git("merge-base", "HEAD", self.upstream).out.strip()
            if base != self.git("rev-parse", self.upstream).out.strip():
                commit = self.rebase_onto_target(base)
                rebased = True

            if not kept:
                self.take(turn)
            pushed = self.git("push", "--quiet", "origin", "HEAD:" + self.target)
            if pushed.status == 0:
                self.say("{} landed on {} as {} in {} {}, holding the Turn {}".format(
                    self.named, self.target, commit, tries, "try" if tries == 1 else "tries",
                    "from fetch to push" if kept else "for its push"))
                if rebased and self.tracker.close_names_commits:
                    self.name_the_rebased(built)
                return

            said = (pushed.out + pushed.err).rstrip("\n")
            if not any(mark in said for mark in LOST_RACE):
                raise self.die("{} could not be pushed. Nothing was pushed. git said:\n{}".format(
                    self.named, said))
            tries += 1
            if not kept:
                turn.let_go()
                self.out.write("note  {} lost a race to {}, so it takes the Turn and keeps it "
                               "until the landing ends\n".format(self.named, self.target))
                self.out.flush()
                self.take(turn)
                kept = True


def spec_named(argv):
    if SPEC_FLAG not in argv:
        return argv, None
    at = argv.index(SPEC_FLAG)
    spec = argv[at + 1] if len(argv) > at + 1 else ""
    if not is_a_number(spec):
        raise misuse(USAGE)
    return argv[:at] + argv[at + 2:], spec


def permission_mode_set():
    return os.environ.get("SPEC_LOOP_PERMISSION_MODE", "acceptEdits")


# The driver hands in the mode of its run, so the resolving Session never falls back to the default.
# It hands in the Target branch too, since in spec mode only the driver has read the spec.
def main(argv, runner, out, err, wait, permission_mode=None, target=None, tracker=None):
    if permission_mode is None:
        permission_mode = permission_mode_set()
    try:
        argv, spec = spec_named(argv)
        worktree = argv[0] if len(argv) > 0 else ""
        ticket = argv[1] if len(argv) > 1 else ""
        session = argv[2] if len(argv) > 2 else ""

        if worktree == "--plan":
            for step in PLAN:
                out.write("\t".join(step) + "\n")
            return 0
        if not worktree or not is_a_number(ticket) or len(argv) > 3:
            raise misuse(USAGE)

        Landing(runner, worktree, ticket, session, out, err, wait, permission_mode,
                target, spec, tracker).land()
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    # Windows adds a carriage return, which the driver would read as part of the plan.
    sys.stdout.reconfigure(newline="\n")
    sys.stderr.reconfigure(newline="\n")
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr, time.sleep))
