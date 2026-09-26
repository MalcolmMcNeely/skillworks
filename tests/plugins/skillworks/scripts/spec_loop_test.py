#
# The spec loop's plan and its steps, read against a throwaway repository.

import io
import json
import re
import threading
import uuid
from pathlib import Path

import pytest

import land_ticket
import spec_loop
import ticket_worktree
from conftest import ROOT, Ran, check, git, launch, no_wait, project_suite, write_suite
from runner import Subprocess

SPEC = "158"

ONE_OPEN_TICKET = (("168", "open", "TICKET: The dry run prints the plan"),)
ONE_CLOSED_TICKET = (("161", "closed", "TICKET: Already done"),)

# What each axis says when a case has not given it words of its own.
AXIS_REPORTS = {
    "review-standards": "## Standards. Nothing found.",
    "review-spec": "## Spec. Nothing found.",
    "review-architecture": "## Architecture. Nothing found.",
}


class Driver:
    def __init__(self, repo, runner):
        self.repo = repo
        self.runner = runner
        # Recorded rather than waited out, so the claim can be read without spending its seconds.
        self.waits = []

    def run(self, *args):
        out, err = io.StringIO(), io.StringIO()
        status = spec_loop.main(
            [str(a) for a in args], self.runner, out, err, self.waits.append)
        return Ran(status, out.getvalue(), err.getvalue())

    def records(self):
        return self.repo.work / ".spec-loop" / SPEC

    def log(self):
        return (self.records() / "loop.log").read_text(encoding="utf-8")


@pytest.fixture
def loop(repo, runner, monkeypatch):
    # The loop puts its log where it is run, so it is run in the throwaway repository.
    monkeypatch.chdir(repo.work)
    # A session is looked for under this case's own folder, so no real one can answer a check here.
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", (repo.root / "claude").as_posix())
    # A suite run from inside a Session inherits both, so a case names the Parent it means or none.
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    monkeypatch.delenv("OTEL_RESOURCE_ATTRIBUTES", raising=False)
    # A loop started from a bypass run inherits its mode, so a case sets the one it means.
    monkeypatch.delenv("SPEC_LOOP_PERMISSION_MODE", raising=False)
    return Driver(repo, runner)


# A reason on stderr and what the loop said on stdout are one report, and a case reads it whole.
def said(ran):
    return ran.out + ran.err


class Tracker:
    # Every answer the loop asks for and no others, so an unplanned call fails rather than guesses.
    def __init__(self, runner, tickets):
        self.runner = runner
        self.tickets = tickets
        self.closed = set()
        runner.stub("gh", does=self.answer)

    def numbers(self, only_open=False):
        return "".join(row[0] + "\n" for row in self.tickets
                       if not only_open or (row[1] == "open" and row[0] not in self.closed))

    def answer(self):
        asked = " ".join(self.runner.calls[-1][1:])
        if asked == "auth status":
            return Ran(0, "", "")
        if asked == "repo view --json nameWithOwner --jq .nameWithOwner":
            return Ran(0, "owner/repo\n", "")
        if asked == "api user --jq .login":
            return Ran(0, "me\n", "")
        if asked.startswith("issue edit"):
            return Ran(0, "", "")
        if "blocked_by" in asked:
            return Ran(0, "0\n", "")
        if "assignees" in asked:
            return Ran(0, "\n", "")
        if "sub_issues" in asked:
            if ".[].number" in asked:
                return Ran(0, self.numbers(), "")
            if 'select(.state=="open")' in asked:
                return Ran(0, self.numbers(only_open=True), "")
            return Ran(0, "".join("\t".join(row) + "\n" for row in self.tickets), "")
        if asked.endswith("--jq .state"):
            number = asked.split(" ")[1].rsplit("/", 1)[-1]
            return Ran(0, "closed\n" if number in self.closed else "open\n", "")
        if asked.endswith("--jq .title"):
            return Ran(0, "SPEC: A spec to plan\n", "")
        return Ran(1, "", "the tracker has no answer for: " + asked + "\n")


def given_the_tracker_holds(loop, tickets):
    # Enough of a claude for the preflight to find one, and none of a session.
    loop.runner.stub("claude")
    return Tracker(loop.runner, tickets)


class Sessions:
    # A session that answers the way a real one would, and starts no model.
    def __init__(self, repo, runner):
        self.repo = repo
        self.runner = runner
        self.count = 0
        self.says = {}
        self.refuses = set()
        self.removes = {}
        self.writes = {}
        self.stages = set()
        self.bare = set()
        self.denials = {}
        self.garbles = set()
        self.errors = set()
        self.then = {}
        self.nudged = {}
        self.writes_when_nudged = {}
        self.when_nudged = {}
        self.forks = set()
        self.builds = True
        self.record_at_start = []
        self.steps = {}
        self.loaded = {}
        self.folder = repo.root / "claude" / "projects" / "one"
        self.folder.mkdir(parents=True, exist_ok=True)
        runner.stub("claude", does=self.answer)

    def answer(self):
        called = self.runner.calls[-1]
        if not called[2].startswith("/"):
            return self.answer_nudge(called)
        asked = called[2]
        command = asked.split(" ")[0]
        args = asked[len(command):]
        args = args[1:] if args.startswith(" ") else args
        step = command[1:].removeprefix("skillworks:")

        if step in self.refuses:
            return Ran(1, "", "the {} session was turned down\n".format(step))
        if step in self.removes:
            Path(self.removes[step]).unlink(missing_ok=True)
        if step in self.writes:
            name, text = self.writes[step]
            (Path(self.runner.where) / name).write_text(text, encoding="utf-8", newline="\n")
        if step in self.stages:
            git(self.runner.where, "add", "-N", ".")

        self.record_at_start.append(sessions_recorded(self.runner.where))

        # A real claude answers with the id it was handed, and makes one up only when handed none.
        self.count += 1
        called = self.runner.calls[-1]
        if "--session-id" in called:
            session = called[called.index("--session-id") + 1]
        elif "--resume" in called and step not in self.forks:
            session = called[called.index("--resume") + 1]
        else:
            session = "session-{}".format(self.count)
        self.steps[session] = step
        self.loaded[session] = asked
        self.record(session, "/" + step if step in self.bare else command, args)

        # The step that builds leaves the worktree changed, which is what its check reads.
        if asked.endswith("--stop-after-tests") and self.builds:
            (Path(self.runner.where) / "built.txt").write_text(
                "built\n", encoding="utf-8", newline="\n")

        # Matched on the command asked, so a case can pick out one of the three implement steps.
        for mark, does in self.then.items():
            if mark in asked:
                does()

        if step in self.garbles:
            return Ran(0, "the session ended before it wrote a result\n", "")

        return self.answered(step, session, self.said_by(step))

    # A resume keeps the Session's history, so the command it first loaded is still in its file.
    def answer_nudge(self, called):
        session = called[called.index("--resume") + 1]
        step = self.steps[session]
        with (self.folder / (session + ".jsonl")).open("a", encoding="utf-8", newline="\n") as file:
            file.write(json.dumps({"type": "user", "message": {"content": called[2]}}) + "\n")
        if step in self.writes_when_nudged:
            name, text = self.writes_when_nudged[step]
            (Path(self.runner.where) / name).write_text(text, encoding="utf-8", newline="\n")
        for mark, does in self.when_nudged.items():
            if mark in self.loaded[session]:
                does()
        waiting = self.nudged.get(step, [])
        said = waiting.pop(0) if waiting else self.said_by(step)
        return self.answered(step, session, said)

    def said_by(self, step):
        return self.says.get(step, AXIS_REPORTS.get(step, "did the " + step))

    def answered(self, step, session, said):
        answered = {"is_error": step in self.errors, "session_id": session, "result": said}
        if step in self.denials:
            answered["permission_denials"] = self.denials[step]
        return Ran(0, json.dumps(answered) + "\n", "")

    def record(self, session, command, args):
        entry = {"type": "user", "message": {"content":
                 "<command-name>{}</command-name><command-args>{}</command-args>".format(
                     command, args)}}
        (self.folder / (session + ".jsonl")).write_text(
            json.dumps(entry) + "\n", encoding="utf-8", newline="\n")


