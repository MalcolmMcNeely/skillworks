#
# Drive one spec's tickets to done, sequentially, one fresh Claude session each.
# Each ticket is built in a throwaway worktree of its own, cut from the newest
# origin/main, and lands on the remote the moment it passes. The main checkout
# is never worked in, so it stays usable for the whole run.
#
#   spec-loop <spec-issue-number> [--dry-run]
#
# The script picks the next ticket. The model never picks. Control flow lives
# here so a run is inspectable, stoppable and resumable.
#
# A model can skip a step a skill asks for, so each step is its own call here.
# A step can exit 0 and do nothing, so the script checks facts after each one.
#
# The worktree script and the landing script are read as modules rather than
# started as programs, so one Runner carries the whole driver and a test has a
# single place to answer for everything it reaches.
#
# Env:
#   SPEC_LOOP_PERMISSION_MODE   passed to `claude -p` (default: acceptEdits). A spec whose
#                               tickets write under .claude/ needs bypassPermissions.
#
# Written against gh 2.92.0, which has no dependency flags. Everything goes
# through `gh api`. See docs/research/harness/ticket-state-guardrails.md.

import hashlib
import io
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

import land_ticket
import ticket_worktree
from fetch_origin import fetch_origin
from runner import Subprocess
from stop import MISUSED, REFUSED, Stop, is_a_number, misuse
from suite import Suite

USAGE = "usage: spec-loop <spec-issue-number> [--dry-run]\n"

# gh asks at a terminal, and a loop run has nobody at one.
GH_QUIET = {"GH_PROMPT_DISABLED": "1"}

# Long enough for another loop's write to be visible, and injected so a test need not pay it.
CLAIM_WAIT = 3

PARENT_KEY = "skillworks.parent.session.id"

# Under `claude -p` a background command dies with the Session, so the slowest check must fit in the foreground.
BASH_LIMIT_MS = str(45 * 60 * 1000)


class Step(NamedTuple):
    name: str
    # The ticket number goes in the one placeholder; a driver's own step holds a description.
    asks: str
    checks: str
    # A resumed step would read the one before it, so each axis and the sweep starts fresh.
    resumes: bool
    # False where the driver does the work, so nothing asks a Session for a result it never gave.
    session: bool = True


# The skills load from the Plugin, and Claude Code names a Plugin skill with the Plugin in front.
PLUGIN = "/skillworks:"

AXIS_CHECKS = "no-error command-loaded ticket-open axis-reported"

# One list, read by the plan and by the run, so the two cannot drift apart.
REVIEW_STEPS = ("standards", "spec", "architecture")

STEPS = (
    (Step("build", PLUGIN + "implement {} --stop-after-tests",
          "no-error command-loaded ticket-open tree-changed", False),)
    + tuple(Step(axis, PLUGIN + "review-" + axis + " {}", AXIS_CHECKS, False) for axis in REVIEW_STEPS)
    + (Step("fix", PLUGIN + "implement {} --fix", "no-error command-loaded ticket-open", True),
       Step("sweep", PLUGIN + "comment-sweep", "no-error command-loaded ticket-open", False),
       Step("suite", "the whole suite, as the Suite file names it",
            "suite-can-run suite-green", False, session=False),
       Step("finish", PLUGIN + "implement {} --finish",
            "no-error command-loaded new-commit tree-clean ticket-closed", True))
)

# A check that proves the work was done. One that proves the Session could run never earns a Nudge.
NUDGED_BY = ("axis-reported",)

# Enough for a Session that stopped short, and few enough that a stuck one stops where it can be read.
NUDGES = 2

NUDGE_TAIL = (
    "Any command you left in the background was stopped when your last turn ended, so its output "
    "is not complete. Run it again in the foreground.\n"
    "If something blocks you, say what it is.\n")

# The sweep follows the fix, because the fix writes and a sweep has to follow whatever wrote last.
CIRCUIT = ("fix", "sweep", "suite")


def nudged_on(step):
    return [check for check in step.checks.split() if check in NUDGED_BY]


def heading_of(axis):
    return "## " + axis[0].upper() + axis[1:]


