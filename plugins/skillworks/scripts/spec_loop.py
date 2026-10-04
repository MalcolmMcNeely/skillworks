# /// script
# dependencies = ["filelock>=3.16"]
# ///
#
# Drive one spec's tickets to done, sequentially, one fresh Claude session each.
# Each ticket is built in a throwaway worktree of its own, cut from the newest
# Target branch, and lands on the remote the moment it passes. The main checkout
# is never worked in, so it stays usable for the whole run.
#
#   spec-loop <spec-issue-number> [--dry-run] [--bypass]
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
# Every question about a spec or a ticket goes to the Tracker that loop.json names.
#
# Env:
#   SPEC_LOOP_PERMISSION_MODE   passed to `claude -p` (default: acceptEdits); writes under .claude/ need `--bypass`

import hashlib
import io
import json
import os
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, NamedTuple

import land_ticket
import ticket_worktree
from count.gap_ticket import gap_ticket
from count.gaps import count_verdicts, gap_said
from count.items import read_items, with_readme
from count.rename_ticket import rename_ticket
from count.renames import (RENAMES, count_renames, has_no_glossary_word, name_of,
                           read_rename_verdicts, read_renames, unmade_said)
from count.verdicts import VERDICTS, read_verdicts
from fetch_origin import fetch_origin
from output.streams import speaking_any_character
from runner import MAY_READ_THE_PLUGIN, Subprocess, session_changes
from seed_steering import missing_steering
from steering.readme_surface import readme_surface_of
from steering.rule_imports import missing_import
from steering.target_branch import in_spec_mode, target_branch_for, tracker_for
from stop import MISUSED, REFUSED, Stop, is_a_number, misuse
from suite import Suite
from tracker.reading import FLAKES, listed
from tracker.spec_commits import spec_commits

USAGE = "usage: spec-loop <spec-issue-number> [--dry-run] [--bypass]\n"

FLAGS = ("--dry-run", "--bypass")

BYPASS_MODE = "bypassPermissions"

# gh asks at a terminal, and a loop run has nobody at one.
GH_QUIET = {"GH_PROMPT_DISABLED": "1"}

FULL_RUN = ticket_worktree.FULL_RUN


class Step(NamedTuple):
    name: str
    # The ticket number goes in the one placeholder; a driver's own step holds a description.
    asks: str
    checks: str
    # A resumed step would read the one before it, so each axis and the sweep starts fresh.
    resumes: bool
    # False where the driver does the work, so nothing asks a Session for a result it never gave.
    session: bool = True
    # Empty only where the driver does the work, because no Session is there to be told anything.
    told: str = ""


# What a Session that changes nothing must leave on the Tracker, so one that stopped short is Nudged.
class Recorded(NamedTuple):
    check: str
    holds: Callable[[], object]
    owed: str


# The skills load from the Plugin, and Claude Code names a Plugin skill with the Plugin in front.
PLUGIN = "/skillworks:"

AXIS_CHECKS = "no-error command-loaded ticket-open axis-reported"

# One list, read by the plan and by the run, so the two cannot drift apart.
REVIEW_STEPS = ("standards", "spec", "architecture")

# Driver text and in no skill, because nobody answers only in the loop, and a skill run by hand asks.
BLOCKED_ONLY_WHEN = (
    "Begin your report with a line that starts with `BLOCKED` only when you cannot do the work: a "
    "tool call was denied and no allowed way exists, or the ticket has nothing left to build.")

# Only a step that builds may choose, so a judge cannot choose its way out of a finding.
TOLD_TO_BUILD = (
    "Nobody will answer a question in this loop. A Choice is only for what the ticket and the spec "
    "leave open. A point either of them names is not open, and a part that only touches the point "
    "does not open it. Where they leave more than one way open, pick one that your step allows and "
    "carry on, and write one line that starts with `CHOSE`, with what you chose and why. Where two "
    "parts that both name one point disagree, take the stricter one and carry on, and write one "
    "line that starts with `DEPARTS`, naming both parts and why. A question the ticket tells you to "
    "ask a person is a Choice: answer it, and write a `CHOSE` line. Where a check needs a real "
    "device such as a printer or a phone, a real outside account or service, or a person's eyes on "
    "the screen or the page, carry on, and write one line that starts with `HAND CHECK`, with the "
    "check and how a person runs it. No Session has those three things, and nothing else is a Hand "
    "check. The Suite is never one, because the driver runs it. A question to a person is never "
    "one, because it is a Choice. " + BLOCKED_ONLY_WHEN)

TOLD_TO_JUDGE = (
    "Nobody will answer a question in this loop. Where the change differs from the ticket or the "
    "spec, a review reports a finding and a check gives a Verdict. Write no line that starts with "
    "`CHOSE`, `DEPARTS` or `HAND CHECK`. " + BLOCKED_ONLY_WHEN)

# The build already answered the ticket's question, so a ticket held open for it never Lands.
TOLD_TO_FINISH = (
    "Nobody will answer a question in this loop. A question the ticket puts to a person never "
    "keeps the ticket open: the build answered it, so close the ticket, and put the question and "
    "the build's answer in the Closing note. Where you find a fault you may not fix, carry on, and "
    "write one line that starts with `DEPARTS`, with the fault and why you may not fix it. Write no "
    "line that starts with `CHOSE` or `HAND CHECK`. " + BLOCKED_ONLY_WHEN)

FIX_HANDED = (
    "The build wrote each line below for this ticket, and the list at the end of the run already "
    "holds it. Write a line that starts with `CHOSE`, `DEPARTS` or `HAND CHECK` only for a Choice, "
    "a Departure or a Hand check that is not below.")

SPEC_HANDED = (
    "The build wrote each `DEPARTS` line below for this ticket. Judge each one as your axis file "
    "says under Judging a Departure.")

DRIFT_HANDED = (
    "A build of this spec wrote each `DEPARTS` line below, in this run or an earlier one. Judge each "
    "one as the skill says under Judging a Departure.")

STEPS = (
    (Step("build", PLUGIN + "implement {} --stop-after-tests",
          "no-error command-loaded ticket-open tree-changed", False, told=TOLD_TO_BUILD),)
    + tuple(Step(axis, PLUGIN + "review-" + axis + " {}", AXIS_CHECKS, False, told=TOLD_TO_JUDGE)
            for axis in REVIEW_STEPS)
    + (Step("fix", PLUGIN + "implement {} --fix", "no-error command-loaded ticket-open", True,
            told=TOLD_TO_BUILD),
       Step("sweep", PLUGIN + "comment-sweep", "no-error command-loaded ticket-open", False,
            told=TOLD_TO_JUDGE),
       Step("suite", "the whole suite, as the Suite file names it",
            "suite-can-run suite-green", False, session=False),
       Step("finish", PLUGIN + "implement {} --finish",
            "no-error command-loaded new-commit ticket-trailer tree-clean ticket-closed", True,
            told=TOLD_TO_FINISH))
)

# A check that proves the work was done. One that proves the Session could run never earns a Nudge.
NUDGED_BY = ("axis-reported", "tree-changed", "new-commit", "ticket-trailer", "tree-clean",
             "ticket-closed")

# Enough for a Session that stopped short, and few enough that a stuck one stops where it can be read.
NUDGES = 2

NUDGE_BACKGROUND = (
    "Any command you left in the background was stopped when your last turn ended, so its output "
    "is not complete. Run it again in the foreground.\n")

NUDGE_BLOCKED = ("Begin your answer with a line that starts with `BLOCKED` only when you cannot do "
                 "the work.\n")

# The tail follows the words the step was told, so a Nudge never invites a Choice from a judge.
NUDGE_TAILS = {
    TOLD_TO_BUILD: NUDGE_BACKGROUND + (
        "Nobody will answer a question. If you put a choice to a person, make it yourself, within "
        "what this step allows, write a `CHOSE` line, and do what is owed. ") + NUDGE_BLOCKED,
    TOLD_TO_JUDGE: NUDGE_BACKGROUND + (
        "Nobody will answer a question. If you put a choice to a person, report it as a finding, "
        "or, where your step is a check, give the Verdict, and do what is owed. Write no line that "
        "starts with `CHOSE`, `DEPARTS` or `HAND CHECK`. ") + NUDGE_BLOCKED,
    TOLD_TO_FINISH: NUDGE_BACKGROUND + (
        "Nobody will answer a question. A question the ticket puts to a person never keeps the "
        "ticket open: the build answered it, so close the ticket, with the question and the "
        "build's answer in the Closing note, and do what is owed. ") + NUDGE_BLOCKED,
}