# A worktree is cut from the remote, so the Suite file has to reach it first.
def given_a_suite_on_main(loop, *checks, runs=None):
    write_suite(loop.repo.work, *checks, runs=runs)
    git(loop.repo.work, "add", "-A")
    git(loop.repo.work, "commit", "--quiet", "-m", "A Suite")
    git(loop.repo.work, "push", "--quiet", "origin", "main")


def given_a_suite_that_passes(loop, runs=None):
    given_a_suite_on_main(loop, project_suite()[0], runs=runs)
    loop.runner.stub("docker")
    loop.runner.stub("dotnet", says="the solution passed")


# The driver runs the suite itself, so a case about the steps needs one it can run.
def given_sessions_that_report(loop, runs=None):
    given_a_suite_that_passes(loop, runs)
    return Sessions(loop.repo, loop.runner)


def given_three_axes_with_something_to_say(sessions):
    sessions.says["review-standards"] = "## Standards. The name box says nothing."
    sessions.says["review-spec"] = "## Spec. The third criterion is unmet."
    sessions.says["review-architecture"] = "## Architecture. The arrow points the wrong way."


def given_an_axis_that_writes(sessions, axis, name, text):
    sessions.writes["review-" + axis] = (name, text)


# What every axis is told to run first, and nothing else.
def given_an_axis_that_only_stages(sessions, axis):
    sessions.stages.add("review-" + axis)


# The step's own check reads the report as well, so only the axis after it can take it away.
def given_a_report_lost_after_the_last_axis(loop, sessions, axis):
    sessions.removes["review-architecture"] = loop.records() / "ticket-168-{}.json".format(axis)


# --- reading what the loop did ----------------------------------------------

def sessions_record(tree):
    folder = git(tree, "rev-parse", "--absolute-git-dir").strip()
    return Path(folder) / ticket_worktree.SESSIONS_RECORD


def sessions_recorded(tree):
    held = sessions_record(tree)
    return held.read_text(encoding="utf-8").split() if held.is_file() else []


def session_calls(runner):
    return [call for call in runner.calls if call[0] == "claude"]


# A Nudge asks in words and a step asks for a command, so the slash tells the two apart.
def step_calls(runner):
    return [call for call in session_calls(runner) if call[2].startswith("/")]


def call_asking(runner, mark):
    for call in session_calls(runner):
        if call[2].startswith(mark):
            return call
    return None


def prompt_asking(runner, mark):
    call = call_asking(runner, mark)
    return "" if call is None else call[2]


# The circuit runs a step a second time, so a case reads them all and picks the one it means.
def prompts_asking(runner, mark):
    return [call[2] for call in session_calls(runner) if call[2].startswith(mark)]


def edit_of(loop, axis):
    for line in loop.log().split("\n"):
        words = line.split()
        if len(words) > 4 and words[1] == "EDIT" and words[3] == axis:
            return " ".join(words[4:])
    return ""


def call_at(runner, mark):
    for at, call in enumerate(runner.calls):
        if mark in " ".join(call):
            return at
    return -1


def every_call_at(runner, mark):
    return [at for at, call in enumerate(runner.calls) if mark in " ".join(call)]


def implement_flags(runner):
    return [call[2].split()[2] for call in session_calls(runner)
            if call[2].startswith("/skillworks:implement 168 ")]


# --- reading the plan -------------------------------------------------------

# The plan indents every line it gives a step, and these two name where a ticket is built.
WHERE_IT_IS_BUILT = ("worktree", "branch")


def indented(ran):
    return [line for line in ran.out.split("\n") if line.startswith("      ") and line.strip()]


# The driver's steps print before the landing's, so a name both lists hold reads as the driver's.
def plan_calls(ran):
    return [line.strip() for line in indented(ran)
            if not line.strip().startswith(("checks: ", "nudges: "))
            and line.split()[0] not in WHERE_IT_IS_BUILT]


# The Nudges sit on the line under a step's checks, and only a step that can be Nudged has one.
def planned_nudges(ran, step):
    lines = indented(ran)
    for at, line in enumerate(lines[:-2]):
        if line.split()[0] == step:
            under = lines[at + 2].strip()
            return under[len("nudges: "):] if under.startswith("nudges: ") else ""
    return ""


# The step names in the order the plan prints them, so a case reads the order and not just the set.
def planned_steps(ran):
    return [line.split()[0] for line in plan_calls(ran)]


def planned_call(ran, step):
    for line in plan_calls(ran):
        if line.split()[0] == step:
            return line
    return ""


# The checks sit on the line under the call they belong to, so a case reads the pair.
def planned_checks(ran, step):
    lines = indented(ran)
    for at, line in enumerate(lines[:-1]):
        if line.split()[0] == step:
            under = lines[at + 1].strip()
            return under[len("checks: "):] if under.startswith("checks: ") else under
    return ""


# --- the dry run ------------------------------------------------------------