def owed(step, check):
    if check == "axis-reported":
        return ("You have not written your report under the heading {}. Write it, with your "
                "findings or a statement that you found none.\n".format(heading_of(step.name)))
    return "The check {} has not passed.\n".format(check)


def step_named(name):
    return next(step for step in STEPS if step.name == name)


# Not `refusal`: that writes straight to stderr, and what the loop says goes to the log too.
def stop(said):
    return Stop(REFUSED, said)


def as_git_path(repo):
    return Path(repo).as_posix()


def field(path, name):
    try:
        held = json.loads(Path(path).read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return ""
    if not isinstance(held, dict):
        return ""
    value = held.get(name)
    return "" if value is None else value


# Cut short, because a write's input holds the whole file and one Denial is read on one line.
DENIAL_INPUT_CHARS = 80


def denials(path):
    held = field(path, "permission_denials")
    if not isinstance(held, list):
        return []
    named = []
    for denial in held:
        if not isinstance(denial, dict):
            continue
        given = json.dumps(denial.get("tool_input", {}))
        if len(given) > DENIAL_INPUT_CHARS:
            given = given[:DENIAL_INPUT_CHARS] + "..."
        named.append("{} {}".format(denial.get("tool_name", "an unnamed tool"), given))
    return named


def written(path, text):
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def appended(path, text):
    with Path(path).open("a", encoding="utf-8", newline="\n") as file:
        file.write(text)


def listed(said):
    return [line for line in said.split("\n") if line != ""]


# Every record the loop reads is three tab separated columns, and a short one still reads as three.
def columns(line):
    return (line.split("\t") + ["", ""])[:3]


# The bytes and not the file list, so an edit inside a file already changed is still seen.
def digest(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return ""


def changed_between(before, after):
    return sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))


def sessions_folder():
    held = os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude")
    return Path(held) / "projects"


# A session writes one file, under a folder named for the checkout it ran in.
def session_file(session):
    folder = sessions_folder()
    if not folder.is_dir():
        return None
    for project in sorted(folder.iterdir()):
        found = project / (session + ".jsonl")
        if found.is_file():
            return found
    return None


# Only a user prompt counts, since a tool result can quote the command tags.
def loaded(written_by_session, command, args):
    # Matched to the end of their first line, because the driver writes the reports below it.
    opening = "<command-args>" + args
    named = "<command-name>" + command + "</command-name>"
    for line in listed(written_by_session.read_text(encoding="utf-8", errors="replace")):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("type") != "user":
            continue
        message = entry.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or named not in content:
            continue
        if args == "" or opening + "</command-args>" in content or opening + "\n" in content:
            return True
    return False


# The ticket now running counts as remaining, so the estimate never flatters the run.
def progress_suffix(position, total, mean):
    said = "{}/{}".format(position, total)
    if mean is None:
        return said
    return said + "  ~{}m left".format((mean * (total - position + 1) + 30) // 60)


# Said rather than left to be worked out, so a flake is read off the log afterwards.
def suite_verdict(outcome, at):
    if not outcome.passed:
        return "went red"
    return "passed, so the red before it was a flake" if at > 1 else "passed"


# Only a Session sets this ID and a Child inherits the attribute, so all below name the first Parent.
def session_changes():
    # Claude Code sets this, and the session must not read as nested in this one.
    changes = {
        "CLAUDECODE": None,
        "BASH_DEFAULT_TIMEOUT_MS": BASH_LIMIT_MS,
        "BASH_MAX_TIMEOUT_MS": BASH_LIMIT_MS,
    }
    parent = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not parent:
        return changes
    # Appended, because the attributes a developer set still have to arrive.
    held = os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "")
    named = "{}={}".format(PARENT_KEY, parent)
    changes["OTEL_RESOURCE_ATTRIBUTES"] = held + "," + named if held else named
    return changes


def plan_line(name, what, checks=""):
    said = "      {:<12} {}\n".format(name, what)
    if checks:
        said += "                   checks: {}\n".format(checks)
    return said