# The command keeps Proofs the driver reads, so the Suite step after runs only what changed.
SUITE_BY_COMMAND = (
    "\n\nWhen you check your work against the Suite, run `skillworks-suite`, and never the test "
    "commands the Suite file names. In this loop the driver runs the whole Suite as a step of its "
    "own.")

# Read only at the start of a line, so a Session that mentions one in passing names none.
# In the order the list shows them, so a Departure is the first thing a developer reads.
LISTED_OPENINGS = (("DEPARTS", "DEPRT", "Departure", "Departures", "wrote"),
                   ("CHOSE", "CHOSE", "Choice", "Choices", "made"),
                   ("HAND CHECK", "HAND ", "Hand check", "Hand checks", "named"))

# Nobody is at a terminal to approve the slices, and the log holds only the Session's last message.
CUT_UNATTENDED = (
    "\n\nSkip the approval questions. End with the breakdown you showed, as your last message, "
    "so the loop log holds it.")

CUT_RECORDED = "tickets-filed"
REPORT_RECORDED = "report-recorded"
NEW_REPORT_RECORDED = "new-report-recorded"

UNCUT_NUMBER = "<ticket>"
UNCUT_JOB_NUMBER = "UNCUT"

# A Surface is named in words with spaces between, so a space alone cannot part two items.
ITEM_SEPARATOR = ", "

# The sweep follows the fix, because the fix writes and a sweep has to follow whatever wrote last.
CIRCUIT = ("fix", "sweep", "suite")


def nudged_on(step):
    return [check for check in step.checks.split() if check in NUDGED_BY]


def heading_of(axis):
    return "## " + axis[0].upper() + axis[1:]


def owed(tracker, ticket, step, check):
    if check == "axis-reported":
        return ("You have not written your report under the heading {}. Write it, with your "
                "findings or a statement that you found none.\n".format(heading_of(step.name)))
    if check == "tree-changed":
        return ("You have changed nothing in the worktree. Build what ticket {} asks, and leave "
                "the change uncommitted.\n".format(tracker.trailer(ticket)))
    if check == "new-commit":
        return ("You have not committed the work. Commit it, with Ticket: {} in the message's "
                "trailer.\n".format(tracker.trailer(ticket)))
    if check == "ticket-trailer":
        return ("Git reads no Ticket: {0} trailer in a commit you made. Git reads trailers only "
                "from the last paragraph of the message, so put Ticket: {0} in that paragraph, "
                "with no blank line between it and the other trailers, and amend the commit.\n"
                .format(tracker.trailer(ticket)))
    if check == "tree-clean":
        return ("The worktree still holds uncommitted changes. Commit them or remove them, so "
                "the tree is clean.\n")
    if check == "ticket-closed":
        return tracker.close_asked(ticket)
    return "The check {} has not passed.\n".format(check)


def step_named(name):
    return next(step for step in STEPS if step.name == name)


# Not `refusal`: that writes straight to stderr, and what the loop says goes to the log too.
def stop(said):
    return Stop(REFUSED, said)


# The stop that came first is still why the loop ended, so a later one carries it along.
def after(stopped, first):
    if first is None:
        return stopped
    return stop("{}\n      The loop had already stopped: {}".format(stopped.said, first.said))


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


# The first line alone, so a Session that quotes the word lower in its report is not Blocked.
def blocked_line(path):
    for line in str(field(path, "result")).split("\n"):
        if line.strip():
            return line if line.startswith("BLOCKED") else ""
    return ""


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


# Enough to show what a Session was denied, and few enough that a passing step stays short.
DENIALS_SHOWN = 3


# A result that is not JSON is kept as it came, so the Journal holds what a broken Session said.
def as_kept(text):
    try:
        return json.loads(text)
    except ValueError:
        return text


def lines_opening(path, opening):
    return [line for line in str(field(path, "result")).split("\n") if line.startswith(opening)]


STAMP_FORM = "%Y-%m-%d %H:%M:%S"


def stamp():
    return datetime.now(timezone.utc).strftime(STAMP_FORM)


def written(path, text):
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def appended(path, text):
    with Path(path).open("a", encoding="utf-8", newline="\n") as file:
        file.write(text)


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


# A landing can wait on the Turn through another loop's suite, so each line passes on as it ends.
class Lines:
    def __init__(self, heard):
        self.heard = heard
        self.held = ""

    def write(self, said):
        *ended, self.held = (self.held + said).split("\n")
        for line in ended:
            self.heard(line)
        return len(said)

    def flush(self):
        pass

    def end(self):
        if self.held:
            self.heard(self.held)
            self.held = ""


def how_many(count, word, words):
    return "{} {}".format(count, word if count == 1 else words)


def in_words(names):
    return names[0] if len(names) == 1 else "{} and {}".format(", ".join(names[:-1]), names[-1])


def handed(heading, preface, lines):
    if not lines:
        return ""
    return "\n\n## {}\n\n{}\n\n{}\n".format(heading, preface, "\n".join(lines))


def contradicts_said(verdict):
    return verdict.item + (": " + verdict.reason if verdict.reason else "")


def nudges_line(checks):
    return "                   nudges: up to {}, on {}\n".format(NUDGES, checks)


def plan_line(name, what, checks=""):
    said = "      {:<12} {}\n".format(name, what)
    if checks:
        said += "                   checks: {}\n".format(checks)
    return said


def told_plan():
    named = {told: [step.name for step in STEPS if step.told == told]
             for told in (TOLD_TO_BUILD, TOLD_TO_JUDGE, TOLD_TO_FINISH)}
    named[TOLD_TO_BUILD].append("cut")
    named[TOLD_TO_JUDGE] += ["drift", "re-check", "names", "name-re-check"]
    return "  each Session above is told, after its command\n" + "".join(
        "    {}:\n    {}\n".format(", ".join(steps), told) for told, steps in named.items())