def test_the_dry_run_prints_the_worktree_and_the_branch(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    assert loop.repo.tree(SPEC, "ticket-168").as_posix() in said(ran)
    assert "spec-loop/158/ticket-168" in said(ran)


def test_the_dry_run_prints_every_landing_step_with_its_checks(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    # Written out, so a renamed or reordered landing step fails here rather than moving both sides.
    for line in (
        "the worktree, its tree and the trailer on its commit",
        "checks: is-a-worktree tree-clean ticket-named",
        "git fetch origin (up to 5 attempts)",
        "checks: origin-has-main something-to-land",
        "git rebase origin/main, when the base has moved",
        "checks: commits-kept files-kept",
        "the build session, when the rebase conflicts",
        "checks: session-named no-refusal none-left-conflicting no-marker-staged "
        "rebase-carried-on",
        "the whole suite, when the base has moved",
        "checks: suite-can-run suite-green",
        "git push origin HEAD:main, again after each lost race",
        "checks: pushed\n",
    ):
        assert line in said(ran)


def test_the_dry_run_still_prints_the_sessions_it_would_start(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    for line in (
        "/skillworks:implement 168 --stop-after-tests",
        "/skillworks:implement 168 --fix",
        "/skillworks:comment-sweep",
        "/skillworks:implement 168 --finish",
        "checks: no-error command-loaded ticket-open tree-changed",
        "checks: no-error command-loaded new-commit tree-clean ticket-closed",
    ):
        assert line in said(ran)


def test_the_dry_run_prints_all_eight_steps_in_order(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    for line in ("/skillworks:review-standards 168", "/skillworks:review-spec 168",
                 "/skillworks:review-architecture 168"):
        assert line in said(ran)
    assert planned_steps(ran)[:8] == [
        "build", "standards", "spec", "architecture", "fix", "sweep", "suite", "finish"]


def test_the_dry_run_gives_the_suite_step_no_session(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    planned = planned_call(ran, "suite")
    assert "as the Suite file names it" in planned
    assert "claude -p" not in planned
    assert planned_checks(ran, "suite") == "suite-can-run suite-green"


def test_the_dry_run_gives_every_review_step_the_same_checks(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    for axis in ("standards", "spec", "architecture"):
        assert planned_checks(ran, axis) == "no-error command-loaded ticket-open axis-reported"


# Read off the plan rather than written out, so the two move together or this case fails.
def test_the_dry_run_gives_the_fix_step_the_checks_the_sweep_has(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    assert planned_checks(ran, "fix") == planned_checks(ran, "sweep")
    assert planned_checks(ran, "sweep") == "no-error command-loaded ticket-open"


def test_the_dry_run_resumes_the_build_session_for_the_fix_and_the_finish_alone(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    for step in ("build", "standards", "spec", "architecture", "sweep"):
        planned = planned_call(ran, step)
        assert planned != ""
        assert "--resume" not in planned
    for step in ("fix", "finish"):
        assert "--resume <build session>" in planned_call(ran, step)


def test_the_dry_run_gives_a_new_id_to_every_session_it_does_not_resume(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    for step in ("build", "standards", "spec", "architecture", "sweep"):
        assert "--session-id <new id>" in planned_call(ran, step)
    for step in ("fix", "finish"):
        assert "--session-id" not in planned_call(ran, step)


def test_the_dry_run_names_the_steps_that_can_be_nudged_and_no_others(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    for axis in ("standards", "spec", "architecture"):
        assert planned_nudges(ran, axis) == "up to 2, on axis-reported"
    assert planned_nudges(ran, "build") == "up to 2, on tree-changed"
    assert planned_nudges(ran, "finish") == "up to 2, on new-commit tree-clean ticket-closed"
    for step in ("fix", "sweep", "suite"):
        assert planned_nudges(ran, step) == ""


def test_a_closed_ticket_is_listed_and_given_no_plan(loop):
    given_the_tracker_holds(loop, (
        ("161", "closed", "TICKET: Already done"),
        ("168", "open", "TICKET: Still to do"),
    ))

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    assert "#161 [closed]" in said(ran)
    assert "ticket-161" not in said(ran)


def test_the_dry_run_starts_no_session_and_reaches_no_remote(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    base = git(loop.repo.origin, "rev-parse", "main").strip()

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    assert not runner.started("claude")
    assert git(loop.repo.origin, "rev-parse", "main").strip() == base
    assert not (loop.repo.work / ".claude" / "worktrees").exists()
    assert git(loop.repo.work, "for-each-ref", "--format=%(refname:short)",
               "refs/heads").strip() == "main"


def test_the_plan_is_written_to_the_log_as_well(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    assert "spec-loop/158/ticket-168" in loop.log()


# --- a restart over what a stopped run left behind ---------------------------

# One closed ticket takes the run past the loop body, so the restart is what these cases read.
def leftover(loop):
    return loop.repo.tree(SPEC, "ticket-164")


def given_a_leftover_worktree(loop, job):
    out, err = io.StringIO(), io.StringIO()
    assert ticket_worktree.main(
        ["open", loop.repo.work.as_posix(), SPEC, job], loop.runner, out, err, no_wait) == 0


# Git refuses a ref where a folder of refs sits, so this job's keep fails after the earlier ones.
def refuse_keeping(loop, job):
    git(loop.repo.work, "branch", "spec-loop/{}/{}-kept-1/blocker".format(SPEC, job), "main")


def test_a_restart_over_a_leftover_holding_work_carries_on(loop):
    given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    given_a_leftover_worktree(loop, "ticket-164")
    (leftover(loop) / "loose.txt").write_text("half done\n", encoding="utf-8", newline="\n")

    ran = loop.run(SPEC)

    assert ran.status == 0
    assert "END   spec #158" in said(ran)
    assert "uncommitted work" in said(ran)
    assert not leftover(loop).exists()
    git(loop.repo.work, "cat-file", "-e", "spec-loop/158/ticket-164-kept-1:loose.txt")


def test_a_restart_over_a_leftover_holding_nothing_carries_on(loop):
    given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    given_a_leftover_worktree(loop, "ticket-164")

    ran = loop.run(SPEC)

    assert ran.status == 0
    assert "END   spec #158" in said(ran)
    assert "nothing uncommitted" in said(ran)
    assert not leftover(loop).exists()
    assert loop.repo.has_branch(SPEC, "ticket-164-kept-1")


def test_the_log_names_the_job_and_the_branch_a_leftover_was_kept_on(loop):
    given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    given_a_leftover_worktree(loop, "ticket-164")

    ran = loop.run(SPEC)

    assert ran.status == 0
    assert "ticket-164" in loop.log()
    assert "spec-loop/158/ticket-164-kept-1" in loop.log()


# An open ticket, so a run that failed to stop would start a session and say so.
def test_a_keep_that_fails_part_way_still_names_the_job_it_kept(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_leftover_worktree(loop, "ticket-164")
    given_a_leftover_worktree(loop, "ticket-165")
    refuse_keeping(loop, "ticket-165")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "KEPT  ticket-164" in said(ran)
    assert "spec-loop/158/ticket-164-kept-1" in said(ran)
    assert "Nothing was started" in said(ran)
    assert not runner.started("claude")


def test_the_log_names_a_job_kept_before_a_keep_failed(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_leftover_worktree(loop, "ticket-164")
    given_a_leftover_worktree(loop, "ticket-165")
    refuse_keeping(loop, "ticket-165")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "spec-loop/158/ticket-164-kept-1" in loop.log()


def test_the_log_holds_the_reason_a_keep_failed(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_leftover_worktree(loop, "ticket-164")
    given_a_leftover_worktree(loop, "ticket-165")
    refuse_keeping(loop, "ticket-165")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "would not rename branch spec-loop/158/ticket-165" in loop.log()


def test_a_keep_that_succeeded_says_what_it_left_alone(loop):
    given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    stray = loop.repo.group(SPEC) / "stray"
    stray.mkdir(parents=True)
    (stray / "notes.txt").write_text("notes\n", encoding="utf-8", newline="\n")

    ran = loop.run(SPEC)

    assert ran.status == 0
    assert "{} is no worktree of its own, so it was left where it is".format(
        stray.as_posix()) in loop.log()


def test_a_keep_that_left_nothing_alone_says_nothing(loop):
    given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    given_a_leftover_worktree(loop, "ticket-164")

    ran = loop.run(SPEC)

    assert ran.status == 0
    assert "WARN" not in said(ran)
    assert "left where it is" not in said(ran)


# --- the review steps, run for real -----------------------------------------

def ticket_worktree_of(loop):
    return loop.repo.tree(SPEC, "ticket-168")


# The finish step cannot pass its checks here, so the loop stops with all three axes on record.
def test_the_review_steps_and_the_sweep_are_given_sessions_that_resume_nothing(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    for asked in ("/skillworks:review-standards 168", "/skillworks:review-spec 168",
                  "/skillworks:review-architecture 168", "/skillworks:comment-sweep"):
        call = call_asking(runner, asked)
        assert call is not None
        assert "--resume" not in call


def test_the_fix_step_and_the_finishing_step_each_run_under_their_own_flag(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert implement_flags(runner) == ["--stop-after-tests", "--fix", "--finish"]


def test_a_review_step_that_reported_nothing_stops_the_loop(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.says["review-standards"] = "I have finished looking."

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step standards failed check axis-reported" in said(ran)
    assert call_asking(runner, "/skillworks:review-spec") is None


def test_a_review_step_that_reported_no_findings_passes_its_check(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.says["review-standards"] = "## Standards. No findings on this change."

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert call_asking(runner, "/skillworks:review-spec 168") is not None
    assert "step standards failed" not in said(ran)


# A bare name is what loads from the project skills folder, so it is not the Plugin's skill.
def test_a_step_whose_session_loaded_the_bare_name_did_not_load_the_plugin_skill(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.bare.add("review-spec")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step spec failed check command-loaded" in said(ran)
    reasons = (loop.records() / "ticket-168-spec.err").read_text(encoding="utf-8")
    assert '"/skillworks:review-spec 168" did not load as a command' in reasons
    assert call_asking(runner, "/skillworks:implement 168 --fix") is None


def test_a_review_step_that_errored_stops_the_loop_and_keeps_the_worktree(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.refuses.add("review-spec")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step spec exited non-zero" in said(ran)
    assert ticket_worktree_of(loop).as_posix() in said(ran)
    assert ticket_worktree_of(loop).is_dir()
    assert call_asking(runner, "/skillworks:implement 168 --fix") is None
    assert call_asking(runner, "/skillworks:implement 168 --finish") is None


# --- the reports reaching the fix step --------------------------------------

def test_the_fix_step_is_given_what_all_three_axes_found(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_three_axes_with_something_to_say(given_sessions_that_report(loop))

    ran = loop.run(SPEC)

    assert ran.status == 1
    asked = prompt_asking(runner, "/skillworks:implement 168 --fix")
    assert "The name box says nothing." in asked
    assert "The third criterion is unmet." in asked
    assert "The arrow points the wrong way." in asked


def test_the_fix_step_is_told_which_axis_each_report_came_from(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_three_axes_with_something_to_say(given_sessions_that_report(loop))

    ran = loop.run(SPEC)

    assert ran.status == 1
    for axis in ("standards", "spec", "architecture"):
        assert "## The {} axis reported".format(axis) in prompt_asking(
            runner, "/skillworks:implement 168 --fix")


# The reports stop at `fix`, which reconciles, so carrying them on would be the same work twice.
def test_the_finishing_step_is_given_no_axis_report(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_three_axes_with_something_to_say(given_sessions_that_report(loop))

    ran = loop.run(SPEC)

    assert ran.status == 1
    asked = prompt_asking(runner, "/skillworks:implement 168 --finish")
    assert asked != ""
    assert "axis reported" not in asked


def test_the_fix_step_and_the_finishing_step_both_resume_the_build_session(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    built = call_asking(runner, "/skillworks:implement 168 --stop-after-tests")
    build_session = built[built.index("--session-id") + 1]
    for mark in ("/skillworks:implement 168 --fix", "/skillworks:implement 168 --finish"):
        call = call_asking(runner, mark)
        assert call[call.index("--resume") + 1] == build_session


# --- the id each Session is given -------------------------------------------

def new_session_calls(runner):
    return [call for call in session_calls(runner) if "--resume" not in call]


def id_given(call):
    return call[call.index("--session-id") + 1]


def test_every_new_session_is_given_an_id_of_its_own(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    ids = [id_given(call) for call in new_session_calls(runner)]
    assert len(ids) == 5
    assert len(set(ids)) == len(ids)
    for given in ids:
        assert str(uuid.UUID(given)) == given


def test_each_id_is_in_the_record_before_its_session_starts(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    calls = step_calls(runner)
    assert len(calls) == len(sessions.record_at_start) == 7
    for call, held in zip(calls, sessions.record_at_start):
        if "--resume" not in call:
            assert held[-1] == id_given(call)


def test_a_resumed_step_is_given_no_new_id_and_adds_nothing_to_the_record(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    for mark in ("/skillworks:implement 168 --fix", "/skillworks:implement 168 --finish"):
        assert "--session-id" not in call_asking(runner, mark)
    assert sessions_recorded(ticket_worktree_of(loop)) == [
        id_given(call) for call in new_session_calls(runner)]


def test_the_record_sits_in_the_worktree_git_folder_and_git_never_sees_it(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    tree = ticket_worktree_of(loop)
    assert sessions_record(tree).is_file()
    seen = git(tree, "status", "--porcelain", "--ignored", "--untracked-files=all")
    assert "built.txt" in seen
    assert ticket_worktree.SESSIONS_RECORD not in seen


def test_a_missing_axis_report_stops_the_loop_before_the_fix_step(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    given_a_report_lost_after_the_last_axis(loop, sessions, "standards")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step fix was short of a review axis report" in said(ran)
    assert call_asking(runner, "/skillworks:implement 168 --fix") is None


def test_a_missing_axis_report_names_the_axis_it_came_from(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    given_a_report_lost_after_the_last_axis(loop, sessions, "standards")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "the standards axis left no report" in (
        loop.records() / "ticket-168-fix.err").read_text(encoding="utf-8")


# --- the Edit each axis made ------------------------------------------------

def test_an_axis_that_changed_nothing_has_an_edit_saying_it_changed_nothing(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert edit_of(loop, "standards") == "changed nothing"
    assert call_asking(runner, "/skillworks:review-spec 168") is not None


def test_every_axis_leaves_its_edit_in_the_log(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    for axis in ("standards", "spec", "architecture"):
        assert edit_of(loop, axis) != ""


def test_every_axis_leaves_its_edit_on_disk_under_its_own_name(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    for axis in ("standards", "spec", "architecture"):
        held = loop.records() / "ticket-168-{}.edit".format(axis)
        assert held.read_text(encoding="utf-8").strip() == "changed nothing"


def test_an_axis_that_added_a_file_has_it_named_in_its_edit(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_writes(
        given_sessions_that_report(loop), "standards", "named.txt", "the name box\n")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert edit_of(loop, "standards") == "changed named.txt"


# The build step already left built.txt, so only a reading of the bytes can see this edit.
def test_an_axis_that_edited_a_file_the_build_changed_still_has_an_edit(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_writes(
        given_sessions_that_report(loop), "spec", "built.txt", "built, then mended\n")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert edit_of(loop, "spec") == "changed built.txt"


# Without the driver taking its reading the same way either side, this would read as an edit.
def test_an_axis_that_only_ran_the_command_its_brief_opens_with_changed_nothing(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_only_stages(given_sessions_that_report(loop), "standards")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert edit_of(loop, "standards") == "changed nothing"


def test_the_fix_step_is_told_what_each_axis_changed(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    given_an_axis_that_writes(sessions, "standards", "named.txt", "the name box\n")
    given_an_axis_that_writes(sessions, "architecture", "built.txt", "built, then turned round\n")

    ran = loop.run(SPEC)

    assert ran.status == 1
    asked = prompt_asking(runner, "/skillworks:implement 168 --fix")
    assert "The standards axis changed named.txt." in asked
    assert "The spec axis changed nothing." in asked
    assert "The architecture axis changed built.txt." in asked


def test_an_axis_that_edits_does_not_stop_the_loop(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_writes(
        given_sessions_that_report(loop), "standards", "named.txt", "the name box\n")

    ran = loop.run(SPEC)

    assert "step standards failed" not in said(ran)
    assert call_asking(runner, "/skillworks:review-spec 168") is not None
    assert call_asking(runner, "/skillworks:implement 168 --fix") is not None


# --- the Nudge a review that stopped short is given --------------------------

STOPPED_SHORT = "I will wait for the tests to finish."
BACKGROUND_LINE = ("Any command you left in the background was stopped when your last turn "
                   "ended, so its output is not complete. Run it again in the foreground.")
BLOCKER_LINE = "If something blocks you, say what it is."


def given_an_axis_that_stops_short(sessions, axis, *nudged):
    sessions.says["review-" + axis] = STOPPED_SHORT
    sessions.nudged["review-" + axis] = list(nudged)


def nudge_calls(runner):
    return [call for call in session_calls(runner) if not call[2].startswith("/")]


def nudge_lines(loop):
    return [line for line in loop.log().split("\n") if line.split()[1:2] == ["NUDGE"]]


# The finish never commits unless a case says so, so it is Nudged too, and a case names its step.
def failed_in(loop, step):
    return [line.split("failed ", 1)[1] for line in nudge_lines(loop)
            if line.split()[3] == step]


def test_a_review_that_reports_on_its_first_nudge_passes_and_the_loop_goes_on(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_stops_short(
        given_sessions_that_report(loop), "standards", "## Standards. Nothing found.")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step standards failed" not in said(ran)
    assert len(failed_in(loop, "standards")) == 1
    assert call_asking(runner, "/skillworks:review-spec 168") is not None
    assert call_asking(runner, "/skillworks:implement 168 --fix") is not None


def test_a_review_still_short_after_two_nudges_stops_the_loop_and_keeps_the_worktree(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_stops_short(given_sessions_that_report(loop), "standards")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step standards failed check axis-reported after 2 Nudges" in said(ran)
    assert len(nudge_calls(runner)) == 2
    assert ticket_worktree_of(loop).as_posix() in said(ran)
    assert ticket_worktree_of(loop).is_dir()
    assert call_asking(runner, "/skillworks:review-spec 168") is None


def test_a_review_that_errored_is_never_nudged(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    given_an_axis_that_stops_short(sessions, "standards")
    sessions.errors.add("review-standards")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step standards failed check no-error" in said(ran)
    assert nudge_calls(runner) == []


def test_a_review_that_loaded_no_command_is_never_nudged(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    given_an_axis_that_stops_short(sessions, "spec")
    sessions.bare.add("review-spec")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step spec failed check command-loaded" in said(ran)
    assert nudge_calls(runner) == []


def test_a_review_that_found_its_ticket_closed_is_never_nudged(loop, runner):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    given_an_axis_that_stops_short(sessions, "standards")
    sessions.then["review-standards"] = lambda: tracker.closed.add("168")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step standards failed check ticket-open" in said(ran)
    assert nudge_calls(runner) == []


def test_a_review_that_exited_non_zero_is_never_nudged(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.refuses.add("review-standards")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step standards exited non-zero" in said(ran)
    assert nudge_calls(runner) == []


def test_a_nudge_resumes_the_reviews_own_session_and_not_the_build_session(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_stops_short(given_sessions_that_report(loop), "spec")

    loop.run(SPEC)

    reviewed = id_given(call_asking(runner, "/skillworks:review-spec 168"))
    built = id_given(call_asking(runner, "/skillworks:implement 168 --stop-after-tests"))
    nudges = nudge_calls(runner)
    assert len(nudges) == 2
    for call in nudges:
        assert call[call.index("--resume") + 1] == reviewed
        assert "--session-id" not in call
    assert reviewed != built


def test_a_nudge_runs_as_the_session_it_resumes_ran(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_stops_short(given_sessions_that_report(loop), "spec")

    loop.run(SPEC)

    made = [call for call in runner.made if call.args[0] == "claude"]
    first = next(call for call in made if call.args[2].startswith("/skillworks:review-spec"))
    for nudge in (call for call in made if not call.args[2].startswith("/")):
        assert nudge.args[-4:] == first.args[-4:]
        assert nudge.env == first.env
        assert nudge.where == first.where


def test_a_nudge_names_what_is_owed_then_the_background_then_the_blocker(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_stops_short(given_sessions_that_report(loop), "architecture")

    loop.run(SPEC)

    asked = nudge_calls(runner)[0][2].split("\n")
    assert "## Architecture" in asked[0]
    assert asked[1:] == [BACKGROUND_LINE, BLOCKER_LINE, ""]


def test_the_log_has_one_nudge_line_for_each_nudge(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_stops_short(given_sessions_that_report(loop), "standards")

    loop.run(SPEC)

    lines = nudge_lines(loop)
    assert len(lines) == 2
    for at, line in enumerate(lines, start=1):
        assert "#168 standards" in line
        assert "{} of 2".format(at) in line
        assert "axis-reported" in line


def test_the_fix_step_reads_the_report_the_nudged_review_wrote(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_stops_short(given_sessions_that_report(loop), "standards",
                                   "I read the output.", "## Standards. The name box says nothing.")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert len(failed_in(loop, "standards")) == 2
    asked = prompt_asking(runner, "/skillworks:implement 168 --fix")
    assert "The name box says nothing." in asked
    assert STOPPED_SHORT not in asked
    assert "The name box says nothing." in (
        loop.records() / "ticket-168-standards.json").read_text(encoding="utf-8")


def test_a_review_edit_spans_its_session_and_every_nudge_of_it(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    given_an_axis_that_stops_short(sessions, "standards", "## Standards. Nothing found.")
    given_an_axis_that_writes(sessions, "standards", "named.txt", "the name box\n")
    sessions.writes_when_nudged["review-standards"] = ("nudged.txt", "after the Nudge\n")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert edit_of(loop, "standards") == "changed named.txt, nudged.txt"
    assert len([line for line in loop.log().split("\n") if " EDIT " in line
                and " standards " in line]) == 1


def test_a_nudged_session_adds_nothing_to_the_record_of_sessions(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_stops_short(given_sessions_that_report(loop), "spec", "## Spec. Nothing.")

    loop.run(SPEC)

    assert len(failed_in(loop, "spec")) == 1
    assert sessions_recorded(ticket_worktree_of(loop)) == [
        id_given(call) for call in new_session_calls(runner)]


# --- the Nudge a build or a finish that stopped short is given --------------

BUILD = "implement 168 --stop-after-tests"
FINISH = "implement 168 --finish"


def built_on_nudge(runner):
    def build():
        (Path(runner.where) / "built.txt").write_text("built\n", encoding="utf-8", newline="\n")
    return build


def committed(runner):
    def commit():
        git(runner.where, "add", "-A")
        git(runner.where, "commit", "--quiet", "-m", "Built\n\nTicket: #168")
    return commit


def closed(tracker):
    return lambda: tracker.closed.add("168")


def all_of(*done):
    def every():
        for does in done:
            does()
    return every


def test_a_build_that_changed_nothing_is_nudged_and_goes_on_when_the_nudge_changes_it(
        loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.builds = False
    sessions.when_nudged[BUILD] = built_on_nudge(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step build failed" not in said(ran)
    assert failed_in(loop, "build") == ["tree-changed"]
    assert call_asking(runner, "/skillworks:review-standards 168") is not None


def test_a_build_that_still_changed_nothing_after_two_nudges_stops_the_loop(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.builds = False

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step build failed check tree-changed after 2 Nudges" in said(ran)
    assert len(nudge_calls(runner)) == 2
    assert call_asking(runner, "/skillworks:review-standards 168") is None


def test_a_finish_that_did_not_close_its_ticket_is_nudged(loop, runner):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = committed(runner)
    sessions.when_nudged[FINISH] = closed(tracker)

    ran = loop.run(SPEC)

    assert "step finish failed" not in said(ran)
    assert failed_in(loop, "finish") == ["ticket-closed"]


def test_a_finish_that_did_not_commit_is_nudged(loop, runner):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = closed(tracker)
    sessions.when_nudged[FINISH] = committed(runner)

    ran = loop.run(SPEC)

    assert "step finish failed" not in said(ran)
    assert failed_in(loop, "finish") == ["new-commit tree-clean"]


def test_a_finish_that_left_the_tree_unclean_is_nudged(loop, runner):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(committed(runner), closed(tracker),
                                   lambda: (Path(runner.where) / "stray.txt").write_text(
                                       "left\n", encoding="utf-8", newline="\n"))
    sessions.when_nudged[FINISH] = lambda: (Path(runner.where) / "stray.txt").unlink()

    ran = loop.run(SPEC)

    assert "step finish failed" not in said(ran)
    assert failed_in(loop, "finish") == ["tree-clean"]


def test_a_finish_still_owing_work_after_two_nudges_stops_the_loop(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step finish failed check new-commit after 2 Nudges" in said(ran)
    assert failed_in(loop, "finish") == ["new-commit tree-clean ticket-closed"] * 2
    assert ticket_worktree_of(loop).is_dir()


def test_a_build_nudge_names_what_it_owes_then_the_background_then_the_blocker(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop).builds = False

    loop.run(SPEC)

    asked = nudge_calls(runner)[0][2].split("\n")
    assert "changed nothing" in asked[0]
    assert asked[1:] == [BACKGROUND_LINE, BLOCKER_LINE, ""]


def test_a_finish_nudge_names_each_failed_check_on_a_line_of_its_own(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    loop.run(SPEC)

    asked = nudge_calls(runner)[0][2].split("\n")
    assert "not committed" in asked[0]
    assert "uncommitted changes" in asked[1]
    assert "#168 is still open" in asked[2]
    assert asked[3:] == [BACKGROUND_LINE, BLOCKER_LINE, ""]


def test_a_finish_nudge_resumes_the_finish_sessions_own_id_and_not_the_build_session(
        loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.forks.add("implement")

    loop.run(SPEC)

    built = id_given(call_asking(runner, "/skillworks:" + BUILD))
    finished = json.loads((loop.records() / "ticket-168-finish.json").read_text(
        encoding="utf-8"))["session_id"]
    nudges = nudge_calls(runner)
    assert len(nudges) == 2
    assert finished != built
    for call in nudges:
        assert call[call.index("--resume") + 1] == finished


# --- the suite the driver runs itself ---------------------------------------

SOLUTION = "dotnet test Skillworks.slnx"


def suite_output(loop):
    return (loop.records() / "ticket-168-suite.out").read_text(encoding="utf-8")


def test_the_driver_runs_the_suite_and_asks_no_session_to(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert runner.built(SOLUTION)
    assert len(step_calls(runner)) == 7


def test_the_suite_runs_in_the_ticket_worktree(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert [call.where for call in runner.made if call.args[0] == "dotnet"] == [
        ticket_worktree_of(loop).as_posix()]


def test_the_suite_runs_after_the_sweep_and_a_green_one_runs_the_finishing_step(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert call_at(runner, "/skillworks:comment-sweep") < call_at(runner, SOLUTION)
    assert call_at(runner, SOLUTION) < call_at(runner, "/skillworks:implement 168 --finish")


def test_the_suite_keeps_what_it_said_with_the_other_step_records(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "the solution passed" in suite_output(loop)


def test_a_red_suite_stops_the_loop_before_the_finishing_step(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    runner.stub("dotnet", says="a test failed", status=1)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step suite failed check suite-green" in said(ran)
    assert call_asking(runner, "/skillworks:implement 168 --finish") is None


def test_a_red_suite_keeps_what_it_said_and_the_worktree_it_said_it_in(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    loop.runner.stub("dotnet", says="a test failed", status=1)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "a test failed" in suite_output(loop)
    assert ticket_worktree_of(loop).as_posix() in said(ran)
    assert ticket_worktree_of(loop).is_dir()


# Main moves while the ticket is built, and measured from main its new file would wake a check.
def test_the_suite_is_woken_by_the_change_since_the_worktree_was_cut(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_suite_on_main(loop, check("dotnet", "test", "Skillworks.slnx", when=["built.txt"]),
                          check("npm", "test", when=["later.txt"]))
    runner.stub("dotnet", says="the solution passed\n")
    runner.stub("npm")
    sessions = Sessions(loop.repo, runner)

    def main_moves():
        loop.repo.advance_origin("later")
        git(loop.repo.work, "fetch", "--quiet", "origin")
    sessions.then["--stop-after-tests"] = main_moves

    loop.run(SPEC)

    assert suite_output(loop).endswith(
        "the solution passed\n"
        "npm test did not run, because the change touches none of the paths it names\n")


def test_a_machine_short_of_what_the_suite_needs_stops_the_loop_naming_it(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    loop.runner.stub("docker", says="the daemon is not running", status=1)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "Docker" in said(ran)
    assert "the daemon is not running" in said(ran)


# No session can start Docker, so handing this to one would spend a step on a failure it cannot mend.
def test_a_machine_short_of_what_the_suite_needs_starts_no_session_to_mend_it(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    runner.stub("docker", says="the daemon is not running", status=1)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert len(session_calls(runner)) == 6
    assert not runner.started("dotnet")


def test_the_loop_says_which_step_the_suite_is(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "STEP  #168 suite" in loop.log()


# --- a red suite run a second time ------------------------------------------

# The Suite file says how often red runs, so a repo with no flakes pays for no second run.
def test_with_no_setting_a_red_suite_is_believed_on_its_first_run(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "suite run 2" not in loop.log()
    assert "a Span test failed" in prompts_asking(runner, "/skillworks:implement 168 --fix")[1]


# The second run falls through to the passing stub, so one case holds a flake and nothing else.
def given_a_suite_red_on_its_first_run_alone(runner):
    runner.refuse(SOLUTION, "a Span test failed", times=1)


def given_a_suite_red_on_every_run(runner):
    runner.stub("dotnet", says="a test failed", status=1)


def test_a_red_suite_is_run_a_second_time_before_it_is_believed(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert len(runner.started("dotnet")) == 2


def test_a_green_first_run_is_never_run_again(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert len(runner.started("dotnet")) == 1


def test_a_second_run_that_passes_carries_the_loop_on_to_the_finishing_step(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert call_asking(runner, "/skillworks:implement 168 --finish") is not None
    assert "failed check suite-green" not in said(ran)


def test_the_log_names_which_of_the_two_runs_each_one_is(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "suite run 1 went red" in loop.log()
    assert "suite run 2 went red" in loop.log()


def test_the_log_names_the_one_run_a_green_suite_took(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "suite run 1 passed" in loop.log()
    assert "suite run 2" not in loop.log()


def test_a_second_run_that_passes_says_the_first_was_a_flake(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "suite run 2 passed, so the red before it was a flake" in loop.log()


def test_both_runs_are_kept_where_the_other_step_records_are(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "a Span test failed" in suite_output(loop)
    assert "the solution passed" in suite_output(loop)


# A second run cannot start Docker either, so nothing is spent proving that twice.
def test_a_machine_short_of_what_the_suite_needs_is_never_run_again(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    runner.stub("docker", says="the daemon is not running", status=1)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert len(runner.started("docker")) == 1


# --- a red suite goes round once --------------------------------------------

# Red on both runs is the ticket's own, and a third run is the one the circuit leads back to.
def given_a_suite_red_until_the_loop_goes_round(runner):
    runner.refuse(SOLUTION, "the runs before the circuit failed", times=2)


def test_red_on_both_runs_goes_to_fix_then_sweep_then_suite(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_until_the_loop_goes_round(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    went_round = every_call_at(runner, "/skillworks:implement 168 --fix")[1]
    swept = every_call_at(runner, "/skillworks:comment-sweep")[1]
    assert went_round < swept < every_call_at(runner, SOLUTION)[2]


def test_the_failure_output_reaches_the_fix_prompt(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "a test failed" in prompts_asking(runner, "/skillworks:implement 168 --fix")[1]


def test_the_fix_step_before_the_suite_is_told_of_no_failure(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "a test failed" not in prompts_asking(runner, "/skillworks:implement 168 --fix")[0]


def test_the_retry_runs_under_the_fix_flag_and_no_other(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_until_the_loop_goes_round(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert implement_flags(runner) == [
        "--stop-after-tests", "--fix", "--fix", "--finish"]


def test_a_suite_green_after_the_circuit_carries_the_loop_on(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_until_the_loop_goes_round(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert call_asking(runner, "/skillworks:implement 168 --finish") is not None
    assert "failed check suite-green" not in said(ran)


def test_a_second_circuit_never_happens(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert len(prompts_asking(runner, "/skillworks:implement 168 --fix")) == 2
    assert len(prompts_asking(runner, "/skillworks:comment-sweep")) == 2
    assert len(runner.started("dotnet")) == 4


def test_red_after_the_circuit_stops_the_loop_before_the_finishing_step(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step suite failed check suite-green" in said(ran)
    assert call_asking(runner, "/skillworks:implement 168 --finish") is None


def test_a_stop_after_the_circuit_leaves_the_worktree_and_names_it_in_the_log(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert ticket_worktree_of(loop).is_dir()
    assert ticket_worktree_of(loop).as_posix() in loop.log()


def test_the_log_says_the_loop_went_round_and_where_it_went(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "goes round once: fix, then sweep, then suite" in loop.log()


def test_the_record_keeps_what_the_suite_said_on_both_sides_of_the_circuit(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_until_the_loop_goes_round(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert suite_output(loop).count("the runs before the circuit failed") == 2
    assert "the solution passed" in suite_output(loop)


# --- the passing suite reaching the finishing step ---------------------------

def finish_prompt(runner):
    return prompt_asking(runner, "/skillworks:implement 168 --finish")


def test_the_finishing_step_is_handed_the_output_of_the_suite_that_passed(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "the solution passed" in finish_prompt(runner)


def test_the_finishing_step_is_handed_the_line_of_each_check_that_did_not_run(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_suite_on_main(loop, check("dotnet", "test", "Skillworks.slnx"),
                          check("npm", "test", when=["untouched.txt"]))
    runner.stub("dotnet", says="the solution passed\n")
    runner.stub("npm")
    Sessions(loop.repo, runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "the solution passed" in finish_prompt(runner)
    assert ("npm test did not run, because the change touches none of the paths it names"
            in finish_prompt(runner))


# One step owns the gate, so a Session cannot report a result the driver never saw.
def test_the_finishing_step_is_told_the_driver_ran_the_suite_and_to_run_none(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "The driver ran the whole suite" in finish_prompt(runner)
    assert "run no tests" in finish_prompt(runner)


def test_the_suite_runs_before_the_finishing_step(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert call_at(runner, SOLUTION) < call_at(runner, "/skillworks:implement 168 --finish")


# A flake spends a run, and the run that proved the work is the one the closing comment names.
def test_the_finishing_step_is_handed_the_run_that_passed_and_not_the_one_that_failed(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "the solution passed" in finish_prompt(runner)
    assert "a Span test failed" not in finish_prompt(runner)


# --- the Denials a stop names -----------------------------------------------

BYPASS = "spec-loop 158 --bypass"

A_DENIED_WRITE = {"tool_name": "Write", "tool_use_id": "toolu_1",
                   "tool_input": {"file_path": ".claude/rules/words.md", "content": "x" * 500}}
A_DENIED_COMMAND = {"tool_name": "Bash", "tool_use_id": "toolu_2",
                     "tool_input": {"command": "rm -rf .claude/worktrees"}}


# The finishing Session never commits here, so every case stops at the finishing step.
def given_a_finish_that_was_denied(sessions, *denials):
    sessions.denials["implement"] = list(denials)


def test_a_stop_after_denials_gives_the_way_past_them(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_finish_that_was_denied(given_sessions_that_report(loop), A_DENIED_WRITE)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step finish failed check new-commit" in said(ran)
    assert "Denial" in said(ran)
    assert BYPASS in said(ran)
    assert "SPEC_LOOP_PERMISSION_MODE" not in said(ran)
    assert ticket_worktree_of(loop).as_posix() in said(ran)


def test_a_stop_names_each_denial_by_its_tool_and_the_start_of_its_input(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_finish_that_was_denied(given_sessions_that_report(loop),
                                   A_DENIED_WRITE, A_DENIED_COMMAND)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert 'Write {"file_path": ".claude/rules/words.md"' in said(ran)
    assert 'Bash {"command": "rm -rf .claude/worktrees"}' in said(ran)
    assert "x" * 500 not in said(ran)


def test_the_denials_and_the_way_past_them_reach_the_log_as_well(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_finish_that_was_denied(given_sessions_that_report(loop), A_DENIED_WRITE)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert 'Write {"file_path": ".claude/rules/words.md"' in loop.log()
    assert BYPASS in loop.log()


def test_a_stop_with_no_denials_gives_no_way_past_them(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step finish failed check new-commit" in said(ran)
    assert BYPASS not in said(ran) + loop.log()
    assert "Denial" not in said(ran) + loop.log()


def test_a_stop_with_an_empty_list_of_denials_gives_no_way_past_them(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_finish_that_was_denied(given_sessions_that_report(loop))

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert BYPASS not in said(ran) + loop.log()


def test_a_stop_with_an_empty_result_gives_no_way_past_denials(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop).refuses.add("review-spec")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step spec exited non-zero" in said(ran)
    assert BYPASS not in said(ran) + loop.log()


def test_a_stop_with_a_result_that_is_not_json_gives_no_way_past_denials(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop).garbles.add("review-standards")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step standards failed check no-error" in said(ran)
    assert BYPASS not in said(ran) + loop.log()


def test_a_stop_of_the_step_the_driver_runs_itself_gives_no_way_past_denials(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_finish_that_was_denied(given_sessions_that_report(loop), A_DENIED_WRITE)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step suite failed check suite-green" in said(ran)
    assert BYPASS not in said(ran) + loop.log()


# --- the Parent each Session names -------------------------------------------

PARENT = "skillworks.parent.session.id=parent-session"


def changes_given_to_sessions(runner):
    return [call.env or {} for call in runner.made if call.args[0] == "claude"]


def test_every_step_session_names_the_session_that_started_the_driver(loop, runner, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "parent-session")
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    asked = [call[2].split(" ")[0] for call in step_calls(runner)]
    assert asked == ["/skillworks:" + name for name in (
        "implement", "review-standards", "review-spec", "review-architecture",
        "implement", "comment-sweep", "implement")]
    for changes in changes_given_to_sessions(runner):
        assert changes.get("OTEL_RESOURCE_ATTRIBUTES") == PARENT


def test_the_drift_session_names_the_session_that_started_the_driver(loop, runner, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "parent-session")
    given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    given_sessions_that_report(loop)

    loop.run(SPEC)

    assert call_asking(runner, "/skillworks:spec-drift") is not None
    assert changes_given_to_sessions(runner)[-1].get("OTEL_RESOURCE_ATTRIBUTES") == PARENT


def test_attributes_already_set_are_kept_and_the_parent_is_added(loop, runner, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "parent-session")
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "team=studio,host.kind=laptop")
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    loop.run(SPEC)

    changes = changes_given_to_sessions(runner)
    assert changes
    for change in changes:
        assert change.get("OTEL_RESOURCE_ATTRIBUTES") == "team=studio,host.kind=laptop," + PARENT


def test_a_driver_started_by_hand_names_no_parent(loop, runner, monkeypatch):
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "team=studio")
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    loop.run(SPEC)

    changes = changes_given_to_sessions(runner)
    assert changes
    for change in changes:
        assert "OTEL_RESOURCE_ATTRIBUTES" not in change


# --- the Bash limit each Session runs with -----------------------------------

FORTY_FIVE_MINUTES_MS = "2700000"


def test_every_session_runs_with_a_45_minute_bash_limit_and_background_tasks_on(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    loop.run(SPEC)

    calls = [call for call in runner.made if call.args[0] == "claude"]
    assert any("--resume" in call.args for call in calls)
    assert any("--resume" not in call.args for call in calls)
    for call in calls:
        changes = call.env or {}
        assert changes.get("BASH_DEFAULT_TIMEOUT_MS") == FORTY_FIVE_MINUTES_MS
        assert changes.get("BASH_MAX_TIMEOUT_MS") == FORTY_FIVE_MINUTES_MS
        assert "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS" not in changes


# --- the permission mode a run is in -----------------------------------------

RESOLVE = "/skillworks:resolve-conflict"


# The build and main both add the same file, so the landing asks the build Session to resolve it.
def given_a_run_that_reaches_a_landing_conflict(loop):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(
        committed(loop.runner), closed(tracker),
        lambda: loop.repo.push_from_elsewhere("built.txt", "theirs", "Somebody else's built"))


def modes_of_sessions(runner):
    calls = session_calls(runner)
    assert call_asking(runner, RESOLVE) is not None, "the landing asked no Session to resolve"
    return {call[call.index("--permission-mode") + 1] for call in calls}


def loop_line(loop):
    return next(line for line in loop.log().split("\n") if " LOOP " in line)


def test_bypass_runs_every_session_and_the_landing_in_bypass_mode(loop, runner):
    given_a_run_that_reaches_a_landing_conflict(loop)

    ran = loop.run(SPEC, "--bypass")

    assert ran.status == 1
    assert modes_of_sessions(runner) == {"bypassPermissions"}
    assert "bypassPermissions" in loop_line(loop)


def test_with_no_flag_and_no_setting_every_session_runs_in_accept_edits(loop, runner):
    given_a_run_that_reaches_a_landing_conflict(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert modes_of_sessions(runner) == {"acceptEdits"}
    assert "acceptEdits" in loop_line(loop)


def test_the_setting_still_sets_the_mode_of_every_session(loop, runner, monkeypatch):
    monkeypatch.setenv("SPEC_LOOP_PERMISSION_MODE", "plan")
    given_a_run_that_reaches_a_landing_conflict(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert modes_of_sessions(runner) == {"plan"}
    assert "plan" in loop_line(loop)


def test_the_flag_wins_over_the_setting(loop, runner, monkeypatch):
    monkeypatch.setenv("SPEC_LOOP_PERMISSION_MODE", "acceptEdits")
    given_a_run_that_reaches_a_landing_conflict(loop)

    ran = loop.run(SPEC, "--bypass")

    assert ran.status == 1
    assert modes_of_sessions(runner) == {"bypassPermissions"}
    assert "bypassPermissions" in loop_line(loop)


@pytest.mark.parametrize("flags", [("--bypass", "--dry-run"), ("--dry-run", "--bypass")])
def test_bypass_and_the_dry_run_go_together_in_either_order(loop, runner, flags):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, *flags)

    assert ran.status == 0, said(ran)
    assert "DRY   no session was run" in ran.out
    assert session_calls(runner) == []


@pytest.mark.parametrize("flags", [("--bypas",), ("--bypass", "--dry-run", "--later")])
def test_an_unknown_argument_still_prints_the_usage(loop, flags):
    ran = loop.run(SPEC, *flags)

    assert ran.status == 64
    assert ran.err == spec_loop.USAGE


def test_the_agentic_loop_document_names_the_bypass_flag():
    text = (ROOT / "docs/agentic-development/agentic-loop.md").read_text(encoding="utf-8")

    assert "--bypass" in text


# --- what the landing says, and when ----------------------------------------

WAITS = "waits for the Turn"

STAMP = r"[0-9]{2}:[0-9]{2}:[0-9]{2} "


def given_a_run_that_lands(loop):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(committed(loop.runner), closed(tracker))


# Held in this process, since the OS turns away a second handle on the Turn's file even from here.
def holding_the_turn(loop):
    turn = land_ticket.Turn.of(Subprocess(), loop.repo.work.as_posix(), "spec #200 ticket #199")
    turn.take(lambda holder: None)
    return turn


# Each write is read as it lands, so a case can act the moment the loop says something.
class Heard(io.StringIO):
    def __init__(self, mark):
        super().__init__()
        self.mark = mark
        self.seen = threading.Event()

    def write(self, said):
        written = super().write(said)
        if self.mark in said:
            self.seen.set()
        return written


# The landing blocks on the Turn, so the loop runs beside the case that holds it.
class Beside:
    def __init__(self, loop, *args):
        self.out = Heard(WAITS)
        self.err = io.StringIO()
        self.status = None
        self.thread = threading.Thread(target=self.run, args=(loop, args), daemon=True)
        self.thread.start()

    def run(self, loop, args):
        try:
            self.status = spec_loop.main(
                [str(a) for a in args], loop.runner, self.out, self.err, loop.waits.append)
        finally:
            # A loop that ended without the line must fail the case, not hang it.
            self.out.seen.set()

    def heard(self):
        self.out.seen.wait()

    def ended(self):
        self.thread.join()
        return Ran(self.status, self.out.getvalue(), self.err.getvalue())


def landing_output(loop):
    return (loop.records() / "ticket-168-land.out").read_text(encoding="utf-8")


def stamped_in_log(loop, line):
    return re.search("^" + STAMP + re.escape(line) + "$", loop.log(), re.MULTILINE) is not None


def test_a_loop_waiting_for_the_turn_says_so_in_its_log_while_it_waits(loop):
    given_a_run_that_lands(loop)
    base = git(loop.repo.origin, "rev-parse", "main").strip()
    turn = holding_the_turn(loop)
    try:
        run = Beside(loop, SPEC)
        run.heard()

        assert stamped_in_log(loop, "note  #168 waits for the Turn, which spec #200 ticket #199 holds")
        assert git(loop.repo.origin, "rev-parse", "main").strip() == base
    finally:
        turn.let_go()
    ran = run.ended()

    assert ran.status == 0, said(ran)
    assert "DONE  #168" in loop.log()
    assert git(loop.repo.origin, "log", "-1", "--format=%s", "main").strip() == "Built"


def test_every_line_of_a_landing_that_waited_carries_the_time_in_the_log(loop):
    given_a_run_that_lands(loop)
    turn = holding_the_turn(loop)
    try:
        run = Beside(loop, SPEC)
        run.heard()
    finally:
        turn.let_go()
    run.ended()

    lines = landing_output(loop).splitlines()
    assert len(lines) == 2
    for line in lines:
        assert stamped_in_log(loop, line), line


def test_the_landing_output_of_a_ticket_that_lands_holds_what_the_landing_said(loop):
    given_a_run_that_lands(loop)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    assert re.fullmatch(
        "ok    #168 landed on main as [0-9a-f]+ in 1 try, holding the Turn for its push\n",
        landing_output(loop))


def test_the_landing_output_of_a_ticket_that_stops_holds_what_the_landing_said(loop):
    given_a_run_that_lands(loop)
    loop.repo.refuse_pushes()

    ran = loop.run(SPEC)

    assert ran.status == 1
    held = landing_output(loop)
    assert held.startswith("FAIL  #168 could not be pushed. Nothing was pushed. git said:\n")
    assert "pre-receive hook declined" in held
    assert held.endswith("\n")
    assert not re.search("^" + STAMP, held, re.MULTILINE)
    for line in held.splitlines():
        assert stamped_in_log(loop, line), line


# --- the claim --------------------------------------------------------------

def test_a_ticket_is_claimed_and_read_back_after_a_wait(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert loop.waits == [3]
    assert runner.built("issue edit 168 --add-assignee @me")


# --- the documents held to the step list -------------------------------------

# An ADR records what was decided on a day, so it keeps its old list and is not held here.
LIVE_DOCUMENTS = (
    "docs/agentic-development/agentic-loop.md",
    "plugins/skillworks/skills/what-next/SKILL.md",
)

# A list gone short would leave the walk below silent rather than red, so it is counted first.
LIVE_DOCUMENT_COUNT = 2

# An HTML comment, so a reader of the rendered page never sees it and a writer editing the file does.
STEP_MARK = "<!-- steps -->"


def as_an_arrow(names):
    return " → ".join(names)


def the_step_list():
    return as_an_arrow(step.name for step in spec_loop.STEPS)


# Only the marked line is read, so the prose around it can be reworded freely.
def marked_line(text):
    lines = [line.strip() for line in text.splitlines()]
    marked = [at for at, line in enumerate(lines) if line == STEP_MARK]
    assert len(marked) == 1, "expected one marked line, found {}".format(len(marked))
    return lines[marked[0] + 1]


def given_a_document_marked_with(line):
    return "Prose a writer may reword.\n\n{}\n{}\n\nAnd more of it.\n".format(STEP_MARK, line)


def test_every_live_document_carries_the_step_list_as_its_marked_line():
    assert len(LIVE_DOCUMENTS) == LIVE_DOCUMENT_COUNT

    for path in LIVE_DOCUMENTS:
        held = (ROOT / path).read_text(encoding="utf-8")

        assert marked_line(held) == the_step_list(), path + " does not carry the step list"


def test_a_document_that_missed_a_step_added_to_the_driver_is_caught():
    missing = as_an_arrow(step.name for step in spec_loop.STEPS[:-1])

    assert marked_line(given_a_document_marked_with(missing)) == missing != the_step_list()


def test_a_document_that_holds_the_steps_out_of_order_is_caught():
    turned = as_an_arrow(step.name for step in reversed(spec_loop.STEPS))

    assert marked_line(given_a_document_marked_with(turned)) == turned != the_step_list()


def test_the_prose_around_the_marked_line_is_never_read():
    reworded = given_a_document_marked_with(the_step_list())

    assert marked_line(reworded) == the_step_list()


# --- the command the Plugin puts on PATH ------------------------------------

def test_a_loop_started_below_the_top_of_the_repository_logs_at_the_top(loop, monkeypatch):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    below = loop.repo.work / "src" / "deep"
    below.mkdir(parents=True)
    monkeypatch.chdir(below)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0, said(ran)
    assert "spec-loop/158/ticket-168" in loop.log()
    assert not (below / ".spec-loop").exists()


def test_the_spec_loop_command_starts_the_driver_in_the_plugin(repo):
    ran = launch("spec-loop", where=repo.work)

    assert ran.status == 64
    assert ran.err == "usage: spec-loop <spec-issue-number> [--dry-run] [--bypass]\n"


# The Plugin reaches repos with no Docker and no flaky tests, so what it tells them holds for any repo.
def test_what_next_leaves_the_reruns_to_the_suite_file_and_names_no_tool_of_this_repo():
    text = (ROOT / "plugins/skillworks/skills/what-next/SKILL.md").read_text(encoding="utf-8")

    assert "Docker" not in text
    assert "`uv`" not in text
    assert "container" not in text
    assert "Suite file sets how many times" in text