class Loop:
    def __init__(self, runner, spec, out, err, wait):
        self.runner = runner
        self.spec = spec
        self.out = out
        self.err = err
        self.wait = wait
        self.permission_mode = os.environ.get("SPEC_LOOP_PERMISSION_MODE", "acceptEdits")
        self.session_changes = session_changes()
        self.log_dir = Path(".spec-loop") / spec
        self.log = self.log_dir / "loop.log"

        self.root = Path.cwd()
        self.repo = ""
        self.me = ""
        self.spec_title = ""
        self.ticket_count = 0

        self.job_worktree = ""
        self.ticket_base = ""
        self.position = 0

        # Not being None is also the record that the loop has already been round.
        self.red_suite = None

        # The driver read this one, so the finishing Session names it rather than proving it again.
        self.green_suite = None

        # Nothing is read from an earlier run, so a rerun grows a mean of its own.
        self.timed_tickets = 0
        self.timed_seconds = 0
        self.mean_seconds = None

    def wrote(self, said):
        self.out.write(said)
        appended(self.log, said)

    def say(self, said):
        self.wrote("{} {}\n".format(datetime.now(timezone.utc).strftime("%H:%M:%S"), said))

    # --- the programs this reaches -------------------------------------------

    def gh(self, *args):
        return self.runner.run(["gh"] + [str(a) for a in args], self.root.as_posix(), GH_QUIET)

    def git(self, repo, *args):
        return self.runner.run(["git", "-C", as_git_path(repo)] + [str(a) for a in args])

    # Recorded before the Session starts, so a run that stops mid-Session still knows who was working.
    def new_session(self):
        found = self.git(self.job_worktree, "rev-parse", "--absolute-git-dir")
        if found.status != 0:
            raise stop("FAIL  the git folder of {} would not be read, so no Session could be "
                       "recorded. {}".format(self.job_worktree, found.err.strip()))
        session = str(uuid.uuid4())
        appended(Path(found.out.strip()) / ticket_worktree.SESSIONS_RECORD, session + "\n")
        return ["--session-id", session]

    def claude_p(self, prompt, *rest):
        rest = [str(a) for a in rest] or self.new_session()
        return self.runner.run(
            ["claude", "-p", prompt] + rest
            + ["--permission-mode", self.permission_mode, "--output-format", "json"],
            self.job_worktree,
            self.session_changes)

    # A path comes back on stdout, so a reason takes stderr, and the log too for a background run.
    def worktree(self, command, job=""):
        out, err = io.StringIO(), io.StringIO()
        status = ticket_worktree.main(
            [command, self.root.as_posix(), self.spec, job], self.runner, out, err)
        if status != 0:
            self.err.write(err.getvalue())
            appended(self.log, err.getvalue())
        return status, out.getvalue(), err.getvalue()

    def opened(self, job):
        status, said, _ = self.worktree("open", job)
        if status != 0 or not said.strip():
            return ""
        return said.strip()

    def issue_field(self, issue, jq):
        return self.gh("api", "repos/{}/issues/{}".format(self.repo, issue), "--jq", jq)

    def issue_state(self, ticket):
        return self.issue_field(ticket, ".state")

    def sub_issues(self, query):
        return self.gh("api", "--paginate", "repos/{}/issues/{}/sub_issues".format(
            self.repo, self.spec), "--jq", query)

    # --- what a step asks for ------------------------------------------------

    def step_file(self, ticket, step, kind):
        return self.log_dir / "ticket-{}-{}.{}".format(ticket, step, kind)

    def edit_of(self, ticket, axis):
        held = self.step_file(ticket, axis, "edit")
        if not held.is_file():
            return "left no Edit"
        return held.read_text(encoding="utf-8", errors="replace").strip()

    # Read off disk rather than handed on by a session, so no session has to remember to carry them.
    def review_reports(self, ticket):
        said = ""
        for axis in REVIEW_STEPS:
            held = self.step_file(ticket, axis, "json")
            report = str(field(held, "result")).rstrip("\n")
            if not report:
                return None, "the {} axis left no report at {}\n".format(axis, held)
            said += "\n## The {} axis reported\n\n{}\n".format(axis, report)
            said += "\nThe {} axis {}.\n".format(axis, self.edit_of(ticket, axis))
        return said, ""

    def suite_report(self):
        if self.green_suite is None:
            return ""
        return ("\n\n## The suite passed\n\nThe driver ran the whole suite and read the result, so "
                "run no tests yourself. Name what follows in the closing comment as what proved "
                "the work.\n\n{}\n").format(self.green_suite.said.rstrip("\n"))

    # The checks and the plan read `asks`, so nothing added below the command line reaches them.
    def step_body(self, ticket, step):
        asked = step.asks.format(ticket)
        if step.name == "finish":
            return asked + self.suite_report(), ""
        if step.name != "fix":
            return asked, ""
        reports, reason = self.review_reports(ticket)
        if reports is None:
            return None, reason
        said = ("{}\n\nThe three review axes have run. Their reports follow, each with the Edit "
                "that axis made.\n{}").format(asked, reports.rstrip("\n"))
        if self.red_suite is not None:
            said += ("\n\n## The suite went red\n\nThe driver ran it as often as the Suite file "
                     "asks, and it went red every time. What it said follows.\n\n{}\n").format(
                         self.red_suite.said.rstrip("\n"))
        return said, ""

    # --- the checks ----------------------------------------------------------

    def command_loaded(self, session, command, args):
        found = session_file(session)
        if found is None:
            return False, 'No session named "{}" under {}\n'.format(session, sessions_folder())
        if loaded(found, command, args):
            return True, ""
        return False, '"{}" did not load as a command in {}\n'.format(
            (command + " " + args).strip(), found)

    # A session can end its turn having said nothing, so the heading is what proves it did not.
    def axis_reported(self, axis, held):
        if heading_of(axis) in str(field(held, "result")):
            return True, ""
        return False, ("the {} axis reported neither a finding nor a statement that it found "
                       "none\n".format(axis))

    def tree_of_job(self):
        return self.git(self.job_worktree, "status", "--porcelain").out.strip()

    def check_passes(self, ticket, step, check, held):
        if check == "no-error":
            return field(held, "is_error") is False, ""
        if check == "command-loaded":
            command, _, args = step.asks.format(ticket).partition(" ")
            return self.command_loaded(str(field(held, "session_id")), command, args)
        if check == "axis-reported":
            return self.axis_reported(step.name, held)
        if check == "ticket-open":
            return self.issue_state(ticket).out.strip() == "open", ""
        if check == "ticket-closed":
            return self.issue_state(ticket).out.strip() == "closed", ""
        if check == "tree-changed":
            return self.tree_of_job() != "", ""
        if check == "tree-clean":
            return self.tree_of_job() == "", ""
        if check == "new-commit":
            head = self.git(self.job_worktree, "rev-parse", "HEAD").out.strip()
            return head != self.ticket_base, ""
        return False, "no check is named {}\n".format(check)

    # --- the Edit an axis made -----------------------------------------------

    # Every axis runs `git add -N .` first, so a reading without it reads that command as an edit.
    def reading_of_job(self):
        self.git(self.job_worktree, "add", "-N", ".")
        named = self.git(self.job_worktree, "diff", "HEAD", "--name-only", "-z").out
        return {path: digest(Path(self.job_worktree) / path)
                for path in named.split("\0") if path}

    # An Edit and not a check, so an axis doing its job never stops the loop.
    def record_edit(self, ticket, axis, before):
        changed = changed_between(before, self.reading_of_job())
        said = "changed " + (", ".join(changed) if changed else "nothing")
        written(self.step_file(ticket, axis, "edit"), said + "\n")
        self.say("EDIT  #{} {:<13}{}".format(ticket, axis, said))

    # --- running one step ----------------------------------------------------

    # The loop picks only open tickets, so a rerun would skip a closed one.
    def reopen(self, ticket):
        # A read that failed is not a ticket that is open, and guessing it is loses the ticket.
        state = self.issue_state(ticket)
        if state.status != 0:
            self.say("WARN  #{} would not be read, so it may still be closed and a rerun skip "
                     "it.".format(ticket))
            return
        if state.out.strip() != "closed":
            return
        if self.gh("issue", "reopen", ticket).status == 0:
            self.say("      #{} is open again, so a rerun starts from it".format(ticket))
        else:
            self.say("WARN  #{} did not reopen. Reopen it by hand, or a rerun will skip it."
                     .format(ticket))

    # The hint only where a Denial was listed, since a stop with another cause needs another fix.
    def stop_step(self, ticket, step, reason, see, result=None):
        self.reopen(ticket)
        said = "FAIL  #{} step {} {}. Its worktree is at {}. See {}".format(
            ticket, step, reason, self.job_worktree, see)
        named = denials(result) if result is not None else []
        if not named:
            return stop(said)
        for denial in named:
            said += "\n      Denial: " + denial
        return stop(said + "\n      If one of these Denials stopped the step, rerun with "
                    "SPEC_LOOP_PERMISSION_MODE=bypassPermissions")

    def run_step(self, ticket, step, *rest):
        held = self.step_file(ticket, step.name, "json")
        reasons = self.step_file(ticket, step.name, "err")
        self.say("STEP  #{} {:<13}{}".format(
            ticket, step.name,
            progress_suffix(self.position, self.ticket_count, self.mean_seconds)))

        # Built before the session starts, so two axes out of three never reach the fix step.
        prompt, reason = self.step_body(ticket, step)
        if prompt is None:
            written(reasons, reason)
            raise self.stop_step(ticket, step.name, "was short of a review axis report", reasons)

        # Only the session and its Nudges write between the readings, so the Edit is that axis alone.
        before = self.reading_of_job() if step.name in REVIEW_STEPS else None
        try:
            self.run_sessions(ticket, step, prompt, rest, held, reasons)
        finally:
            if before is not None:
                self.record_edit(ticket, step.name, before)

    # A Nudge resumes the step's own Session, so it keeps what that Session already did.
    def run_sessions(self, ticket, step, prompt, rest, held, reasons):
        opening = [str(a) for a in rest] or self.new_session()
        session = opening[-1]
        ran = self.claude_p(prompt, *opening)
        written(reasons, ran.err)
        nudge = 0
        while True:
            written(held, ran.out)
            if ran.status != 0:
                raise self.stop_step(ticket, step.name, "exited non-zero",
                                     "{} and {}".format(reasons, held), held)
            failed = self.failed_checks(ticket, step, held, reasons)
            if not failed:
                return
            if nudge == NUDGES:
                raise self.stop_step(
                    ticket, step.name, "failed check {} after {} Nudges".format(failed[0], NUDGES),
                    "{} and {}".format(held, reasons), held)
            nudge += 1
            self.say("NUDGE #{} {:<13}{} of {}, failed {}".format(
                ticket, step.name, nudge, NUDGES, " ".join(failed)))
            ran = self.claude_p("".join(owed(step, check) for check in failed) + NUDGE_TAIL,
                                "--resume", session)
            appended(reasons, ran.err)

    # Every check runs every time, since a Nudge that mends one thing can break another.
    def failed_checks(self, ticket, step, held, reasons):
        failed = []
        for check in step.checks.split():
            passed, reason = self.check_passes(ticket, step, check, held)
            if reason:
                appended(reasons, reason)
            if passed:
                continue
            if check not in NUDGED_BY:
                raise self.stop_step(ticket, step.name, "failed check " + check,
                                     "{} and {}".format(held, reasons), held)
            failed.append(check)
        return failed

    # --- the step the driver runs itself -------------------------------------

    def suite_heard(self, ticket, held):
        def heard(outcome, at):
            appended(held, "--- suite run {}\n{}".format(at, outcome.said))
            self.say("      #{} suite run {} {}".format(ticket, at, suite_verdict(outcome, at)))
        return heard

    # Red is handed back rather than raised, so the caller chooses between a circuit and a stop.
    def run_suite_step(self, ticket, step):
        held = self.step_file(ticket, step.name, "out")
        self.say("STEP  #{} {:<13}{}".format(
            ticket, step.name,
            progress_suffix(self.position, self.ticket_count, self.mean_seconds)))

        # The red that sent the loop round is why it ran again, so a second run adds to the record.
        if self.red_suite is None:
            written(held, "")
        outcome = Suite(self.runner, self.job_worktree).run(self.suite_heard(ticket, held))

        # A machine short of what the checks need is nothing a Session could mend, so none is asked.
        if not outcome.ready:
            appended(held, "--- the suite could not start\n{}".format(outcome.said))
            raise stop("ABORT #{} failed check suite-can-run, so no Session was asked to mend "
                       "it: {}\n      Its worktree is at {}. See {}".format(
                           ticket, outcome.said.strip(), self.job_worktree, held))
        self.green_suite = outcome if outcome.passed else None
        return None if outcome.passed else outcome

    # --- getting started -----------------------------------------------------

    def preflight(self):
        if not self.runner.found("gh"):
            raise stop("ABORT gh is not installed")
        if not self.runner.found("claude"):
            raise stop("ABORT claude is not on PATH")
        if self.gh("auth", "status").status != 0:
            raise stop("ABORT gh is not authenticated. Run: gh auth login")

        self.repo = self.gh("repo", "view", "--json", "nameWithOwner",
                            "--jq", ".nameWithOwner").out.strip()
        self.me = self.gh("api", "user", "--jq", ".login").out.strip()

        state = self.issue_state(self.spec)
        if state.status != 0:
            raise stop("ABORT cannot read {}#{}".format(self.repo, self.spec))
        self.spec_title = self.issue_field(self.spec, ".title").out.strip()
        if state.out.strip() != "open":
            raise stop("ABORT spec #{} is {}. The loop needs it open.".format(
                self.spec, state.out.strip()))

        # --paginate runs --jq once per page, so a length would count only the first hundred.
        self.ticket_count = len(listed(self.sub_issues(".[].number").out))
        if self.ticket_count == 0:
            raise stop("ABORT spec #{} has no sub-issues. Run /skillworks:to-tickets first.".format(self.spec))

    # --- the dry run ---------------------------------------------------------

    def landing_plan(self):
        out, err = io.StringIO(), io.StringIO()
        land_ticket.main(["--plan"], self.runner, out, err)
        return listed(out.getvalue())

    def dry_run(self):
        self.say("DRY   repo={}  me={}".format(self.repo, self.me))
        self.say("DRY   spec #{}: {}".format(self.spec, self.spec_title))

        # Asked of the scripts that do the work, so the plan cannot drift from the run.
        landing = self.landing_plan()
        if not landing:
            raise stop("ABORT the landing steps would not be read, so the plan would be short of "
                       "them.")

        tickets = self.sub_issues('.[] | "\\(.number)\\t\\(.state)\\t\\(.title)"')

        # Gathered whole and printed once, so a step that cannot be planned can still stop the run.
        plan = ""
        for line in listed(tickets.out):
            number, state, title = columns(line)
            plan += "  #{} [{}] {}\n".format(number, state, title)
            if state != "open":
                continue

            status, said, _ = self.worktree("plan", "ticket-" + number)
            told = said.strip().split("\t")
            if status != 0 or len(told) != 2:
                raise stop("ABORT #{} could not be told where it would be built.".format(number))
            plan += plan_line("worktree", told[0])
            plan += plan_line("branch", told[1])

            for step in STEPS:
                if not step.session:
                    plan += plan_line(step.name, step.asks, step.checks)
                    continue
                call = 'claude -p "{}"'.format(step.asks.format(number))
                if step.resumes:
                    call += " --resume <build session>"
                else:
                    call += " --session-id <new id>"
                plan += plan_line(step.name, call, step.checks)
                nudged = nudged_on(step)
                if nudged:
                    plan += "                   nudges: up to {}, on {}\n".format(
                        NUDGES, " ".join(nudged))

            for step in landing:
                named, what, checks = columns(step)
                plan += plan_line(named, what, checks)

        self.wrote(plan)
        self.say("DRY   no session was run, and nothing reached the remote")

    # --- the restart ---------------------------------------------------------

    # Kept as branches rather than refused, and said before the stop, so nothing is lost.
    def keep_leftovers(self):
        status, leftovers, warnings = self.worktree("keep")
        # A keep that failed has had its whole stderr read out already.
        if status == 0:
            for line in listed(warnings):
                if line.startswith("warn  "):
                    self.say("WARN  " + line[len("warn  "):])
        for line in listed(leftovers):
            job, branch, held = columns(line)
            if held == "held":
                self.say("KEPT  {} held uncommitted work. The whole attempt is on branch {}".format(
                    job, branch))
            else:
                self.say("KEPT  {} held nothing uncommitted. Its attempt is on branch {}".format(
                    job, branch))
        if status != 0:
            raise stop("ABORT spec #{} has a worktree group that would not be kept. Nothing was "
                       "started.".format(self.spec))

    # --- picking the next ticket ---------------------------------------------

    def assignees_besides_me(self, ticket):
        return self.issue_field(ticket, '[.assignees[].login] | map(select(. != "{}")) | '
                                        'join(",")'.format(self.me)).out.strip()

    def next_ticket(self, open_tickets):
        for number in open_tickets:
            # blocked_by counts OPEN blockers only. See ticket-state-guardrails.md.
            blocked = self.issue_field(
                number, '.issue_dependencies_summary.blocked_by // "missing"').out.strip()
            if blocked in ("", "missing"):
                raise stop("ABORT #{} reports no issue_dependencies_summary. Refusing to "
                           "guess.".format(number))
            if blocked != "0":
                continue
            if self.assignees_besides_me(number):
                continue
            return number
        return ""

    # There is no compare-and-swap here, so this detects a race rather than preventing one.
    def claimed(self, ticket):
        self.gh("issue", "edit", ticket, "--add-assignee", "@me")
        self.wait(CLAIM_WAIT)
        others = self.assignees_besides_me(ticket)
        if not others:
            return True
        self.gh("issue", "edit", ticket, "--remove-assignee", "@me")
        self.say("SKIP  #{} claimed by {}".format(ticket, others))
        return False

    # --- one ticket ----------------------------------------------------------

    # One way in for both kinds of step, so the circuit cannot run them differently from the run.
    def run_any_step(self, ticket, step, session):
        if not step.session:
            return self.run_suite_step(ticket, step)
        if step.resumes:
            self.run_step(ticket, step, "--resume", session)
        else:
            self.run_step(ticket, step)
        return None

    # The circuit ends at the suite, so the verdict of its last step is the circuit's own.
    def go_round(self, ticket, session, red):
        self.red_suite = red
        self.say("      #{} the suite went red on every run it was given, so the loop goes "
                 "round once: {}".format(ticket, ", then ".join(CIRCUIT)))
        outcome = None
        for name in CIRCUIT:
            outcome = self.run_any_step(ticket, step_named(name), session)
        return outcome

    def build_ticket(self, ticket):
        session = ""
        for step in STEPS:
            red = self.run_any_step(ticket, step, session)
            # One circuit is the bound, small enough to hold in your head at two in the morning.
            if red is not None and self.red_suite is None:
                red = self.go_round(ticket, session, red)
            if red is not None:
                raise self.stop_step(ticket, step.name, "failed check suite-green",
                                     self.step_file(ticket, step.name, "out"))
            if step.name != "build":
                continue
            held = self.step_file(ticket, "build", "json")
            session = str(field(held, "session_id"))
            if not session:
                raise stop("FAIL  #{} step build gave no session id. See {}".format(ticket, held))
        return session

    # The session that wrote the ticket goes too, to resolve what its work conflicts with.
    def land(self, ticket, session):
        held = self.step_file(ticket, "land", "out")
        said = io.StringIO()
        landed = land_ticket.main([self.job_worktree, ticket, session], self.runner, said, said)
        written(held, said.getvalue())
        self.say(said.getvalue().rstrip("\n"))
        if landed != 0:
            # The finishing step closed it, and the work it closed on never reached the remote.
            self.reopen(ticket)
            raise stop("FAIL  #{} did not reach main. Its worktree is at {}. See {}".format(
                ticket, self.job_worktree, held))

    def run_ticket(self, ticket):
        self.say("START #{} {}".format(ticket, self.issue_field(ticket, ".title").out.strip()))

        self.red_suite = None
        self.green_suite = None
        self.job_worktree = self.opened("ticket-" + ticket)
        if not self.job_worktree:
            raise stop("FAIL  #{} got no worktree to be built in.".format(ticket))
        self.ticket_base = self.git(self.job_worktree, "rev-parse", "HEAD").out.strip()
        started = time.time()

        self.land(ticket, self.build_ticket(ticket))
        landed_at = self.git(self.job_worktree, "rev-parse", "--short", "HEAD").out.strip()

        # A ticket that failed never gets here, so a worktree left behind means a stop.
        if self.worktree("close", "ticket-" + ticket)[0] != 0:
            raise stop("FAIL  #{} landed, but its worktree at {} would not go.".format(
                ticket, self.job_worktree))

        # A skipped ticket never reaches here, so nobody else's work is in the mean.
        self.timed_seconds += int(time.time() - started)
        self.timed_tickets += 1
        self.mean_seconds = self.timed_seconds // self.timed_tickets
        self.say("DONE  #{}  {}".format(ticket, landed_at))

    # --- the drift check -----------------------------------------------------

    def check_drift(self, base):
        self.say("DRIFT all tickets closed. Checking the result against spec #{}.".format(
            self.spec))

        # The main checkout was never pulled, so only a fresh worktree holds the finished work.
        self.job_worktree = self.opened("drift")
        if not self.job_worktree:
            raise stop("FAIL  the drift check got no worktree to run in.")

        ran = self.claude_p(PLUGIN + "spec-drift {} {}".format(self.spec, base))
        written(self.log_dir / "drift.json", ran.out)
        written(self.log_dir / "drift.err", ran.err)
        if ran.status != 0:
            self.say("WARN  drift check exited non-zero. See {}".format(
                self.log_dir / "drift.err"))

        if self.tree_of_job():
            raise stop("FAIL  drift check left uncommitted changes in {}.".format(
                self.job_worktree))
        if self.worktree("close", "drift")[0] != 0:
            raise stop("FAIL  the drift worktree at {} would not go.".format(self.job_worktree))

    # --- the whole run -------------------------------------------------------

    def run(self, dry):
        # No guard on the branch or on the edits: nothing is ever built in this checkout.
        found = self.git(Path.cwd(), "rev-parse", "--show-toplevel")
        if found.status != 0:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            raise stop("ABORT {} is not a git worktree.".format(Path.cwd().as_posix()))
        self.root = Path(found.out.strip())
        self.log_dir = self.root / ".spec-loop" / self.spec
        self.log = self.log_dir / "loop.log"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.preflight()
        if dry:
            return self.dry_run()

        self.keep_leftovers()

        # Every worktree is cut from origin/main, so the ref has to be current first.
        if not fetch_origin(self.runner, self.root.as_posix(), self.err):
            raise stop("ABORT could not fetch from origin")

        # Written once, so a resumed run still measures from where the first run started.
        held = self.log_dir / "base.sha"
        if not held.is_file():
            written(held, self.git(self.root, "rev-parse", "origin/main").out)
        base = held.read_text(encoding="utf-8").strip()

        self.say("LOOP  spec #{} from {} ({})".format(self.spec, base, self.repo))

        while True:
            open_tickets = listed(
                self.sub_issues('.[] | select(.state=="open") | .number').out)
            ticket = self.next_ticket(open_tickets)
            if not ticket:
                if not open_tickets:
                    break
                raise stop("STUCK {} ticket(s) still open but none are startable (blocked, or "
                           "claimed by someone else).".format(len(open_tickets)))

            if not self.claimed(ticket):
                continue

            # Counts closed tickets, not this run's, so a rerun starts at its real place.
            self.position = self.ticket_count - len(open_tickets) + 1
            self.run_ticket(ticket)

        self.check_drift(base)
        self.say("END   spec #{} complete. Every ticket is on main.".format(self.spec))
        self.say("      Review it with: git log --oneline {}..origin/main".format(base))


def arguments(argv):
    spec = argv[0] if len(argv) > 0 else ""
    rest = argv[1:]
    if not is_a_number(spec):
        raise misuse(USAGE)
    if rest and rest != ["--dry-run"]:
        raise misuse(USAGE)
    return spec, bool(rest)


def main(argv, runner, out, err, wait):
    loop = None
    try:
        spec, dry = arguments(argv)
        loop = Loop(runner, spec, out, err, wait)
        loop.run(dry)
        return 0
    except Stop as stopped:
        if stopped.status == MISUSED or loop is None:
            err.write(stopped.said)
        else:
            loop.say(stopped.said)
        return stopped.status


if __name__ == "__main__":
    # Windows adds a carriage return, which would reach the log as well as the terminal.
    sys.stdout.reconfigure(newline="\n")
    sys.stderr.reconfigure(newline="\n")
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr, time.sleep))