class Loop:
    def __init__(self, runner, spec, out, err, wait, permission_mode):
        self.runner = runner
        self.spec = spec
        self.out = out
        self.err = err
        self.wait = wait
        self.permission_mode = permission_mode
        self.log_dir = Path(".spec-loop") / spec
        self.log = self.log_dir / "loop.log"
        self.journal = self.log_dir / "journal.jsonl"

        self.root = Path.cwd()
        self.target = ""
        self.spec_mode = False
        self.tracker = None
        self.spec_title = ""
        self.ticket_count = 0
        # Read before the first ticket, so the count judges the report by the spec the run began on.
        self.items = None
        self.drift_read = None
        self.names_read = None

        self.job_worktree = ""
        self.ticket_base = ""
        self.position = 0

        # Not being None is also the record that the loop has already been round.
        self.red_suite = None

        # The driver read this one, so the finishing Session names it rather than proving it again.
        self.green_suite = None
        self.flakes = []

        # Every step's and not one ticket's, so the note on the spec names each Flake of the run.
        self.run_flakes = []
        self.left_full_run_tree = ""

        self.listed = []
        self.built = {}

        # This run's alone, so a rerun proves the Target branch again only when it lands something.
        self.landed = []

        # Nothing is read from an earlier run, so a rerun grows a mean of its own.
        self.timed_tickets = 0
        self.timed_seconds = 0
        self.mean_seconds = None

    # The log first, so a line already seen on the terminal is always in the log too.
    def wrote(self, said):
        appended(self.log, said)
        self.out.write(said)

    def say(self, said):
        self.wrote("{} {}\n".format(stamp(), said))

    def named(self, ticket):
        return self.tracker.named(ticket)

    def spec_named(self):
        return self.tracker.spec_named(self.spec)

    # --- the programs this reaches -------------------------------------------

    # A pull request is GitHub's own and no Tracker's, so it is the one thing asked of gh here.
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

    # Only a Session started for a ticket names one, so the hook tags no commit of the Cut or a check.
    def claude_p(self, prompt, *rest, ticket=None):
        rest = [str(a) for a in rest] or self.new_session()
        return self.runner.run(
            ["claude", "-p", prompt] + rest
            + ["--permission-mode", self.permission_mode, "--output-format", "json"] + MAY_READ_THE_PLUGIN,
            self.job_worktree,
            session_changes(self.tracker.trailer(ticket) if ticket else None))

    # A path comes back on stdout, so a reason takes stderr, and the log too for a background run.
    def worktree(self, command, job=""):
        out, err = io.StringIO(), io.StringIO()
        status = ticket_worktree.main(
            [command, self.root.as_posix(), self.spec, job], self.runner, out, err, self.wait,
            self.target)
        if status != 0:
            self.err.write(err.getvalue())
            appended(self.log, err.getvalue())
        return status, out.getvalue(), err.getvalue()

    def opened(self, job):
        status, said, _ = self.worktree("open", job)
        if status != 0 or not said.strip():
            return ""
        return said.strip()

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
                "run no tests yourself. Name what follows in the Closing note: the checks that "
                "ran as what proved the work, and each check whose line says it did not run beside "
                "the Proof it names, which an earlier pass on the same inputs made.\n\n{}\n{}").format(
                    self.green_suite.said.rstrip("\n"), self.flakes_report())

    def flakes_report(self):
        if not self.flakes:
            return ""
        return ("\n## Flakes\n\nEach check below went red and then passed, so the suite counted it "
                "green. Name each Flake in the Closing note, with the file that keeps its red "
                "output.\n\n{}").format(
                    "".join("- {}: {}\n".format(check, held) for check, held in self.flakes))

    # The Tracker names the ticket, so a number local to its spec reaches the Session with its spec.
    def asks(self, step, ticket):
        return step.asks.format(self.tracker.reference(ticket))

    # The checks and the plan read `asks`, so nothing added below the command line reaches them.
    def step_body(self, ticket, step):
        asked = self.asks(step, ticket) + SUITE_BY_COMMAND + "\n\n" + step.told
        if step.name == "finish":
            return asked + self.suite_report(), ""
        if step.name == "spec":
            return asked + self.build_departures(ticket), ""
        if step.name != "fix":
            return asked, ""
        reports, reason = self.review_reports(ticket)
        if reports is None:
            return None, reason
        said = ("{}\n\nThe three review axes have run. Their reports follow, each with the Edit "
                "that axis made.\n{}").format(asked, reports.rstrip("\n"))
        said += self.build_lines(ticket)
        if self.red_suite is not None:
            said += ("\n\n## The suite went red\n\nThe driver ran it as often as the Suite file "
                     "asks, and it went red every time. What it said follows.\n\n{}\n").format(
                         self.red_suite.said.rstrip("\n"))
        return said, ""

    # Handed on, so the list at the end of the run shows a line the fix carries forward only once.
    def build_lines(self, ticket):
        return handed("The build wrote these lines", FIX_HANDED, self.built.get(ticket, []))

    # The spec review alone judges whether the build kept to the rule for taking the stricter part.
    def build_departures(self, ticket):
        departures = [line for line in self.built.get(ticket, []) if line.startswith("DEPARTS")]
        return handed("The build wrote these Departures", SPEC_HANDED, departures)

    # Read from the Journal, so a Departure built in a run that stopped still keeps the spec open.
    def spec_departures(self):
        departures = []
        if self.journal.is_file():
            for line in listed(self.journal.read_text(encoding="utf-8")):
                entry = json.loads(line)
                if entry.get("step") == "build":
                    departures += [d for d in entry.get("departures", []) if d not in departures]
        return handed("The builds wrote these Departures", DRIFT_HANDED, departures)

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
            command, _, args = self.asks(step, ticket).partition(" ")
            return self.command_loaded(str(field(held, "session_id")), command, args)
        if check == "axis-reported":
            return self.axis_reported(step.name, held)
        if check == "ticket-open":
            return self.tracker.state_in(ticket, self.job_worktree) == "open", ""
        if check == "ticket-closed":
            return self.tracker.state_in(ticket, self.job_worktree) == "closed", ""
        if check == "tree-changed":
            return self.tree_of_job() != "", ""
        if check == "tree-clean":
            return self.tree_of_job() == "", ""
        if check == "new-commit":
            head = self.git(self.job_worktree, "rev-parse", "HEAD").out.strip()
            return head != self.ticket_base, ""
        if check == "ticket-trailer":
            return self.commits_carry_the_trailer(ticket), ""
        return False, "no check is named {}\n".format(check)

    # Land turns down a commit whose trailer git cannot read, and by then no Session is left to mend it.
    def commits_carry_the_trailer(self, ticket):
        said = self.git(self.job_worktree, "log", "--format=%(trailers:key=Ticket,valueonly)%x00",
                        self.ticket_base + "..HEAD").out
        return all("".join(c for c in named.strip().split("\n")[0] if not c.isspace())
                   == self.tracker.trailer(ticket)
                   for named in said.split("\0")[:-1])

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
        self.say("EDIT  {} {:<13}{}".format(self.named(ticket), axis, said))

    # --- running one step ----------------------------------------------------

    # The loop picks only open tickets, so a rerun would skip a closed one.
    def reopen(self, ticket):
        # A read that failed is not a ticket that is open, and guessing it is loses the ticket.
        state = self.tracker.state(ticket)
        if state is None:
            self.say("WARN  {} would not be read, so it may still be closed and a rerun skip "
                     "it.".format(self.named(ticket)))
            return
        if state != "closed":
            return
        if self.tracker.reopen(ticket):
            self.say("      {} is open again, so a rerun starts from it".format(self.named(ticket)))
        else:
            self.say("WARN  {} did not reopen. Reopen it by hand, or a rerun will skip it."
                     .format(self.named(ticket)))

    # The hint only where a Denial was listed, since a stop with another cause needs another fix.
    def stop_naming_denials(self, said, result):
        named = denials(result) if result is not None else []
        if not named:
            return stop(said)
        for denial in named:
            said += "\n      Denial: " + denial
        # The flag and not the env var, because the allow rule `Bash(spec-loop:*)` matches only the flag.
        return stop(said + "\n      If one of these Denials stopped the loop, rerun with "
                    "spec-loop {} --bypass".format(self.spec))

    # Said for a passing result too, so a Denial the Session found a way round still shows.
    def say_denials(self, who, result):
        named = denials(result)
        said = "DENY  {}{}".format(who, how_many(len(named), "Denial", "Denials"))
        if len(named) > DENIALS_SHOWN:
            said += ", and the first {} follow".format(DENIALS_SHOWN)
        for denial in named[:DENIALS_SHOWN]:
            said += "\n      Denial: " + denial
        self.say(said)

    def say_result(self, who, result):
        self.say_denials(who, result)
        listed = []
        for line in str(field(result, "result")).split("\n"):
            for opening, tag, *_ in LISTED_OPENINGS:
                if line.startswith(opening):
                    self.say("{} {}{}".format(tag, who, line))
                    self.listed.append((opening, who + line))
                    listed.append(line)
        return listed

    # Only ever added to, so an attempt a Nudge, a second fix or a rerun came after is still read.
    def add_to_journal(self, ran, held, step, attempt, failed, ticket=None, spec_step=None):
        entry = {"at": stamp(), "ticket": ticket, "spec_step": spec_step, "step": step,
                 "attempt": attempt, "status": ran.status, "failed": failed,
                 "denials": len(denials(held)), "blocked": blocked_line(held) or None,
                 "choices": lines_opening(held, "CHOSE"),
                 "hand_checks": lines_opening(held, "HAND CHECK"),
                 "departures": lines_opening(held, "DEPARTS"), "result": as_kept(ran.out)}
        appended(self.journal, json.dumps(entry) + "\n")

    # Said at a stop as well as at a clean finish, so a Hand check is never lost mid-log.
    def list_what_sessions_wrote(self):
        if not self.listed:
            return
        counts = []
        lines = []
        for opening, _, one, many, verb in LISTED_OPENINGS:
            of_kind = [said for each, said in self.listed if each == opening]
            counts.append("{} {}".format(verb, how_many(len(of_kind), one, many)))
            lines += of_kind
        self.say("LIST  this run {}, {} and {}{}".format(
            *counts, "".join("\n      " + said for said in lines)))

    def stop_step(self, ticket, step, reason, see, result=None):
        self.reopen(ticket)
        return self.stop_naming_denials("FAIL  {} step {} {}. Its worktree is at {}. See {}".format(
            self.named(ticket), step, reason, self.job_worktree, see), result)

    # No Nudge, because one would tell a Session to close a ticket it cannot finish.
    def stop_blocked(self, ticket, step, line, see, result):
        self.reopen(ticket)
        return self.stop_naming_denials("STOP  {} step {} is Blocked: {}\n      Its worktree is at "
                                        "{}. See {}".format(self.named(ticket), step, line,
                                                            self.job_worktree, see), result)

    def run_step(self, ticket, step, *rest):
        held = self.step_file(ticket, step.name, "json")
        reasons = self.step_file(ticket, step.name, "err")
        self.say("STEP  {} {:<13}{}".format(
            self.named(ticket), step.name,
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

    # A Nudge resumes the Session the step's result names, so a finish is not sent to the build's.
    def run_sessions(self, ticket, step, prompt, rest, held, reasons):
        ran = self.claude_p(prompt, *rest, ticket=ticket)
        written(reasons, ran.err)
        nudge = 0
        while True:
            written(held, ran.out)
            listed = self.say_result("{} {:<13}".format(self.named(ticket), step.name), held)
            if step.name == "build":
                self.built.setdefault(ticket, []).extend(listed)
            failed = None
            try:
                if ran.status == 0:
                    failed = self.failed_checks(ticket, step, held, reasons)
            finally:
                self.add_to_journal(ran, held, step.name, nudge, failed, ticket=ticket)
            if ran.status != 0:
                raise self.stop_step(ticket, step.name, "exited non-zero",
                                     "{} and {}".format(reasons, held), held)
            if failed and failed[0] not in NUDGED_BY:
                raise self.stop_step(ticket, step.name, "failed check " + failed[0],
                                     "{} and {}".format(held, reasons), held)
            blocked = blocked_line(held)
            if blocked:
                raise self.stop_blocked(ticket, step.name, blocked,
                                        "{} and {}".format(held, reasons), held)
            if not failed:
                return
            if nudge == NUDGES:
                raise self.stop_step(
                    ticket, step.name, "failed check {} after {} Nudges".format(failed[0], NUDGES),
                    "{} and {}".format(held, reasons), held)
            nudge += 1
            self.say("NUDGE {} {:<13}{} of {}, failed {}".format(
                self.named(ticket), step.name, nudge, NUDGES, " ".join(failed)))
            ran = self.claude_p("".join(owed(self.tracker, ticket, step, check)
                                        for check in failed) + NUDGE_TAILS[step.told],
                                "--resume", field(held, "session_id"), ticket=ticket)
            appended(reasons, ran.err)

    # Every check runs every time, since a Nudge that mends one thing can break another.
    # Blocked is read between the kinds: a Session that never ran fails, and a Blocked one stops.
    # Handed back and not raised, so the Journal keeps what was judged before the loop acts on it.
    def failed_checks(self, ticket, step, held, reasons):
        checks = step.checks.split()
        for check in checks:
            if check in NUDGED_BY:
                continue
            if not self.passes_noting_reason(ticket, step, check, held, reasons):
                return [check]
        if blocked_line(held):
            return []
        return [check for check in checks if check in NUDGED_BY
                and not self.passes_noting_reason(ticket, step, check, held, reasons)]

    def passes_noting_reason(self, ticket, step, check, held, reasons):
        passed, reason = self.check_passes(ticket, step, check, held)
        if reason:
            appended(reasons, reason)
        return passed

    # --- the step the driver runs itself -------------------------------------

    def suite_heard(self, ticket, held):
        def heard(outcome, at):
            appended(held, "--- suite run {}\n{}".format(at, outcome.said))
            self.say("      {} suite run {} {}".format(
                self.named(ticket), at, suite_verdict(outcome, at)))
        return heard

    # A file of its own for each, so a later run, or a later loop on the spec, never writes over one.
    def stamped(self, named):
        named += "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        held = self.log_dir / (named + ".out")
        again = 1
        while held.exists():
            again += 1
            held = self.log_dir / "{}-{}.out".format(named, again)
        return held

    def keep_flake(self, ticket, step, flake):
        return self.keep_flake_output("ticket-{}-{}".format(ticket, step),
                                      "{} {:<13}".format(self.named(ticket), step),
                                      "{} {}".format(self.named(ticket), step), flake)

    def keep_flake_output(self, named, who, step, flake):
        held = self.stamped("flake-" + named)
        written(held, flake.said)
        self.say("FLAKE {}{} went red and then passed. Its red output is kept at {}".format(
            who, flake.check, held.as_posix()))
        self.run_flakes.append((flake.check, step, held.as_posix()))
        return held.as_posix()

    # Red is handed back rather than raised, so the caller chooses between a circuit and a stop.
    def run_suite_step(self, ticket, step):
        held = self.step_file(ticket, step.name, "out")
        self.say("STEP  {} {:<13}{}".format(
            self.named(ticket), step.name,
            progress_suffix(self.position, self.ticket_count, self.mean_seconds)))

        # The red that sent the loop round is why it ran again, so a second run adds to the record.
        if self.red_suite is None:
            written(held, "")
        outcome = Suite(self.runner, self.job_worktree).run(
            self.suite_heard(ticket, held))

        # A machine short of what the checks need is nothing a Session could mend, so none is asked.
        if not outcome.ready:
            appended(held, "--- the suite could not start\n{}".format(outcome.said))
            raise stop("ABORT {} failed check suite-can-run, so no Session was asked to mend "
                       "it: {}\n      Its worktree is at {}. See {}".format(
                           self.named(ticket), outcome.said.strip(), self.job_worktree, held))
        for flake in outcome.flakes:
            self.flakes.append((flake.check, self.keep_flake(ticket, step.name, flake)))
        self.green_suite = outcome if outcome.passed else None
        return None if outcome.passed else outcome

    # --- getting started -----------------------------------------------------

    def preflight(self):
        self.tracker = tracker_for(self.runner, self.root, self.spec)
        if not self.runner.found("claude"):
            raise stop("ABORT claude is not on PATH")
        missing = missing_steering(self.root) or missing_import(self.root)
        if missing:
            raise stop("ABORT " + missing)
        reason = self.tracker.connect()
        if reason:
            raise stop("ABORT " + reason)

        state = self.tracker.spec_state(self.spec)
        if state is None:
            raise stop("ABORT cannot read spec {} from {}".format(self.spec_named(), self.tracker.repo))
        self.spec_title = self.tracker.spec_title(self.spec)
        if state != "open":
            raise stop("ABORT spec {} is {}. The loop needs it open.".format(self.spec_named(), state))

        self.ticket_count = len(self.tracker.tickets(self.spec))

    # Before the first ticket, so a spec whose Verdicts could never be counted costs no build.
    def read_shape(self):
        items = read_items(self.tracker.spec_body(self.spec))
        if items.faults:
            raise stop("ABORT spec {} is not in the shape the loop counts, so no ticket was "
                       "started.\n{}      /skillworks:grill writes a spec in the shape the loop counts. "
                       "Write it in that shape, and run the loop again.".format(
                           self.spec_named(),
                           "".join("      Fault: {}\n".format(fault) for fault in items.faults)))
        self.items = items
        self.say("SHAPE spec {} holds {}, {} and {}, so the drift check's Verdicts can be "
                 "counted".format(self.spec_named(),
                                  how_many(len(items.stories), "story", "stories"),
                                  how_many(len(items.decisions), "decision", "decisions"),
                                  how_many(len(items.surfaces), "Surface", "Surfaces")))

    # --- the Cut -------------------------------------------------------------

    # Typed and not called through the Skill tool, because the Skill tool refuses a hidden skill.
    def cut_asks(self):
        return PLUGIN + "to-tickets {}".format(self.spec)

    def cut_owed(self):
        return ("Spec {} holds no tickets yet. Publish the tickets you showed, one file for each in "
                ".spec-loop/{}/tickets/, with tracker-publish tickets {} <file>...\n".format(
                    self.spec_named(), self.spec, self.spec))

    # A re-check records with the same command as its check, so one sentence serves all four.
    def report_owed(self, report, kind, file):
        return ("Spec {} holds no {} yet. Record the report you wrote with tracker-publish {} {} "
                ".spec-loop/{}/{}\n".format(self.spec_named(), report, kind, self.spec, self.spec,
                                            file))

    def cut_tickets(self):
        self.say("CUT   spec {} has no tickets, so a Session cuts them first".format(
            self.spec_named()))
        result = self.run_clean_session(
            "cut", "Cut", self.cut_asks(),
            Recorded(CUT_RECORDED, lambda: self.tracker.tickets(self.spec), self.cut_owed()),
            TOLD_TO_BUILD + CUT_UNATTENDED, NUDGE_TAILS[TOLD_TO_BUILD])
        shown = str(field(result, "result")).rstrip("\n")
        if shown:
            self.wrote(shown + "\n")
        self.ticket_count = len(self.tracker.tickets(self.spec))
        if self.ticket_count == 0:
            raise self.stop_naming_denials("STOP  spec {} still has no tickets after the Cut, so "
                                   "nothing was built. See {}".format(
                                       self.spec_named(), self.log_dir / "cut.err"), result)

    # --- the dry run ---------------------------------------------------------

    def landing_plan(self):
        out, err = io.StringIO(), io.StringIO()
        land_ticket.main(["--plan"], self.runner, out, err, self.wait)
        return listed(out.getvalue())

    def after_tickets_plan(self):
        drift = 'claude -p "{}spec-drift {} <base>'.format(PLUGIN, self.spec)
        names = 'claude -p "{}spec-names {} <base>'.format(PLUGIN, self.spec)
        return ("  after every ticket is closed\n"
                + plan_line("drift", drift + '" --session-id <new id>',
                            "a report recorded, a Verdicts list, no Contradicts")
                + nudges_line(REPORT_RECORDED)
                + plan_line("gap-ticket", "one ticket under the spec when the count finds a Gap, "
                            "built through every step above")
                + plan_line("re-check", drift + ' <the Gap items>" --session-id <new id>, once',
                            "no Gap left, no Contradicts")
                + nudges_line(NEW_REPORT_RECORDED)
                + plan_line("names", names + '" --session-id <new id>',
                            "a Name report recorded, a Renames list")
                + nudges_line(REPORT_RECORDED)
                + plan_line("rename-ticket", "one ticket under the spec when the Name check finds "
                            "a rename, built through every step above")
                + plan_line("name-re-check", names + ' <the rename ticket>" --session-id <new id>, '
                            'once', "a new Name report, a Verdicts list, every rename Done")
                + nudges_line(NEW_REPORT_RECORDED)
                + plan_line("full-run", "the whole Suite on the newest origin/<target>, with no "
                            "Proofs and no images, once and last"))

    def ticket_plan(self, number, landing):
        # A job name takes letters only, so the place for a number is asked for in letters.
        job = "ticket-" + (UNCUT_JOB_NUMBER if number == UNCUT_NUMBER else number)
        status, said, _ = self.worktree("plan", job)
        told = said.strip().replace(job, "ticket-" + number).split("\t")
        if status != 0 or len(told) != 2:
            raise stop("ABORT {} could not be told where it would be built.".format(
                self.named(number)))
        plan = plan_line("worktree", told[0]) + plan_line("branch", told[1])

        for step in STEPS:
            if not step.session:
                plan += plan_line(step.name, step.asks, step.checks)
                continue
            call = 'claude -p "{}"'.format(self.asks(step, number))
            if step.resumes:
                call += " --resume <build session>"
            else:
                call += " --session-id <new id>"
            plan += plan_line(step.name, call, step.checks)
            nudged = nudged_on(step)
            if nudged:
                plan += nudges_line(" ".join(nudged))

        for step in landing:
            named, what, checks = columns(step)
            plan += plan_line(named, what, checks)
        return plan

    def dry_run(self):
        self.say("DRY   repo={}  me={}".format(self.tracker.repo, self.tracker.me))
        self.say("DRY   spec {}: {}".format(self.spec_named(), self.spec_title))
        self.read_shape()

        # Asked of the scripts that do the work, so the plan cannot drift from the run.
        landing = self.landing_plan()
        if not landing:
            raise stop("ABORT the landing steps would not be read, so the plan would be short of "
                       "them.")

        # Gathered whole and printed once, so a step that cannot be planned can still stop the run.
        plan = ""
        if self.ticket_count == 0:
            self.say("DRY   spec {} has no tickets, so a Session would cut them first".format(
                self.spec_named()))
            plan += "  before the first ticket\n" + plan_line(
                "cut", 'claude -p "{}" --session-id <new id>'.format(self.cut_asks()),
                "nothing left uncommitted, at least one ticket under the spec")
            plan += nudges_line(CUT_RECORDED)
            plan += "  each ticket the Cut makes\n" + self.ticket_plan(UNCUT_NUMBER, landing)
        for number, state, title in self.tracker.ticket_rows(self.spec):
            plan += "  {} [{}] {}\n".format(self.named(number), state, title)
            if state == "open":
                plan += self.ticket_plan(number, landing)

        self.wrote(plan + self.after_tickets_plan() + told_plan())
        # Asked the way the run asks, so the ticket named is the one a run would claim first.
        chosen = self.next_ticket(self.tracker.open_tickets(self.spec))
        if self.ticket_count == 0:
            self.say("DRY   the next ticket is the first one the Cut makes")
        elif chosen:
            self.say("DRY   the next ticket is {}".format(self.named(chosen)))
        else:
            self.say("DRY   no ticket is startable")
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
            raise stop("ABORT spec {} has a worktree group that would not be kept. Nothing was "
                       "started.".format(self.spec_named()))

    # --- picking the next ticket ---------------------------------------------

    def next_ticket(self, open_tickets):
        for number in open_tickets:
            blocked = self.tracker.open_blockers(number)
            if blocked is None:
                raise stop("ABORT the Tracker would not say how many open blockers {} has. "
                           "Refusing to guess.".format(self.named(number)))
            if blocked != 0:
                continue
            if self.tracker.claimed_by_others(number):
                continue
            return number
        return ""

    def claimed(self, ticket):
        others = self.tracker.claim(ticket, self.wait)
        if not others:
            return True
        self.say("SKIP  {} claimed by {}".format(self.named(ticket), others))
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
        self.say("      {} the suite went red on every run it was given, so the loop goes "
                 "round once: {}".format(self.named(ticket), ", then ".join(CIRCUIT)))
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
                raise stop("FAIL  {} step build gave no session id. See {}".format(
                    self.named(ticket), held))
        return session

    # The session that wrote the ticket goes too, to resolve what its work conflicts with.
    def land(self, ticket, session):
        held = self.step_file(ticket, "land", "out")
        written(held, "")

        def heard(line):
            appended(held, line + "\n")
            self.say(line)
        said = Lines(heard)
        landed = land_ticket.main(
            [self.job_worktree, ticket, session], self.runner, said, said, self.wait,
            self.permission_mode, self.target, self.tracker,
            lambda flake: self.keep_flake(ticket, "land", flake),
            lambda ran, failed: self.keep_resolution(ticket, ran, failed))
        said.end()
        if landed != 0:
            # The finishing step closed it, and the work it closed on never reached the remote.
            self.reopen(ticket)
            raise stop("FAIL  {} did not reach {}. Its worktree is at {}. See {}".format(
                self.named(ticket), self.target, self.job_worktree, held))

    def keep_resolution(self, ticket, ran, failed):
        held = self.step_file(ticket, "resolve", "json")
        written(held, ran.out)
        self.say_result("{} {:<13}".format(self.named(ticket), "resolve"), held)
        self.add_to_journal(ran, held, "resolve", 0, failed, ticket=ticket)

    # A planned stop reopens the ticket itself, and anything else may come after finish closed it.
    def build_and_land(self, ticket):
        try:
            self.land(ticket, self.build_ticket(ticket))
        except Stop:
            raise
        except BaseException:
            self.reopen_keeping_the_error(ticket)
            raise

    # A reopen that raises would take the place of the error that is why the run ended.
    def reopen_keeping_the_error(self, ticket):
        try:
            self.reopen(ticket)
        except Exception as failed:
            self.say("WARN  {} did not reopen, {}: {}. Reopen it by hand, or a rerun will skip "
                     "it.".format(self.named(ticket), type(failed).__name__, failed))

    def run_ticket(self, ticket):
        self.say("START {} {}".format(self.named(ticket), self.tracker.title(ticket)))

        self.red_suite = None
        self.green_suite = None
        self.flakes = []
        self.job_worktree = self.opened("ticket-" + ticket)
        if not self.job_worktree:
            raise stop("FAIL  {} got no worktree to be built in.".format(self.named(ticket)))
        self.ticket_base = self.git(self.job_worktree, "rev-parse", "HEAD").out.strip()
        started = time.time()

        self.build_and_land(ticket)
        self.landed.append(ticket)
        landed_at = self.git(self.job_worktree, "rev-parse", "--short", "HEAD").out.strip()

        # A ticket that failed never gets here, so a worktree left behind means a stop.
        if self.worktree("close", "ticket-" + ticket)[0] != 0:
            raise stop("FAIL  {} landed, but its worktree at {} would not go.".format(
                self.named(ticket), self.job_worktree))

        # A skipped ticket never reaches here, so nobody else's work is in the mean.
        self.timed_seconds += int(time.time() - started)
        self.timed_tickets += 1
        self.mean_seconds = self.timed_seconds // self.timed_tickets
        self.say("DONE  {}  {}".format(self.named(ticket), landed_at))

    def run_tickets(self):
        while True:
            open_tickets = self.tracker.open_tickets(self.spec)
            ticket = self.next_ticket(open_tickets)
            if not ticket:
                if not open_tickets:
                    return
                raise stop("STUCK {} ticket(s) still open but none are startable (blocked, or "
                           "claimed by someone else).".format(len(open_tickets)))

            if not self.claimed(ticket):
                continue

            # Counts closed tickets, not this run's, so a rerun starts at its real place.
            self.position = self.ticket_count - len(open_tickets) + 1
            self.run_ticket(ticket)

    # --- the full run --------------------------------------------------------

    # Tickets leaned on Proofs and images, so this trusts neither; its red is the Target branch's.
    def run_full(self, stopped=None):
        if not self.landed:
            return
        landed = ", ".join(self.named(ticket) for ticket in self.landed)
        self.say("FULL  {} landed in this run, so the whole Suite runs on the newest origin/{} "
                 "with no Proofs and no images".format(landed, self.target))

        held = self.stamped(FULL_RUN)
        written(held, "")
        self.remove_left_full_run(stopped)
        tree = self.opened(FULL_RUN)
        if not tree:
            raise after(stop("FAIL  the full run got no worktree to run in, so {} is unproved "
                             "since {} landed.".format(self.target, landed)), stopped)
        at = self.git(tree, "rev-parse", "--short", "HEAD").out.strip()

        def heard(outcome, run):
            appended(held, "--- suite run {}\n{}".format(run, outcome.said))
            self.say("FULL  run {} {}".format(run, suite_verdict(outcome, run)))
        outcome = Suite(self.runner, tree, fresh=True).run(heard)
        for flake in outcome.flakes:
            self.keep_flake_output(FULL_RUN, "{:<18}".format(FULL_RUN), "the full run", flake)

        # A crash dump or a log a tool wrote there is all a red or a Flake leaves to read.
        left = outcome.ready and (not outcome.passed or bool(outcome.flakes))
        if left:
            self.left_full_run_tree = tree
            self.say("FULL  its worktree is left at {}. The next full run of spec {} removes "
                     "it.".format(tree, self.spec_named()))
        stuck = not left and self.worktree("close", FULL_RUN)[0] != 0
        if not outcome.ready:
            appended(held, "--- the suite could not start\n{}".format(outcome.said))
            raise after(stop("ABORT the full run of the Suite could not start, so {} at {} is "
                             "unproved since {} landed: {}\n      See {}".format(
                                 self.target, at, landed, outcome.said.strip(), held)), stopped)
        if not outcome.passed:
            raise after(stop("RED   the full run of the Suite went red on {} at {}, with no "
                             "Proofs and no images. The spec stays open, and no Session was "
                             "asked to fix it.\n      Red: {}\n      Landed in this run: {}\n"
                             "      See {}".format(
                                 self.target, at, ", ".join(outcome.red), landed, held)), stopped)
        self.say("FULL  {} at {} passed the whole Suite".format(self.target, at))
        if stuck:
            raise after(stop("FAIL  the full run's worktree at {} would not go.".format(tree)),
                        stopped)

    def remove_left_full_run(self, stopped):
        tree, branch, _ = columns(self.worktree("plan", FULL_RUN)[1].strip())
        if not Path(tree).exists() and self.git(
                self.root, "rev-parse", "--verify", "--quiet", "refs/heads/" + branch).status != 0:
            return
        if self.worktree("close", FULL_RUN)[0] != 0:
            raise after(stop("FAIL  the worktree the last full run left at {} would not go, so "
                             "this full run did not start.".format(tree)), stopped)
        self.say("FULL  removed the worktree the last full run left at {}".format(tree))

    # --- the drift check -----------------------------------------------------

    # The Session records its work with the spec and changes nothing, so a tree it left changed stops.
    # Returned so the caller's stop can name the Denials that may be why nothing was recorded.
    def run_clean_session(self, named, what, prompt, recorded=None, told=TOLD_TO_JUDGE,
                          nudge_tail=NUDGE_TAILS[TOLD_TO_JUDGE], handed_on=""):
        # The main checkout was never pulled, so only a fresh worktree holds the finished work.
        self.job_worktree = self.opened(named)
        if not self.job_worktree:
            raise stop("FAIL  the {} got no worktree to run in.".format(what))

        ran = self.claude_p(prompt + "\n\n" + told + handed_on)
        result = self.log_dir / (named + ".json")
        reasons = self.log_dir / (named + ".err")
        written(reasons, ran.err)
        nudge = 0
        while True:
            written(result, ran.out)
            self.say_result("spec {} {:<13}".format(self.spec_named(), named), result)
            if ran.status != 0:
                self.say("WARN  {} exited non-zero. See {}".format(what, reasons))
            blocked = blocked_line(result)
            failed = None
            try:
                # Read before the worktree goes, so a Nudge can resume the Session where it ran.
                failed = ([] if blocked or recorded is None or recorded.holds()
                          else [recorded.check])
            finally:
                self.add_to_journal(ran, result, named, nudge, failed, spec_step=what)
            if blocked:
                raise self.stop_naming_denials("STOP  spec {} {} is Blocked: {}\n      See {}".format(
                    self.spec_named(), named, blocked, result), result)
            if not failed or nudge == NUDGES:
                break
            nudge += 1
            self.say("NUDGE spec {} {:<13}{} of {}, failed {}".format(
                self.spec_named(), named, nudge, NUDGES, recorded.check))
            ran = self.claude_p(recorded.owed + nudge_tail, "--resume", field(result, "session_id"))
            appended(reasons, ran.err)

        if self.tree_of_job():
            raise stop("FAIL  {} left uncommitted changes in {}.".format(what, self.job_worktree))
        if self.worktree("close", named)[0] != 0:
            raise stop("FAIL  the {}'s worktree at {} would not go.".format(
                what, self.job_worktree))
        return result

    # The same lookup the check makes, so the log shows its scope and a broken one never reads as clean.
    def say_scope(self, what, base):
        kept, left = spec_commits(self.tracker, self.spec, base, self.wait, self.target)
        if not kept:
            raise stop("STOP  spec {} has no commit after the base commit {} whose Ticket: trailer "
                       "names one of its tickets. {} The {} did not run and the spec stays "
                       "open.".format(self.spec_named(), base, self.why_no_commit(), what))
        self.say("SCOPE the {} reads {} of spec {}, and leaves out {} after the base commit".format(
            what, how_many(len(kept), "commit", "commits"), self.spec_named(),
            how_many(len(left), "other commit", "other commits")))

    # A ticket closed by a run that died before its push holds no commit, and the loop skips it.
    def why_no_commit(self):
        closed = [self.named(number) for number, state, _ in self.tracker.ticket_rows(self.spec)
                  if state == "closed"]
        if not closed:
            return "Every Landed ticket's commit names it, so the lookup broke."
        return "{} {} closed with no Landed commit. Reopen {}, then rerun with: spec-loop {}.".format(
            in_words(closed), "is" if len(closed) == 1 else "are",
            "it" if len(closed) == 1 else "each one", self.spec)

    # Handed the Gap items, it judges those alone, so the re-check has a small context and misses less.
    def check_drift(self, base, asked=()):
        named = "drift-gaps" if asked else "drift"
        self.say_scope("drift re-check" if asked else "drift check", base)
        if asked:
            self.say("DRIFT the Gap ticket is closed. Checking {} against spec {} again.".format(
                ", ".join(asked), self.spec_named()))
        else:
            self.say("DRIFT all tickets closed. Checking the result against spec {}.".format(
                self.spec_named()))
        recorded = Recorded(
            NEW_REPORT_RECORDED if asked else REPORT_RECORDED,
            lambda: self.drift_recorded(asked),
            self.report_owed("new drift report" if asked else "drift report", "drift",
                             "drift-report.md"))
        result = self.run_clean_session(named, "drift check", PLUGIN + "spec-drift {} {}{}".format(
            self.spec, base, " " + ITEM_SEPARATOR.join(asked) if asked else ""), recorded,
            handed_on=self.spec_departures())
        return self.read_drift_report(named, asked, result)

    # The Tracker hands back the newest report, so a re-check that recorded none reads the first.
    def drift_recorded(self, asked):
        report = self.tracker.drift_report(self.spec)
        return report and not (asked and report == self.drift_read)

    # Read back from the Tracker, so a report the Session only said and never recorded is caught.
    def read_drift_report(self, named, asked, result):
        report = self.tracker.drift_report(self.spec)
        if not report:
            raise self.stop_naming_denials("STOP  the drift check recorded no report on spec {}, so nothing "
                                   "was counted and the spec stays open.".format(
                                       self.spec_named()), result)
        # The Tracker hands back the newest report, so a re-check that recorded none reads the first.
        if asked and report == self.drift_read:
            raise self.stop_naming_denials("STOP  the re-check recorded no new report on spec {}, so the Gap "
                                   "items were not judged again and the spec stays open.".format(
                                       self.spec_named()), result)
        self.drift_read = report
        held = self.log_dir / (named + ".md")
        written(held, report + "\n")
        self.say("DRIFT the report is recorded on spec {}. Read it at {}".format(
            self.spec_named(), held))
        return self.count_drift(read_verdicts(report), held, asked)

    # The driver judges nothing: it counts, so a skipped item is caught by arithmetic.
    def count_drift(self, report, held, asked):
        if report.verdicts is None:
            raise stop("STOP  the drift report on spec {} holds no {} list, so nothing was "
                       "counted and the spec stays open. Read it at {}".format(
                           self.spec_named(), VERDICTS, held))
        every = with_readme(self.items, readme_surface_of(self.root))
        items = every.only(asked) if asked else every
        counted = count_verdicts(items, report.verdicts)
        self.say("COUNT {} {}, and the drift report gives {}".format(
            "the re-check was asked about" if asked else "the spec holds",
            how_many(len(items.every()), "item", "items"),
            how_many(counted.verdicts_given, "Verdict", "Verdicts")))
        outside = ("the re-check was not asked about" if asked
                   else "spec {} does not hold".format(self.spec_named()))
        for verdict in counted.unknown:
            self.say("WARN  the drift report judges {}, which {}, so its Verdict is not "
                     "counted".format(verdict.item, outside))
        for said in report.unrequested:
            self.say("NOTE  Unrequested: " + said)

        gaps = "".join("      Gap: {}\n".format(gap_said(gap)) for gap in counted.gaps)
        if counted.contradicts:
            raise stop("STOP  the drift report finds the code contradicts spec {}, so the loop "
                       "stops before anything more is built. A person decides.\n{}{}"
                       "      Read it at {}".format(
                           self.spec_named(),
                           "".join("      Contradicts: {}\n".format(contradicts_said(verdict))
                                   for verdict in counted.contradicts),
                           gaps, held))
        if counted.gaps and asked:
            raise stop("STOP  the drift check still finds {} on spec {} after the Gap ticket was "
                       "built, and the loop goes round once. A person decides.\n{}"
                       "      Read it at {}".format(
                           how_many(len(counted.gaps), "Gap", "Gaps"), self.spec_named(), gaps,
                           held))
        return counted.gaps

    # --- the Gap round -------------------------------------------------------

    # Filed and then built like any ticket, since the loop reads the open tickets again before each.
    def file_gap_ticket(self, gaps):
        for gap in gaps:
            self.say("GAP   " + gap_said(gap))
        title, body = gap_ticket(gaps)
        ticket = self.tracker.file_ticket(self.spec, title, body)
        self.ticket_count += 1
        self.say("FILED {} under spec {} builds {}, so the loop goes round once".format(
            self.named(ticket), self.spec_named(), how_many(len(gaps), "Gap", "Gaps")))

    # One round, so a Gap that survives a build aimed at it comes to a person rather than looping.
    def close_gaps(self, base):
        gaps = self.check_drift(base)
        if not gaps:
            return
        self.file_gap_ticket(gaps)
        self.run_tickets()
        self.check_drift(base, [gap.item.name for gap in gaps])

    # --- the Name check ------------------------------------------------------

    # After the Gap round, so it sees every name the spec brought in, the Gap build's too.
    def check_names(self, base):
        self.say_scope("Name check", base)
        self.say("NAMES checking the names spec {} brought in against the glossary.".format(
            self.spec_named()))
        result = self.run_clean_session("names", "Name check", PLUGIN + "spec-names {} {}".format(
            self.spec, base), Recorded(
                REPORT_RECORDED, lambda: self.tracker.name_report(self.spec),
                self.report_owed("Name report", "names", "names-report.md")))

        # Read back from the Tracker, so a finding the Session only said and never recorded is caught.
        report = self.tracker.name_report(self.spec)
        if not report:
            raise self.stop_naming_denials("STOP  the Name check recorded no report on spec {}, so no name "
                                   "was read and the spec stays open.".format(
                                       self.spec_named()), result)
        self.names_read = report
        held = self.log_dir / "names.md"
        written(held, report + "\n")
        self.say("NAMES the report is recorded on spec {}. Read it at {}".format(
            self.spec_named(), held))

        renames = read_renames(report)
        if renames is None:
            raise stop("STOP  the Name report on spec {} holds no {} list, so no rename was read "
                       "and the spec stays open. Read it at {}".format(
                           self.spec_named(), RENAMES, held))
        for said in renames:
            self.say("NAME  " + said)
        if not renames:
            self.say("NAMES no rename is owed on spec {}".format(self.spec_named()))
        return renames

    # --- the rename ticket ---------------------------------------------------

    # A rename is never a question for a person, so every one is built without asking.
    def file_rename_ticket(self, renames):
        for said in renames:
            if has_no_glossary_word(said):
                self.say("NOTE  {} has no glossary word, so the rename takes the name the code and "
                         "the spec use most. A person settles the word.".format(name_of(said)))
        title, body = rename_ticket(renames)
        ticket = self.tracker.file_ticket(self.spec, title, body)
        self.ticket_count += 1
        self.say("FILED {} under spec {} makes {}, so the loop builds it and checks each one".format(
            self.named(ticket), self.spec_named(), how_many(len(renames), "rename", "renames")))
        return ticket

    # The rename ticket's diff alone, so the check that each rename was made has a small context.
    def check_renames(self, base, ticket, renames):
        self.say("NAMES the rename ticket {} is closed. Checking it made each rename on spec "
                 "{}.".format(self.named(ticket), self.spec_named()))
        result = self.run_clean_session(
            "names-renames", "Name re-check", PLUGIN + "spec-names {} {} {}".format(
                self.spec, base, self.tracker.reference(ticket)), Recorded(
                    NEW_REPORT_RECORDED, self.new_name_report,
                    self.report_owed("new Name report", "names", "names-report.md")))

        report = self.new_name_report()
        if not report:
            raise self.stop_naming_denials("STOP  the Name re-check recorded no new report on spec {}, so no "
                                   "rename was checked and the spec stays open.".format(
                                       self.spec_named()), result)
        held = self.log_dir / "names-renames.md"
        written(held, report + "\n")
        verdicts = read_rename_verdicts(report)
        if verdicts is None:
            raise stop("STOP  the Name re-check on spec {} holds no {} list, so no rename was "
                       "counted and the spec stays open. Read it at {}".format(
                           self.spec_named(), VERDICTS, held))

        counted = count_renames(renames, verdicts)
        self.say("COUNT the rename ticket owes {}, and the Name re-check gives {}".format(
            how_many(len(renames), "rename", "renames"),
            how_many(counted.verdicts_given, "Verdict", "Verdicts")))
        for verdict in counted.unknown:
            self.say("WARN  the Name re-check judges {}, which the rename ticket does not owe, so "
                     "its Verdict is not counted".format(verdict.item))
        if counted.unmade:
            raise stop("STOP  the Name re-check finds {} on spec {} after the rename ticket was "
                       "built. A person decides.\n{}      Read it at {}".format(
                           how_many(len(counted.unmade), "rename not made", "renames not made"),
                           self.spec_named(),
                           "".join("      Not made: {}\n".format(unmade_said(unmade))
                                   for unmade in counted.unmade), held))
        self.say("NAMES every rename is made on spec {}".format(self.spec_named()))

    # The Tracker hands back the newest report, so a check that recorded none reads the first.
    def new_name_report(self):
        report = self.tracker.name_report(self.spec)
        return report if report != self.names_read else None

    # Its own ticket after the Gap ticket, so each build has one job and no later build brings a name.
    def close_renames(self, base):
        renames = self.check_names(base)
        if not renames:
            return
        ticket = self.file_rename_ticket(renames)
        self.run_tickets()
        self.check_renames(base, ticket, renames)

    # --- the note of the run's Flakes ----------------------------------------

    # A warning and not a stop, so a note that did not reach the spec never hides why the run ended.
    def note_flakes(self):
        if not self.run_flakes:
            return
        note = ("{}\n\nEach check below went red and then passed, so this run counted it green. "
                "Its red output is kept in the file named beside it.\n\n{}".format(
                    FLAKES, "".join("- {}, in {}: {}\n".format(check, step, held)
                                    for check, step, held in self.run_flakes)))
        if self.left_full_run_tree:
            note += ("\nThe full run's worktree is left at {}. The next full run of spec {} "
                     "removes it.\n".format(self.left_full_run_tree, self.spec_named()))
        try:
            self.tracker.record_flakes(self.spec, note)
        except Stop as refused:
            self.say("WARN  the note listing the Flakes of this run did not reach spec {}. The "
                     "FLAKE lines above name each one. {}".format(
                         self.spec_named(), refused.said.strip()))
            return
        self.say("NOTE  spec {} has a note listing the {} of this run".format(
            self.spec_named(), how_many(len(self.run_flakes), "Flake", "Flakes")))

    # --- the spec's close ---------------------------------------------------

    # After the drift check, so no spec is closed before its work was read against it.
    def close_spec(self):
        closed_at = self.tracker.close_spec(self.spec)
        if closed_at:
            self.say("CLOSE spec {} is closed on {} as {}".format(
                self.spec_named(), self.target, closed_at))

    # --- the pull request, in spec mode --------------------------------------

    # Ready and never merged, so a person reviews the spec before it reaches the default branch.
    def mark_ready(self):
        marked = self.gh("pr", "ready", self.target)
        if marked.status != 0:
            raise stop("FAIL  the pull request from {} was not marked ready for review. Mark it "
                       "with: gh pr ready {}\n      gh said: {}".format(
                           self.target, self.target, (marked.out + marked.err).strip()))
        self.say("READY the pull request from {} is ready for review. A person reviews and "
                 "merges it.".format(self.target))

    def hand_over(self):
        if self.tracker.marks_pull_requests:
            self.mark_ready()
            return
        self.say("PR    open the pull request from {} on your host, or mark it ready for review "
                 "if it is open. A person reviews and merges it.".format(self.target))

    # --- the whole run -------------------------------------------------------

    def read_target(self):
        self.spec_mode = in_spec_mode(self.root)
        return target_branch_for(self.runner, self.root, self.spec, self.tracker)

    def run(self, dry):
        # No guard on the branch or on the edits: nothing is ever built in this checkout.
        found = self.git(Path.cwd(), "rev-parse", "--show-toplevel")
        if found.status != 0:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            raise stop("ABORT {} is not a git worktree.".format(Path.cwd().as_posix()))
        self.root = Path(found.out.strip())
        self.log_dir = self.root / ".spec-loop" / self.spec
        self.log = self.log_dir / "loop.log"
        self.journal = self.log_dir / "journal.jsonl"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.preflight()
        if dry:
            return self.dry_run()

        self.read_shape()
        self.keep_leftovers()

        # Read once and handed to the worktree and landing scripts, so all three agree.
        self.target = self.read_target()

        # Every worktree is cut from the Target branch on origin, so the ref has to be current first.
        if not fetch_origin(self.runner, self.root.as_posix(), self.target, self.err, self.wait):
            raise stop("ABORT could not fetch {} from origin".format(self.target))

        # Written once, so a resumed run still measures from where the first run started.
        held = self.log_dir / "base.sha"
        if not held.is_file():
            written(held, self.git(self.root, "rev-parse", "origin/" + self.target).out)
        base = held.read_text(encoding="utf-8").strip()

        self.say("LOOP  spec {} from {} ({}) in {} mode".format(
            self.spec_named(), base, self.tracker.repo, self.permission_mode))

        # After the shape, so a spec the drift check could never count costs no Cut.
        if self.ticket_count == 0:
            self.cut_tickets()

        # A landed ticket stays when the loop stops, so a stop is followed by the full run too.
        # It runs last and once, so the slowest step proves the finished spec and nothing before it.
        try:
            try:
                self.run_tickets()
                self.close_gaps(base)
                self.close_renames(base)
            except Stop as stopped:
                self.run_full(stopped)
                raise
            self.run_full()
        finally:
            self.note_flakes()

        # Reached only with every Verdict Done or In step, every rename Done and the full run green.
        self.close_spec()
        if self.spec_mode:
            self.hand_over()
        self.say("END   spec {} complete. Every ticket is on {}.".format(
            self.spec_named(), self.target))
        self.say("      Review it with: git log --oneline {}..origin/{}".format(base, self.target))


def arguments(argv):
    spec = argv[0] if len(argv) > 0 else ""
    rest = argv[1:]
    if not is_a_number(spec):
        raise misuse(USAGE)
    if any(flag not in FLAGS for flag in rest):
        raise misuse(USAGE)
    mode = BYPASS_MODE if "--bypass" in rest else land_ticket.permission_mode_set()
    return spec, "--dry-run" in rest, mode


def main(argv, runner, out, err, wait):
    loop = None
    try:
        spec, dry, mode = arguments(argv)
        loop = Loop(runner, spec, out, err, wait, mode)
        loop.run(dry)
        loop.list_what_sessions_wrote()
        return 0
    except Stop as stopped:
        if stopped.status == MISUSED or loop is None:
            err.write(stopped.said)
        else:
            # A refusal from a script the loop reads ends its line itself, and say ends it again.
            loop.say(stopped.said.rstrip("\n"))
            loop.list_what_sessions_wrote()
        return stopped.status
    except Exception as failed:
        if loop is None:
            raise
        held = traceback.format_exc()
        loop.log_dir.mkdir(parents=True, exist_ok=True)
        appended(loop.log, held)
        err.write(held)
        loop.say("FAIL  the driver met an error it did not expect, {}: {}. The traceback is above "
                 "in {}. Rerun with: spec-loop {}".format(
                     type(failed).__name__, failed, loop.log.as_posix(), loop.spec))
        loop.list_what_sessions_wrote()
        return REFUSED


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr, time.sleep))
