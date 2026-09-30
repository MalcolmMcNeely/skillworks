#
# The spec loop's plan and its steps, read against a throwaway repository.

import ast
import io
import json
import re
import threading
import uuid
from pathlib import Path

import pytest

import land_ticket
import seed_steering
import spec_loop
import ticket_worktree
from conftest import (ROOT, SCRIPTS, Ran, RecordingRunner, Repo, check, git, launch, no_wait,
                      project_suite, write_loop, write_steering, write_suite)
from runner import Subprocess
from suite import Suite

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
    return driver_in(repo, runner, monkeypatch)


@pytest.fixture
def master(tmp_path, runner, monkeypatch):
    return driver_in(Repo(tmp_path, target="master"), runner, monkeypatch)


SPEC_BRANCH = "spec/target-branch"

COUNTED = ("## Problem Statement\n\nWords.\n\n"
           "## User Stories\n\n1. As a team member, I want a plan.\n2. As a team member, I want a run.\n\n"
           "## Implementation Decisions\n\n1. The driver plans.\n\n"
           "## Surfaces\n\n- **The user docs** (`docs/usage/`): the plan is described.\n")

NAMES_ITS_BRANCH = COUNTED + "\n## Branch\n\n`{}`\n".format(SPEC_BRANCH)

# The Seed's Surfaces hold the README, so the drift check judges it on every spec.
ALL_DONE = {"S1": "Done", "S2": "Done", "D1": "Done", "The user docs": "In step",
            "The README": "In step"}


def drift_report(*extra, unrequested=(), **given):
    judged = dict(ALL_DONE, **{name.replace("_", " "): said for name, said in given.items()})
    said = "## Drift report\n\n### Verdicts\n\n"
    said += "".join("- {}: {}\n".format(name, verdict) for name, verdict in judged.items()
                    if verdict is not None)
    said += "".join("- {}\n".format(line) for line in extra)
    said += "\nThe prose.\n"
    if unrequested:
        said += "\n### Unrequested\n\n" + "".join("- {}\n".format(line) for line in unrequested)
    return said


NAME_CHECK = "/skillworks:spec-names"

JUDGES = ("/skillworks:spec-drift", NAME_CHECK)


def name_report(*renames):
    return "## Name report\n\n### Renames\n\n" + "".join(
        "- {}\n".format(line) for line in renames or ("None",))


NO_RENAMES = name_report()


# The checkout sits on the spec's branch, so what a case commits there reaches it and not main.
@pytest.fixture
def spec_mode(tmp_path, runner, monkeypatch):
    repo = Repo(tmp_path)
    git(repo.work, "checkout", "--quiet", "-b", SPEC_BRANCH)
    git(repo.work, "push", "--quiet", "origin", SPEC_BRANCH)
    repo.target = SPEC_BRANCH
    driven = driver_in(repo, runner, monkeypatch)
    write_loop(repo.work, "spec")
    return driven


def driver_in(repo, runner, monkeypatch):
    # The loop puts its log where it is run, so it is run in the throwaway repository.
    monkeypatch.chdir(repo.work)
    # A session is looked for under this case's own folder, so no real one can answer a check here.
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", (repo.root / "claude").as_posix())
    # A suite run from inside a Session inherits both, so a case names the Parent it means or none.
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    monkeypatch.delenv("OTEL_RESOURCE_ATTRIBUTES", raising=False)
    # A loop started from a bypass run inherits its mode, so a case sets the one it means.
    monkeypatch.delenv("SPEC_LOOP_PERMISSION_MODE", raising=False)
    write_loop(repo.work, repo.target)
    write_steering(repo.work)
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
        self.body = NAMES_ITS_BRANCH
        self.ready = Ran(0, "", "")
        # A drift check that found everything done, so only a case about the count reads a stop.
        self.drift_report = drift_report()
        # A Name check that found no rename, so only a case about the names reads a stop.
        self.name_report = NO_RENAMES
        self.filed = []
        self.notes = []
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
        if asked.startswith("issue create"):
            return self.file(self.runner.calls[-1])
        if asked.endswith("--jq .id"):
            return Ran(0, "9" + asked.split(" ")[1].rsplit("/", 1)[-1] + "\n", "")
        if asked.startswith("api --method POST repos/owner/repo/issues/{}/sub_issues".format(SPEC)):
            return Ran(0, "", "")
        # Every issue the loop filed was linked as it was filed, so none is left without a spec.
        if asked.startswith("api --paginate repos/owner/repo/issues?labels=ready-for-agent"):
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
        if asked == "api repos/owner/repo/issues/{} --jq .body".format(SPEC):
            return Ran(0, self.body, "")
        if asked == "pr ready " + SPEC_BRANCH:
            return self.ready
        if asked == "issue view {} --json comments --jq .comments[-1].body".format(SPEC):
            return Ran(0, self.newest_comment(), "")
        # The body file is gone once gh returns, so it is read while the call is made.
        if asked.startswith("issue comment {} --body-file ".format(SPEC)):
            self.notes.append(Path(self.runner.calls[-1][-1]).read_text(encoding="utf-8"))
            return Ran(0, "https://github.com/owner/repo/issues/{}#issuecomment-1\n".format(SPEC), "")
        return Ran(1, "", "the tracker has no answer for: " + asked + "\n")

    # Each judge posts its report as it runs, so the newest comment is the last judge's.
    def newest_comment(self):
        judges = [call[2] for call in self.runner.calls
                  if call[0] == "claude" and call[2].startswith(JUDGES)]
        if judges and judges[-1].startswith(NAME_CHECK):
            return self.name_report
        return self.drift_report

    # Numbered after the last ticket, and open, so the loop's next read of the spec finds it.
    def file(self, called):
        number = str(max(int(row[0]) for row in self.tickets) + 1)
        self.filed.append((called[called.index("--title") + 1], called[called.index("--body") + 1]))
        self.tickets = self.tickets + ((number, "open", self.filed[-1][0]),)
        return Ran(0, "https://github.com/owner/repo/issues/{}\n".format(number), "")


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
        command = asked.split()[0]
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
        if "--stop-after-tests" in asked and self.builds:
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
def given_a_suite_on_the_target(loop, *checks, runs=None):
    write_suite(loop.repo.work, *checks, runs=runs)
    git(loop.repo.work, "add", "-A")
    git(loop.repo.work, "commit", "--quiet", "-m", "A Suite")
    git(loop.repo.work, "push", "--quiet", "origin", loop.repo.target)


def given_a_suite_that_passes(loop, runs=None):
    given_a_suite_on_the_target(loop, project_suite()[0], runs=runs)
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

def test_the_dry_run_names_the_spec_and_its_tickets_by_issue_number(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET + ONE_CLOSED_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0, said(ran)
    assert "DRY   spec #158: " in ran.out
    assert "#168 [open]" in ran.out
    assert "DRY   the next ticket is #168" in ran.out


def test_a_rule_with_no_import_stops_the_dry_run_naming_the_rule_and_the_line_to_add(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    claude = loop.repo.work / "CLAUDE.md"
    imports = claude.read_text(encoding="utf-8").replace("@docs/agents/rules/words.md\n", "")
    claude.write_text(imports, encoding="utf-8", newline="\n")

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 1
    assert ("ABORT docs/agents/rules/words.md has no import in CLAUDE.md, so it does not load into a session. "
            "Add this line to CLAUDE.md: @docs/agents/rules/words.md") in said(ran)


def test_a_missing_steering_file_stops_the_dry_run_naming_the_file_and_setup(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    (loop.repo.work / "docs" / "agents" / "review-standards.md").unlink()

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 1
    assert ("ABORT docs/agents/review-standards.md is missing, and setup seeds it. "
            "Run /skillworks:skillworks-setup to write it again.") in said(ran)
    assert "DRY" not in ran.out


def test_a_repo_holding_every_seeded_file_passes_the_steering_check(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0, said(ran)
    assert "is missing, and setup seeds it" not in said(ran)


def test_a_seed_added_to_setup_s_list_is_checked_with_no_other_change(loop, monkeypatch):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    monkeypatch.setitem(seed_steering.PLACES, "new-seed.md", "docs/agents/new-seed.md")

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 1
    assert "ABORT docs/agents/new-seed.md is missing, and setup seeds it." in said(ran)


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
        "checks: origin-has-target something-to-land",
        "git rebase origin/<target>, when the base has moved",
        "checks: commits-kept files-kept",
        "the build session, when the rebase conflicts",
        "checks: session-named no-refusal none-left-conflicting no-marker-staged "
        "rebase-carried-on",
        "the whole suite, when the base has moved",
        "checks: suite-can-run suite-green",
        "git push origin HEAD:<target>, again after each lost race",
        "checks: pushed\n",
        "gh issue comment naming the commits that reached <target>, when the rebase replaced them",
        "checks: commented\n",
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
        "checks: no-error command-loaded new-commit ticket-trailer tree-clean ticket-closed",
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
    assert planned_nudges(ran, "finish") == "up to 2, on new-commit ticket-trailer tree-clean ticket-closed"
    for step in ("fix", "sweep", "suite"):
        assert planned_nudges(ran, step) == ""


def test_the_dry_run_names_the_gap_round_between_the_drift_check_and_the_full_run(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0, said(ran)
    assert planned_steps(ran)[-7:-3] == ["drift", "gap-ticket", "re-check", "names"]
    assert planned_steps(ran)[-1] == "full-run"
    assert '"/skillworks:spec-drift 158 <base>"' in planned_call(ran, "drift")
    assert "one ticket under the spec when the count finds a Gap" in planned_call(ran, "gap-ticket")
    assert '"/skillworks:spec-drift 158 <base> <the Gap items>"' in planned_call(ran, "re-check")
    assert planned_checks(ran, "re-check") == "no Gap left, no Contradicts"
    assert "once and last" in planned_call(ran, "full-run")


def test_the_dry_run_names_the_name_check_after_the_gap_round(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0, said(ran)
    assert '"/skillworks:spec-names 158 <base>"' in planned_call(ran, "names")
    assert planned_checks(ran, "names") == "a Name report recorded, a Renames list"


def test_the_dry_run_names_the_rename_steps_between_the_name_check_and_the_full_run(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0, said(ran)
    assert planned_steps(ran)[-4:] == ["names", "rename-ticket", "name-re-check", "full-run"]
    assert ("one ticket under the spec when the Name check finds a rename"
            in planned_call(ran, "rename-ticket"))
    assert ('"/skillworks:spec-names 158 <base> <the rename ticket>"'
            in planned_call(ran, "name-re-check"))
    assert planned_checks(ran, "name-re-check") == "a new Name report, a Verdicts list, every rename Done"


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


# --- the spec's shape ---------------------------------------------------------

SKIPS_A_STORY = COUNTED.replace("2. As a team member, I want a run.", "3. As a team member, I want a run.")


def test_the_dry_run_says_what_the_spec_holds_to_be_counted(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0, said(ran)
    assert ("SHAPE spec #158 holds 2 stories, 1 decision and 1 Surface, so the drift check's "
            "Verdicts can be counted") in ran.out
    assert "SHAPE" in loop.log()


def test_the_dry_run_turns_down_a_spec_in_another_shape_and_names_the_fault(loop):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    tracker.body = SKIPS_A_STORY

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 1
    assert "ABORT spec #158 is not in the shape the loop counts" in said(ran)
    assert "## User Stories skips 2: it goes from 1 to 3" in said(ran)
    assert "spec-loop/158/ticket-168" not in said(ran)


def test_a_spec_in_another_shape_stops_the_run_before_any_ticket_is_claimed(loop, runner):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    tracker.body = COUNTED.replace("- **The user docs**", "- The user docs")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert ("a Surface item under ## Surfaces opens with no bold name: - The user docs "
            "(`docs/usage/`): the plan is described.") in loop.log()
    assert not runner.built("issue edit")
    assert not runner.started("claude")
    assert "START" not in loop.log()


def test_every_shape_fault_reaches_the_stop_line(loop):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    tracker.body = SKIPS_A_STORY.replace("## Implementation Decisions", "## Decisions")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "## User Stories skips 2: it goes from 1 to 3" in loop.log()
    assert "the spec has no ## Implementation Decisions heading" in loop.log()


# --- the Cut ------------------------------------------------------------------

CUT_TICKETS = "/skillworks:to-tickets"


def given_a_cut_that_files(sessions, tracker, tickets):
    def cut():
        tracker.tickets = tickets
    sessions.then[CUT_TICKETS] = cut


def test_a_spec_with_no_tickets_has_them_cut_before_the_first_ticket(loop, runner):
    tracker = given_the_tracker_holds(loop, ())
    sessions = given_sessions_that_report(loop)
    given_a_cut_that_files(sessions, tracker, ONE_OPEN_TICKET)

    loop.run(SPEC)

    assert [call[2].split()[0:2] for call in step_calls(runner)[:2]] == [
        [CUT_TICKETS, SPEC], ["/skillworks:implement", "168"]]


def test_a_spec_with_tickets_has_none_cut(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    loop.run(SPEC)

    assert call_asking(runner, CUT_TICKETS) is None


def test_a_spec_still_without_tickets_after_the_cut_stops_the_loop(loop, runner):
    given_the_tracker_holds(loop, ())
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "STOP  spec #158 still has no tickets" in loop.log()
    assert call_asking(runner, "/skillworks:implement") is None


def test_a_cut_that_filed_no_tickets_after_denials_gives_the_way_past_them(loop):
    given_the_tracker_holds(loop, ())
    given_a_session_that_was_denied(given_sessions_that_report(loop), "to-tickets", A_DENIED_WRITE)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert 'Denial: Write {"file_path": ".claude/rules/words.md"' in loop.log()
    assert BYPASS in loop.log()


def test_the_slices_the_cut_shows_are_in_the_loop_log(loop):
    tracker = given_the_tracker_holds(loop, ())
    sessions = given_sessions_that_report(loop)
    given_a_cut_that_files(sessions, tracker, ONE_OPEN_TICKET)
    sessions.says["to-tickets"] = "1. **Title**: The dry run prints the plan\n   **Blocked by**: none"

    loop.run(SPEC)

    assert "1. **Title**: The dry run prints the plan\n   **Blocked by**: none" in loop.log()


def test_the_cut_s_log_files_are_named_for_the_cut(loop):
    tracker = given_the_tracker_holds(loop, ())
    sessions = given_sessions_that_report(loop)
    given_a_cut_that_files(sessions, tracker, ONE_OPEN_TICKET)

    loop.run(SPEC)

    assert sorted(path.name for path in loop.records().glob("cut.*")) == ["cut.err", "cut.json"]


def test_a_dry_run_on_a_spec_with_no_tickets_says_a_session_would_cut_them_first(loop):
    given_the_tracker_holds(loop, ())

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0, said(ran)
    assert "DRY   spec #158 has no tickets, so a Session would cut them first" in ran.out
    assert '"/skillworks:to-tickets 158' in planned_call(ran, "cut")


def test_a_dry_run_on_a_spec_with_no_tickets_prints_each_ticket_s_steps_with_a_place_for_its_number(loop):
    given_the_tracker_holds(loop, ())

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0, said(ran)
    assert planned_steps(ran)[:9] == [
        "cut", "build", "standards", "spec", "architecture", "fix", "sweep", "suite", "finish"]
    assert "/skillworks:implement <ticket> --stop-after-tests" in planned_call(ran, "build")
    assert "spec-loop/158/ticket-<ticket>" in said(ran)
    assert planned_steps(ran)[-1] == "full-run"


def test_a_dry_run_on_a_spec_with_no_tickets_starts_no_session_and_reaches_no_remote(loop, runner):
    given_the_tracker_holds(loop, ())
    base = git(loop.repo.origin, "rev-parse", "main").strip()

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0, said(ran)
    assert not runner.started("claude")
    assert git(loop.repo.origin, "rev-parse", "main").strip() == base
    assert not (loop.repo.work / ".claude" / "worktrees").exists()


def test_a_dry_run_on_a_spec_with_no_tickets_in_another_shape_is_refused_before_any_step(loop):
    tracker = given_the_tracker_holds(loop, ())
    tracker.body = SKIPS_A_STORY

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 1
    assert "ABORT spec #158 is not in the shape the loop counts" in said(ran)
    assert "ticket-<ticket>" not in said(ran)


def test_the_stop_for_a_spec_in_another_shape_says_the_grill_writes_the_counted_shape(loop):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    tracker.body = SKIPS_A_STORY

    ran = loop.run(SPEC, "--dry-run")

    assert "/skillworks:grill writes a spec in the shape the loop counts" in said(ran)


MESSAGE_CALLS = {"stop", "refusal", "say", "write"}


def said_by(call):
    name = call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")
    return name in MESSAGE_CALLS


def messages():
    found = []
    for script in [SCRIPTS / "spec_loop.py", SCRIPTS / "land_ticket.py",
                   *sorted((SCRIPTS / "tracker").glob("*.py"))]:
        for call in ast.walk(ast.parse(script.read_text(encoding="utf-8"))):
            if isinstance(call, ast.Call) and said_by(call):
                found += [(script.name, text.value) for argument in call.args
                          for text in ast.walk(argument)
                          if isinstance(text, ast.Constant) and isinstance(text.value, str)]
    return found


def test_no_driver_or_tracker_message_names_a_step_the_dev_loop_runs_for_you():
    assert [(script, text) for script, text in messages()
            if "to-tickets" in text or "to-spec" in text] == []


def test_the_walk_for_messages_finds_the_stop_for_a_spec_in_another_shape():
    assert any("is not in the shape the loop counts" in text for _, text in messages())


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
    given_the_closed_ticket_landed_after_the_base(loop)
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
    given_the_closed_ticket_landed_after_the_base(loop)
    given_a_leftover_worktree(loop, "ticket-164")

    ran = loop.run(SPEC)

    assert ran.status == 0
    assert "END   spec #158" in said(ran)
    assert "nothing uncommitted" in said(ran)
    assert not leftover(loop).exists()
    assert loop.repo.has_branch(SPEC, "ticket-164-kept-1")


def test_the_log_names_the_job_and_the_branch_a_leftover_was_kept_on(loop):
    given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    given_the_closed_ticket_landed_after_the_base(loop)
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
    given_the_closed_ticket_landed_after_the_base(loop)
    stray = loop.repo.group(SPEC) / "stray"
    stray.mkdir(parents=True)
    (stray / "notes.txt").write_text("notes\n", encoding="utf-8", newline="\n")

    ran = loop.run(SPEC)

    assert ran.status == 0
    assert "{} is no worktree of its own, so it was left where it is".format(
        stray.as_posix()) in loop.log()


def test_a_keep_that_left_nothing_alone_says_nothing(loop):
    given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    given_the_closed_ticket_landed_after_the_base(loop)
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


def committed(runner, ticket="168"):
    def commit():
        git(runner.where, "add", "-A")
        git(runner.where, "commit", "--quiet", "-m", "Built\n\nTicket: #" + ticket)
    return commit


def closed(tracker, ticket="168"):
    return lambda: tracker.closed.add(ticket)


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


# A trailer above a blank line is body text to git, so Land could never trace the commit back.
def committed_with_a_stranded_trailer(runner):
    def commit():
        git(runner.where, "add", "-A")
        git(runner.where, "commit", "--quiet", "-m",
            "Built\n\nTicket: #168\n\nCo-Authored-By: A <a@example.com>")
    return commit


def trailer_mended(runner):
    return lambda: git(runner.where, "commit", "--amend", "--quiet", "-m",
                       "Built\n\nTicket: #168\nCo-Authored-By: A <a@example.com>")


def test_a_finish_whose_commit_git_reads_no_ticket_trailer_in_is_nudged(loop, runner):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(committed_with_a_stranded_trailer(runner), closed(tracker))
    sessions.when_nudged[FINISH] = trailer_mended(runner)

    ran = loop.run(SPEC)

    assert "step finish failed" not in said(ran)
    assert failed_in(loop, "finish") == ["ticket-trailer"]


def test_a_ticket_trailer_nudge_says_git_reads_only_the_last_paragraph(loop, runner):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(committed_with_a_stranded_trailer(runner), closed(tracker))

    loop.run(SPEC)

    assert "last paragraph" in nudge_calls(runner)[0][2].split("\n")[0]


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


# --- a Flake is named and its red output kept --------------------------------

FLAKE_STAMP = r"[0-9]{8}T[0-9]{12}Z(-[0-9]+)?"


def flake_files(loop, step):
    return sorted(loop.records().glob("flake-ticket-168-{}-*.out".format(step)))


def flake_lines(loop):
    return [line for line in loop.log().split("\n") if line[9:15] == "FLAKE "]


def given_two_checks_that_each_flake(loop):
    given_a_suite_on_the_target(loop, check("dotnet", "test", "Skillworks.slnx"),
                                check("npm", "test"), runs=2)
    loop.runner.stub("dotnet", says="the solution passed")
    loop.runner.stub("npm", says="the front end passed")
    loop.runner.refuse(SOLUTION, "a Span test failed", times=1)
    loop.runner.refuse("npm test", "a front end test failed", times=1)
    return Sessions(loop.repo, loop.runner)


def test_a_check_that_flakes_in_the_suite_step_gets_a_flake_line_naming_it(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    [line] = flake_lines(loop)
    assert "FLAKE #168 suite        dotnet test Skillworks.slnx went red and then passed" in line


def test_the_red_output_of_a_flake_is_kept_in_a_file_named_for_the_step_and_a_stamp(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    [kept] = flake_files(loop, "suite")
    assert re.fullmatch("flake-ticket-168-suite-" + FLAKE_STAMP + r"\.out", kept.name)
    assert "a Span test failed" in kept.read_text(encoding="utf-8")
    assert kept.as_posix() in flake_lines(loop)[0]


def test_a_second_flake_does_not_write_over_the_first(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_two_checks_that_each_flake(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    kept = flake_files(loop, "suite")
    assert len(kept) == 2
    held = [each.read_text(encoding="utf-8") for each in kept]
    assert any("a Span test failed" in each for each in held)
    assert any("a front end test failed" in each for each in held)
    assert len(flake_lines(loop)) == 2


def test_a_flaked_suite_step_goes_on_to_finish_and_starts_no_fix_session(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert implement_flags(runner) == ["--stop-after-tests", "--fix", "--finish"]
    assert "goes round once" not in loop.log()


def test_the_finishing_step_is_handed_each_flake_and_its_kept_file(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_two_checks_that_each_flake(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    prompt = finish_prompt(runner)
    assert "Closing note" in prompt
    kept = flake_files(loop, "suite")
    assert len(kept) == 2
    for each in kept:
        assert each.as_posix() in prompt
    assert "dotnet test Skillworks.slnx" in prompt
    assert "npm test" in prompt


def test_a_suite_step_with_no_flake_hands_the_finishing_step_no_flake(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "Flake" not in finish_prompt(runner)
    assert flake_lines(loop) == []


# The base moves while the ticket finishes, so the landing rebases and runs the Suite again.
def given_a_run_that_lands_on_a_moved_base_and_flakes(loop):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop, runs=2)
    sessions.then[FINISH] = all_of(
        committed(loop.runner), closed(tracker), lambda: loop.repo.advance_origin("later"),
        lambda: loop.runner.refuse(SOLUTION, "a landing test failed", times=1))


def test_a_flake_in_the_landing_gets_a_flake_line_and_a_kept_file(loop):
    given_a_run_that_lands_on_a_moved_base_and_flakes(loop)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    [line] = flake_lines(loop)
    assert "FLAKE #168 land         dotnet test Skillworks.slnx went red and then passed" in line
    [kept] = flake_files(loop, "land")
    assert re.fullmatch("flake-ticket-168-land-" + FLAKE_STAMP + r"\.out", kept.name)
    assert "a landing test failed" in kept.read_text(encoding="utf-8")
    assert kept.as_posix() in line


def test_a_ticket_that_passes_with_a_flake_lands_and_its_worktree_is_removed(loop, runner):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop, runs=2)
    sessions.then[FINISH] = all_of(committed(runner), closed(tracker))
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    assert len(flake_files(loop, "suite")) == 1
    assert "DONE  #168" in loop.log()
    assert not ticket_worktree_of(loop).exists()


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


# npm passed on main and ignores the one file the build writes, so a Proof holds it in the worktree.
def test_the_finishing_step_is_handed_the_line_of_each_check_a_proof_held(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_suite_on_the_target(loop, check("dotnet", "test", "Skillworks.slnx"),
                                check("npm", "test", ignores=["built.txt"]))
    earlier = RecordingRunner()
    earlier.stub("dotnet")
    earlier.stub("npm")
    assert Suite(earlier, loop.repo.work).run().passed
    runner.stub("dotnet", says="the solution passed\n")
    runner.stub("npm")
    Sessions(loop.repo, runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "the solution passed" in finish_prompt(runner)
    assert re.search(r"npm test did not run, because Proof [0-9a-f]{12}, made .+, holds its inputs",
                     finish_prompt(runner))
    assert not runner.started("npm")


# The build starts the real command, so the Proof is the one an agent's own run leaves behind.
def test_a_proof_kept_by_skillworks_suite_in_the_build_skips_that_check_in_the_suite_step(
        loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_suite_on_the_target(loop, check("git", "--version"))
    sessions = Sessions(loop.repo, runner)
    agent_ran = []
    sessions.then["--stop-after-tests"] = lambda: agent_ran.append(
        launch("skillworks-suite", where=runner.where))

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert agent_ran[0].status == 0, said(agent_ran[0])
    assert ["git", "--version"] not in runner.calls
    assert re.search(r"git --version did not run, because Proof [0-9a-f]{12}, made .+, holds its "
                     r"inputs", suite_output(loop))


def test_every_step_session_is_told_to_check_its_work_with_skillworks_suite(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert len(step_calls(runner)) == 7
    for call in step_calls(runner):
        assert "run `skillworks-suite`" in call[2], call[2]
        assert "In this loop the driver runs the whole Suite" in call[2], call[2]


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


# A flake spends a run, and the run that proved the work is the one the Closing note names.
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


def given_a_session_that_was_denied(sessions, step, *denials):
    sessions.denials[step] = list(denials)


# The finishing Session never commits here, so every case stops at the finishing step.
def given_a_finish_that_was_denied(sessions, *denials):
    given_a_session_that_was_denied(sessions, "implement", *denials)


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
    asked = [call[2].split()[0] for call in step_calls(runner)]
    assert asked == ["/skillworks:" + name for name in (
        "implement", "review-standards", "review-spec", "review-architecture",
        "implement", "comment-sweep", "implement")]
    for changes in changes_given_to_sessions(runner):
        assert changes.get("OTEL_RESOURCE_ATTRIBUTES") == PARENT


def test_the_drift_session_names_the_session_that_started_the_driver(loop, runner, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "parent-session")
    given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    given_sessions_that_report(loop)
    given_the_closed_ticket_landed_after_the_base(loop)

    loop.run(SPEC)

    assert call_asking(runner, "/skillworks:spec-drift") is not None
    assert changes_given_to_sessions(runner)[-1].get("OTEL_RESOURCE_ATTRIBUTES") == PARENT


# --- the Ticket trailer each Session is handed -------------------------------

# The Plugin's hook reads this name, so it is written out here and not imported from the driver.
TICKET_VARIABLE = "SKILLWORKS_TICKET"


def trailers_handed(runner, mark):
    return [(call.env or {}).get(TICKET_VARIABLE, "unset") for call in runner.made
            if call.args[0] == "claude" and call.args[2].startswith(mark)]


def trailers_handed_for(runner, ticket):
    return [(call.env or {}).get(TICKET_VARIABLE) for call in runner.made
            if call.args[0] == "claude" and call.args[2].split()[1:2] == [ticket]]


# The one a developer's shell set is taken away and not left, so a Session names no ticket by accident.
def handed_no_trailer(runner, mark):
    handed = trailers_handed(runner, mark)
    return bool(handed) and all(trailer is None for trailer in handed)


def test_every_step_session_is_handed_its_ticket_trailer(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    loop.run(SPEC)

    handed = trailers_handed(runner, "/")
    assert len(handed) == 7
    assert set(handed) == {"#168"}


def test_every_nudge_is_handed_the_trailer_of_the_ticket_it_works_on(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_stops_short(given_sessions_that_report(loop), "spec")

    loop.run(SPEC)

    nudged = [(call.env or {}).get(TICKET_VARIABLE) for call in runner.made
              if call.args[0] == "claude" and not call.args[2].startswith("/")]
    assert nudged
    assert set(nudged) == {"#168"}


def test_the_cut_is_handed_no_ticket_trailer(loop, runner, monkeypatch):
    monkeypatch.setenv(TICKET_VARIABLE, "#1")
    tracker = given_the_tracker_holds(loop, ())
    given_a_cut_that_files(given_sessions_that_report(loop), tracker, ONE_OPEN_TICKET)

    loop.run(SPEC)

    assert handed_no_trailer(runner, CUT_TICKETS)


def test_the_drift_check_is_handed_no_ticket_trailer(loop, runner, monkeypatch):
    monkeypatch.setenv(TICKET_VARIABLE, "#1")
    ran = drifted_in_a_round(loop, drift_report(S2="Missing"), verdicts_alone(S2="Done"))

    assert ran.status == 0, said(ran)
    assert handed_no_trailer(runner, "/skillworks:spec-drift")


def test_the_gap_ticket_s_sessions_are_handed_its_trailer(loop, runner):
    ran = drifted_in_a_round(loop, drift_report(S2="Missing"), verdicts_alone(S2="Done"))

    assert ran.status == 0, said(ran)
    assert set(trailers_handed_for(runner, GAP_TICKET)) == {"#" + GAP_TICKET}


# --- the spec's commits --------------------------------------------------------

# A run resumed after its one ticket Landed, so the checks find a commit of the spec to read.
def given_the_closed_ticket_landed_after_the_base(loop):
    held = loop.records() / "base.sha"
    held.parent.mkdir(parents=True, exist_ok=True)
    held.write_text(git(loop.repo.work, "rev-parse", "origin/" + loop.repo.target),
                    encoding="utf-8", newline="\n")
    loop.repo.push_from_elsewhere("landed.txt", "landed",
                                  "Already done\n\nTicket: #" + ONE_CLOSED_TICKET[0][0])


def given_a_hand_commit_while_168_is_reviewed(loop, sessions):
    sessions.then["review-standards 168"] = lambda: loop.repo.push_from_elsewhere(
        "hand.txt", "hand", "A hand fix with no trailer")


def test_the_log_says_how_many_commits_the_drift_check_reads_and_leaves_out(loop):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    given_a_filed_ticket_that_lands(loop, tracker, sessions, "168")
    given_a_hand_commit_while_168_is_reviewed(loop, sessions)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    log = loop.log()
    line = ("SCOPE the drift check reads 1 commit of spec #{}, and leaves out 1 other commit after "
            "the base commit\n").format(SPEC)
    assert line in log
    assert log.index(line) < log.index("DRIFT all tickets closed")


def test_the_re_check_and_the_name_check_each_say_they_read_the_gap_ticket_s_commit_too(loop):
    ran = drifted_in_a_round(loop, drift_report(S2="Missing"), verdicts_alone(S2="Done"))

    assert ran.status == 0, said(ran)
    log = loop.log()
    scope = ("SCOPE the {} reads {} of spec #" + SPEC + ", and leaves out 0 other commits after the "
             "base commit\n")
    assert log.index(scope.format("drift re-check", "2 commits")) < log.index(
        "DRIFT the Gap ticket is closed")
    assert log.index(scope.format("Name check", "2 commits")) < log.index("NAMES checking")


def test_a_spec_with_no_commit_after_the_base_stops_before_any_check_and_stays_open(loop, runner):
    given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert ("STOP  spec #{} has no commit after the base commit {} whose Ticket: trailer names one "
            "of its tickets").format(SPEC, base_of(loop)) in loop.log()
    assert [call for call in session_calls(runner) if call[2].startswith(JUDGES)] == []
    assert "END" not in loop.log()


def test_the_drift_report_the_session_posted_on_the_spec_is_read_back(loop, runner):
    tracker = given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    given_sessions_that_report(loop)
    given_the_closed_ticket_landed_after_the_base(loop)
    tracker.drift_report = drift_report()

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    assert (loop.records() / "drift.md").read_text(encoding="utf-8") == (
        drift_report().removeprefix("## Drift report\n\n"))
    assert "DRIFT the report is recorded on spec #{}".format(SPEC) in ran.out


# --- the count ---------------------------------------------------------------

def drifted(loop, report, *denials):
    tracker = given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    given_a_session_that_was_denied(given_sessions_that_report(loop), "spec-drift", *denials)
    given_the_closed_ticket_landed_after_the_base(loop)
    tracker.drift_report = report
    return loop.run(SPEC)


def test_every_verdict_done_or_in_step_ends_the_run_and_says_what_was_counted(loop):
    ran = drifted(loop, drift_report())

    assert ran.status == 0, said(ran)
    assert "COUNT the spec holds 5 items, and the drift report gives 5 Verdicts" in loop.log()
    assert "STOP" not in loop.log()
    assert "END   spec #{}".format(SPEC) in loop.log()


def test_a_verdict_for_an_item_the_spec_does_not_hold_is_warned_of_and_stops_nothing(loop):
    ran = drifted(loop, drift_report("S9: Missing. Nothing."))

    assert ran.status == 0, said(ran)
    assert ("WARN  the drift report judges S9, which spec #{} does not hold, so its Verdict is "
            "not counted").format(SPEC) in loop.log()
    assert "END   spec #{}".format(SPEC) in loop.log()


def test_a_report_with_no_verdicts_list_stops_the_loop(loop):
    ran = drifted(loop, "## Drift report\n\nNothing drifted.\n")

    assert ran.status == 1
    assert ("STOP  the drift report on spec #{} holds no ### Verdicts list, so nothing was "
            "counted").format(SPEC) in loop.log()
    assert "COUNT" not in loop.log()
    assert "END" not in loop.log()


def test_a_spec_whose_last_comment_is_no_drift_report_stops_the_loop(loop):
    ran = drifted(loop, "Looks good to me.\n")

    assert ran.status == 1
    assert ("STOP  the drift check recorded no report on spec #{}, so nothing was counted"
            .format(SPEC)) in loop.log()
    assert not (loop.records() / "drift.md").exists()
    assert "END" not in loop.log()


def test_a_drift_check_that_recorded_no_report_after_denials_gives_the_way_past_them(loop):
    ran = drifted(loop, "Looks good to me.\n", A_DENIED_WRITE)

    assert ran.status == 1
    assert 'Denial: Write {"file_path": ".claude/rules/words.md"' in loop.log()
    assert BYPASS in loop.log()


def test_a_drift_check_that_recorded_no_report_with_no_denials_gives_no_way_past_them(loop):
    ran = drifted(loop, "Looks good to me.\n")

    assert ran.status == 1
    assert BYPASS not in said(ran) + loop.log()


def test_a_contradicts_stops_the_loop_naming_it_and_every_gap_beside_it(loop):
    ran = drifted(loop, drift_report(D1="Contradicts. It closes the spec.", S2="Missing",
                                     S1=None))

    assert ran.status == 1
    log = loop.log()
    assert "STOP  the drift report finds the code contradicts spec #{}".format(SPEC) in log
    assert "      Contradicts: D1: It closes the spec.\n" in log
    assert "      Gap: S1 has no Verdict\n" in log
    assert "      Gap: S2 is Missing\n" in log


def test_a_contradicts_stops_the_loop_before_any_gap_is_built(loop, runner):
    ran = drifted(loop, drift_report(D1="Contradicts. It closes the spec.", S2="Missing"))

    assert ran.status == 1
    assert not runner.built("issue create")
    assert len(prompts_asking(runner, "/skillworks:spec-drift")) == 1
    assert "GAP" not in loop.log()


def test_each_unrequested_item_gets_a_note_and_stops_nothing(loop):
    ran = drifted(loop, drift_report(unrequested=("A helper that trims logs.", "A retry.")))

    assert ran.status == 0, said(ran)
    assert "NOTE  Unrequested: A helper that trims logs.\n" in loop.log()
    assert "NOTE  Unrequested: A retry.\n" in loop.log()


def test_unrequested_items_are_noted_even_when_a_gap_stops_the_loop(loop):
    ran = drifted_in_a_round(loop, drift_report(S1="Missing", unrequested=("A retry.",)),
                             verdicts_alone(S1="Missing"))

    assert ran.status == 1
    assert "NOTE  Unrequested: A retry.\n" in loop.log()
    assert loop.log().index("NOTE") < loop.log().index("STOP")


# --- the Gap round -------------------------------------------------------------

# Numbered after the one closed ticket, the way the Tracker numbers what it is handed next.
GAP_TICKET = "162"


def verdicts_alone(**given):
    return "## Drift report\n\n### Verdicts\n\n" + "".join(
        "- {}: {}\n".format(name.replace("_", " "), said) for name, said in given.items())


# Each drift check records the next report, so the re-check reads its own and not the first.
def given_drift_reports(sessions, tracker, *reports):
    waiting = list(reports)

    def record():
        tracker.drift_report = waiting.pop(0)
    sessions.then["spec-drift"] = record


# A file of its own, since a ticket landed before it already holds what every build writes.
def given_a_filed_ticket_that_lands(loop, tracker, sessions, ticket):
    def build():
        (Path(loop.runner.where) / "filed.txt").write_text("built\n", encoding="utf-8", newline="\n")
    sessions.then["implement {} --stop-after-tests".format(ticket)] = build
    sessions.then["implement {} --finish".format(ticket)] = all_of(
        committed(loop.runner, ticket), closed(tracker, ticket))


def drifted_in_a_round(loop, first, second, *denials):
    tracker = given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    sessions = given_sessions_that_report(loop)
    given_a_session_that_was_denied(sessions, "spec-drift", *denials)
    given_the_closed_ticket_landed_after_the_base(loop)
    given_a_filed_ticket_that_lands(loop, tracker, sessions, GAP_TICKET)
    given_drift_reports(sessions, tracker, first, second)
    return loop.run(SPEC)


def base_of(loop):
    return (loop.records() / "base.sha").read_text(encoding="utf-8").strip()


def test_a_missing_a_partial_and_an_item_not_judged_are_filed_as_one_gap_ticket(loop, runner):
    ran = drifted_in_a_round(
        loop, drift_report(S2="Missing. No code stops.", D1="Partial. Half of it.",
                           The_user_docs=None),
        verdicts_alone(S2="Done", D1="Done", The_user_docs="In step"))

    assert ran.status == 0, said(ran)
    log = loop.log()
    assert "COUNT the spec holds 5 items, and the drift report gives 4 Verdicts" in log
    assert "GAP   S2 is Missing: No code stops.\n" in log
    assert "GAP   D1 is Partial: Half of it.\n" in log
    assert "GAP   The user docs has no Verdict\n" in log
    assert ("FILED #{} under spec #{} builds 3 Gaps, so the loop goes round once".format(
        GAP_TICKET, SPEC)) in log
    assert len(runner.built("issue create")) == 1
    assert "ready-for-agent" in runner.built("issue create")[0]


def test_the_gap_ticket_quotes_each_items_spec_text_its_verdict_and_the_reason(loop):
    drifted_in_a_round(
        loop, drift_report(S2="Missing. No code stops.", The_user_docs=None),
        verdicts_alone(S2="Done", The_user_docs="In step"))

    created = loop.runner.built("issue create")[0]
    title = created[created.index("--title") + 1]
    body = created[created.index("--body") + 1]
    assert title == "TICKET: Build the Gaps the drift check found"
    assert "### S2\n\n> As a team member, I want a run.\n\nVerdict: Missing. No code stops.\n" in body
    assert ("### The user docs\n\n> **The user docs** (`docs/usage/`): the plan is described.\n\n"
            "The drift check did not judge this exactly once. Check it, and build it if it is not "
            "there.\n") in body
    assert "- [ ] S2: As a team member, I want a run.\n" in body


def test_a_readme_the_spec_broke_is_filed_as_a_gap_ticket_that_names_the_readme(loop):
    ran = drifted_in_a_round(
        loop, drift_report(The_README="Out of step. It still runs `old-name`."),
        verdicts_alone(The_README="In step"))

    assert ran.status == 0, said(ran)
    assert "GAP   The README is Out of step: It still runs `old-name`.\n" in loop.log()
    created = loop.runner.built("issue create")[0]
    assert ("### The README\n\n> **The README** (`README.md`): "
            in created[created.index("--body") + 1])


def test_a_team_with_no_readme_surface_has_a_readme_verdict_warned_of_and_not_counted(loop):
    surfaces = loop.repo.work / "docs" / "agents" / "surfaces.md"
    surfaces.write_text(surfaces.read_text(encoding="utf-8").replace("## The README", "## The Readme"),
                        encoding="utf-8", newline="\n")

    ran = drifted(loop, drift_report(The_README="Out of step. It is stale."))

    assert ran.status == 0, said(ran)
    assert ("WARN  the drift report judges The README, which spec #{} does not hold, so its "
            "Verdict is not counted").format(SPEC) in loop.log()


def test_an_item_judged_twice_reaches_the_gap_ticket_as_a_check_before_a_build(loop):
    ran = drifted_in_a_round(loop, drift_report("S1: Missing. It is not there."),
                             verdicts_alone(S1="Done"))

    assert ran.status == 0, said(ran)
    assert "GAP   S1 has 2 Verdicts: Done, Missing\n" in loop.log()
    created = loop.runner.built("issue create")[0]
    assert ("### S1\n\n> As a team member, I want a plan.\n\nThe drift check did not judge this "
            "exactly once.") in created[created.index("--body") + 1]


def test_the_gap_ticket_is_built_through_every_step_and_lands(loop, runner):
    ran = drifted_in_a_round(loop, drift_report(S2="Missing"), verdicts_alone(S2="Done"))

    assert ran.status == 0, said(ran)
    asked = [call[2].split()[0] for call in step_calls(runner)
             if call[2].split()[1:2] == [GAP_TICKET]]
    assert asked == ["/skillworks:" + name for name in (
        "implement", "review-standards", "review-spec", "review-architecture", "implement",
        "implement")]
    assert "DONE  #{}".format(GAP_TICKET) in loop.log()


def test_the_re_check_judges_the_gap_items_alone_and_a_closed_round_ends_the_run(loop, runner):
    ran = drifted_in_a_round(
        loop, drift_report(S2="Missing. No code stops.", The_user_docs="Out of step. Short."),
        verdicts_alone(S2="Done", The_user_docs="In step"))

    assert ran.status == 0, said(ran)
    assert prompts_asking(runner, "/skillworks:spec-drift") == [
        "/skillworks:spec-drift {} {}".format(SPEC, base_of(loop)),
        "/skillworks:spec-drift {} {} S2, The user docs".format(SPEC, base_of(loop))]
    log = loop.log()
    assert "COUNT the re-check was asked about 2 items, and the drift report gives 2 Verdicts" in log
    assert (loop.records() / "drift-gaps.md").is_file()
    assert "STOP" not in log
    assert "END   spec #{}".format(SPEC) in log


def test_a_gap_left_after_the_round_stops_the_loop_naming_each_one(loop, runner):
    ran = drifted_in_a_round(
        loop, drift_report(S2="Missing. No code stops.", D1="Partial. Half of it."),
        verdicts_alone(S2="Missing. Still no code.", D1="Done"))

    assert ran.status == 1
    log = loop.log()
    assert ("STOP  the drift check still finds 1 Gap on spec #{} after the Gap ticket was built, "
            "and the loop goes round once. A person decides.").format(SPEC) in log
    assert "      Gap: S2 is Missing: Still no code.\n" in log
    assert "      Gap: D1" not in log
    assert len(runner.built("issue create")) == 1
    assert len(prompts_asking(runner, "/skillworks:spec-drift")) == 2
    assert "END" not in log


def test_a_re_check_that_recorded_no_new_report_stops_the_loop_saying_so(loop):
    report = drift_report(S2="Missing")
    ran = drifted_in_a_round(loop, report, report)

    assert ran.status == 1
    log = loop.log()
    assert ("STOP  the re-check recorded no new report on spec #{}, so the Gap items were not "
            "judged again").format(SPEC) in log
    assert "still finds" not in log
    assert "END" not in log


def test_a_re_check_that_recorded_no_new_report_after_denials_gives_the_way_past_them(loop):
    report = drift_report(S2="Missing")
    ran = drifted_in_a_round(loop, report, report, A_DENIED_WRITE)

    assert ran.status == 1
    assert 'Denial: Write {"file_path": ".claude/rules/words.md"' in loop.log()
    assert BYPASS in loop.log()


def test_an_item_the_re_check_skips_is_a_gap_left_after_the_round(loop):
    ran = drifted_in_a_round(loop, drift_report(S2="Missing", D1="Missing"),
                             verdicts_alone(S2="Done"))

    assert ran.status == 1
    assert "      Gap: D1 has no Verdict\n" in loop.log()


def test_a_verdict_the_re_check_was_not_asked_for_is_warned_of_and_stops_nothing(loop):
    ran = drifted_in_a_round(loop, drift_report(S2="Missing"), verdicts_alone(S2="Done", S1="Done"))

    assert ran.status == 0, said(ran)
    assert ("WARN  the drift report judges S1, which the re-check was not asked about, so its "
            "Verdict is not counted") in loop.log()


def test_a_contradicts_in_the_re_check_stops_the_loop(loop):
    ran = drifted_in_a_round(loop, drift_report(S2="Missing"),
                             verdicts_alone(S2="Contradicts. It closes the spec."))

    assert ran.status == 1
    assert "      Contradicts: S2: It closes the spec.\n" in loop.log()
    assert "END" not in loop.log()


# --- the Name check ------------------------------------------------------------

def named_back(loop, report, *denials):
    tracker = given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    given_a_session_that_was_denied(given_sessions_that_report(loop), "spec-names", *denials)
    given_the_closed_ticket_landed_after_the_base(loop)
    tracker.name_report = report
    return loop.run(SPEC)


def test_a_name_check_that_finds_no_rename_goes_on_to_a_clean_finish(loop, runner):
    ran = named_back(loop, NO_RENAMES)

    assert ran.status == 0, said(ran)
    assert prompts_asking(runner, NAME_CHECK) == [
        "{} {} {}".format(NAME_CHECK, SPEC, base_of(loop))]
    log = loop.log()
    assert "NAMES the report is recorded on spec #{}".format(SPEC) in log
    assert "NAMES no rename is owed on spec #{}".format(SPEC) in log
    assert (loop.records() / "names.md").read_text(encoding="utf-8") == "### Renames\n\n- None\n"
    assert log.index("COUNT") < log.index("NAMES") < log.index("END   spec #{}".format(SPEC))


def test_the_name_check_runs_after_the_gap_round(loop, runner):
    ran = drifted_in_a_round(loop, drift_report(S2="Missing"), verdicts_alone(S2="Done"))

    assert ran.status == 0, said(ran)
    judged = [call[2].split()[0] for call in session_calls(runner) if call[2].startswith(JUDGES)]
    assert judged == ["/skillworks:spec-drift", "/skillworks:spec-drift", NAME_CHECK]


def test_the_name_check_names_the_session_that_started_the_driver(loop, runner, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "parent-session")
    named_back(loop, NO_RENAMES)

    assert session_calls(runner)[-1][2].startswith(NAME_CHECK)
    assert changes_given_to_sessions(runner)[-1].get("OTEL_RESOURCE_ATTRIBUTES") == PARENT


def test_the_name_check_is_handed_no_ticket_trailer(loop, runner, monkeypatch):
    monkeypatch.setenv(TICKET_VARIABLE, "#1")
    named_back(loop, NO_RENAMES)

    assert handed_no_trailer(runner, NAME_CHECK)


def test_a_name_check_that_recorded_no_report_stops_the_loop(loop):
    ran = named_back(loop, "Looks good to me.\n")

    assert ran.status == 1
    assert ("STOP  the Name check recorded no report on spec #{}, so no name was read and the "
            "spec stays open.").format(SPEC) in loop.log()
    assert not (loop.records() / "names.md").exists()
    assert "END" not in loop.log()


def test_a_name_check_that_recorded_no_report_after_denials_gives_the_way_past_them(loop):
    ran = named_back(loop, "Looks good to me.\n", A_DENIED_COMMAND)

    assert ran.status == 1
    assert 'Denial: Bash {"command": "rm -rf .claude/worktrees"}' in loop.log()
    assert BYPASS in loop.log()


def test_a_name_report_with_no_renames_list_stops_the_loop(loop):
    ran = named_back(loop, "## Name report\n\nEvery name is true.\n")

    assert ran.status == 1
    assert ("STOP  the Name report on spec #{} holds no ### Renames list, so no rename was "
            "read").format(SPEC) in loop.log()
    assert "END" not in loop.log()


def test_a_drift_stop_runs_no_name_check(loop, runner):
    ran = drifted(loop, drift_report(D1="Contradicts. It closes the spec."))

    assert ran.status == 1
    assert prompts_asking(runner, NAME_CHECK) == []


def test_no_rename_files_no_rename_ticket_and_runs_no_name_re_check(loop, runner):
    ran = named_back(loop, NO_RENAMES)

    assert ran.status == 0, said(ran)
    assert not runner.built("issue create")
    assert len(prompts_asking(runner, NAME_CHECK)) == 1
    assert "FILED" not in loop.log()


# --- the rename ticket ---------------------------------------------------------

# Numbered after the one closed ticket, and there is no Gap ticket before it.
RENAME_TICKET = "162"

RENAMED = ("`Batch`: it now holds a whole spec.",
           "Gap and Hole: two tickets named one concept two ways, and no glossary word.")


def rename_verdicts(**given):
    return "## Name report\n\n### Verdicts\n\n" + "".join(
        "- {}: {}\n".format(name.replace("_", " "), said) for name, said in given.items())


# Each Name check records the next report, so the Name re-check reads its own and not the first.
def given_name_reports(sessions, tracker, *reports):
    waiting = list(reports)

    def record():
        tracker.name_report = waiting.pop(0)
    sessions.then["spec-names"] = record


def renamed_in_a_round(loop, second, first=name_report(*RENAMED), *denials):
    tracker = given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    sessions = given_sessions_that_report(loop)
    given_a_session_that_was_denied(sessions, "spec-names", *denials)
    given_the_closed_ticket_landed_after_the_base(loop)
    given_a_filed_ticket_that_lands(loop, tracker, sessions, RENAME_TICKET)
    given_name_reports(sessions, tracker, first, second)
    return loop.run(SPEC)


def test_each_rename_is_logged_and_filed_as_one_rename_ticket(loop, runner):
    ran = renamed_in_a_round(loop, rename_verdicts(Batch="Done", Gap_and_Hole="Done"))

    assert ran.status == 0, said(ran)
    log = loop.log()
    assert "NAME  `Batch`: it now holds a whole spec.\n" in log
    assert ("FILED #{} under spec #{} makes 2 renames, so the loop builds it and checks each "
            "one").format(RENAME_TICKET, SPEC) in log
    created = runner.built("issue create")
    assert len(created) == 1
    title = created[0][created[0].index("--title") + 1]
    body = created[0][created[0].index("--body") + 1]
    assert title == "TICKET: Make the renames the Name check found"
    assert "### Batch\n\n> `Batch`: it now holds a whole spec.\n" in body
    assert "### Gap and Hole\n\n> Gap and Hole: two tickets" in body
    assert "ready-for-agent" in created[0]


def test_a_concept_with_no_glossary_word_gets_a_note(loop):
    renamed_in_a_round(loop, rename_verdicts(Batch="Done", Gap_and_Hole="Done"))

    log = loop.log()
    assert ("NOTE  Gap and Hole has no glossary word, so the rename takes the name the code and the "
            "spec use most. A person settles the word.\n") in log
    assert "NOTE  Batch" not in log


def test_the_rename_ticket_is_built_through_every_step_after_the_gap_round(loop, runner):
    ran = renamed_in_a_round(loop, rename_verdicts(Batch="Done", Gap_and_Hole="Done"))

    assert ran.status == 0, said(ran)
    asked = [call[2].split()[0] for call in step_calls(runner)
             if call[2].split()[1:2] == [RENAME_TICKET]]
    assert asked == ["/skillworks:" + name for name in (
        "implement", "review-standards", "review-spec", "review-architecture", "implement",
        "implement")]
    log = loop.log()
    assert log.index("COUNT") < log.index("FILED") < log.index("DONE  #" + RENAME_TICKET)


def test_the_rename_ticket_s_sessions_are_handed_its_trailer(loop, runner):
    ran = renamed_in_a_round(loop, rename_verdicts(Batch="Done", Gap_and_Hole="Done"))

    assert ran.status == 0, said(ran)
    assert set(trailers_handed_for(runner, RENAME_TICKET)) == {"#" + RENAME_TICKET}


def test_a_rename_made_is_checked_on_the_rename_ticket_alone_and_ends_the_run(loop, runner):
    ran = renamed_in_a_round(loop, rename_verdicts(Batch="Done", Gap_and_Hole="Done"))

    assert ran.status == 0, said(ran)
    assert prompts_asking(runner, NAME_CHECK) == [
        "{} {} {}".format(NAME_CHECK, SPEC, base_of(loop)),
        "{} {} {} {}".format(NAME_CHECK, SPEC, base_of(loop), RENAME_TICKET)]
    log = loop.log()
    assert "COUNT the rename ticket owes 2 renames, and the Name re-check gives 2 Verdicts" in log
    assert "NAMES every rename is made on spec #{}".format(SPEC) in log
    assert (loop.records() / "names-renames.md").is_file()
    assert "STOP" not in log
    assert log.index("NAMES every rename") < log.index("END   spec #{}".format(SPEC))


def test_a_rename_not_made_stops_the_loop_naming_it(loop, runner):
    ran = renamed_in_a_round(loop, rename_verdicts(Batch="Done",
                                                   Gap_and_Hole="Not done. Hole is in two files."))

    assert ran.status == 1
    log = loop.log()
    assert ("STOP  the Name re-check finds 1 rename not made on spec #{} after the rename ticket "
            "was built. A person decides.").format(SPEC) in log
    assert "      Not made: Gap and Hole is Not done: Hole is in two files.\n" in log
    assert "Not made: Batch" not in log
    assert len(runner.built("issue create")) == 1
    assert "END" not in log


def test_a_rename_the_check_skips_or_judges_twice_is_not_made(loop):
    ran = renamed_in_a_round(loop, rename_verdicts(Batch="Done") + "- Batch: Done\n")

    assert ran.status == 1
    log = loop.log()
    assert "      Not made: Batch has 2 Verdicts: Done, Done\n" in log
    assert "      Not made: Gap and Hole has no Verdict\n" in log


def test_a_verdict_for_a_rename_the_ticket_does_not_owe_is_warned_of_and_stops_nothing(loop):
    ran = renamed_in_a_round(loop, rename_verdicts(Batch="Done", Gap_and_Hole="Done",
                                                   Stint="Not done. Typo."))

    assert ran.status == 0, said(ran)
    assert ("WARN  the Name re-check judges Stint, which the rename ticket does not owe, so its "
            "Verdict is not counted") in loop.log()


def test_a_name_re_check_that_recorded_no_new_report_stops_the_loop(loop):
    report = name_report(*RENAMED)
    ran = renamed_in_a_round(loop, report, report)

    assert ran.status == 1
    assert ("STOP  the Name re-check recorded no new report on spec #{}, so no rename was "
            "checked").format(SPEC) in loop.log()
    assert "END" not in loop.log()


def test_a_name_re_check_that_recorded_no_new_report_after_denials_gives_the_way_past_them(loop):
    report = name_report(*RENAMED)
    ran = renamed_in_a_round(loop, report, report, A_DENIED_COMMAND)

    assert ran.status == 1
    assert 'Denial: Bash {"command": "rm -rf .claude/worktrees"}' in loop.log()
    assert BYPASS in loop.log()


def test_a_name_re_check_with_no_verdicts_list_stops_the_loop(loop):
    ran = renamed_in_a_round(loop, "## Name report\n\nEvery rename is made.\n")

    assert ran.status == 1
    assert ("STOP  the Name re-check on spec #{} holds no ### Verdicts list, so no rename was "
            "counted").format(SPEC) in loop.log()
    assert "END" not in loop.log()


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


LOOP_OVERVIEW = "docs/usage/the-loop.md"


def test_the_stops_page_names_the_bypass_flag():
    text = (ROOT / STOPS_PAGE).read_text(encoding="utf-8")

    assert "--bypass" in text


# A heading inside a fence belongs to an example file, so it never ends the section.
def page_section(text, heading):
    held = []
    fenced = False
    for line in text.split("\n" + heading + "\n", 1)[1].split("\n"):
        if line.startswith("## ") and not fenced:
            break
        if line.startswith("```"):
            fenced = not fenced
        held.append(line)
    return "\n".join(held)


LOOP_FOLDER = "docs/usage/the-loop"

TARGET_BRANCH_PAGE = LOOP_FOLDER + "/target-branch.md"

TRACKER_PAGE = LOOP_FOLDER + "/tracker.md"

GRILL_PAGE = LOOP_FOLDER + "/the-grill.md"

TICKETS_PAGE = LOOP_FOLDER + "/tickets.md"

STEPS_PAGE = LOOP_FOLDER + "/steps.md"

LANDING_PAGE = LOOP_FOLDER + "/landing.md"

DRIFT_CHECK_PAGE = LOOP_FOLDER + "/drift-check.md"

NAME_CHECK_PAGE = LOOP_FOLDER + "/name-check.md"

FULL_RUN_PAGE = LOOP_FOLDER + "/full-run.md"

STOPS_PAGE = LOOP_FOLDER + "/stops.md"

READING_A_RUN_PAGE = LOOP_FOLDER + "/reading-a-run.md"

STAGE_MAP_PAGE = LOOP_FOLDER + "/stage-map.md"

SESSIONS_PAGE = LOOP_FOLDER + "/sessions.md"


def loop_folder_pages():
    return sorted((ROOT / LOOP_FOLDER).glob("*.md"))


def test_the_loop_folder_holds_the_pages_split_from_the_loop_page():
    assert {ROOT / TARGET_BRANCH_PAGE, ROOT / TRACKER_PAGE, ROOT / GRILL_PAGE,
            ROOT / TICKETS_PAGE, ROOT / STEPS_PAGE, ROOT / LANDING_PAGE,
            ROOT / DRIFT_CHECK_PAGE, ROOT / NAME_CHECK_PAGE,
            ROOT / FULL_RUN_PAGE, ROOT / STOPS_PAGE, ROOT / READING_A_RUN_PAGE,
            ROOT / STAGE_MAP_PAGE, ROOT / SESSIONS_PAGE} <= set(loop_folder_pages())


def page_text(page):
    return (ROOT / page).read_text(encoding="utf-8")


def flat(text):
    return " ".join(text.split())


def test_the_stops_page_holds_when_a_step_fails_the_keep_and_a_denial():
    text = page_text(STOPS_PAGE)

    assert text.startswith("# When a step fails\n")
    for heading in ["\n## Restarting a stopped run: the Keep\n", "\n## A Denial, and `--bypass`\n"]:
        assert heading in text, heading
    assert 'rerun["Rerun: Keep, then build again"]' in text


def test_the_reading_a_run_page_holds_reading_a_run():
    text = page_text(READING_A_RUN_PAGE)

    assert text.startswith("# Reading a run\n")
    assert "The log is `.spec-loop/<spec>/loop.log`." in text


def test_the_reading_a_run_page_links_the_stops_page():
    reading = flat(page_text(READING_A_RUN_PAGE))

    assert "in place of the `SCOPE` line, as [When a step fails](stops.md) shows." in reading
    assert "with no commit to read, as [When a step fails](stops.md) shows." in reading


def test_the_stage_map_page_holds_the_stage_map():
    text = page_text(STAGE_MAP_PAGE)

    assert text.startswith("# The stage map\n")
    assert "[Steering](../steering.md) has the detail on each file." in flat(text)


def test_the_overview_holds_only_its_text_its_chart_and_its_table():
    headings = [line for line in page_text(LOOP_OVERVIEW).split("\n") if line.startswith("#")]

    assert headings == ["# The Dev loop", "## The pages of the loop"]


def overview_charts():
    opening = (ROOT / LOOP_OVERVIEW).read_text(encoding="utf-8").split("\n## ", 1)[0]
    return re.findall(r"```mermaid\n(.*?)```", opening, re.DOTALL)


def test_the_overview_holds_one_small_chart_of_the_loop():
    charts = overview_charts()
    boxes = set(re.findall(r"\b(\w+)\s*[\[{(]", charts[0])) if charts else set()

    assert len(charts) == 1
    assert 6 <= len(boxes) <= 10, boxes


def test_the_overview_no_longer_holds_the_large_chart():
    text = (ROOT / LOOP_OVERVIEW).read_text(encoding="utf-8")

    for node in ['drift["Drift check', 'names["Name check', 'renames["The rename ticket',
                 'clean["A clean finish']:
        assert node not in text, node


def test_the_stops_and_reading_a_run_pages_link_the_full_run_and_a_clean_finish():
    stopping = flat(page_text(STOPS_PAGE))
    reading = flat(page_text(READING_A_RUN_PAGE))

    assert "[the full run](full-run.md) runs next" in stopping
    assert "`END` comes only on [a clean finish](full-run.md#a-clean-finish)." in reading


def test_the_stops_page_links_the_count_the_gap_round_and_the_name_check():
    stopping = flat(page_text(STOPS_PAGE))

    assert "[counts the drift check's Verdicts](drift-check.md#the-count)" in stopping
    assert "[one round](drift-check.md#the-gap-round)" in stopping
    assert "[the Name check](name-check.md)" in stopping
    assert "[the rename ticket](name-check.md#the-rename-ticket)" in stopping
    assert "[the Name re-check](name-check.md#the-name-re-check)" in stopping


def test_the_reading_a_run_page_links_the_gap_round_and_the_rename_ticket():
    reading = flat(page_text(READING_A_RUN_PAGE))

    assert "[the Gap round](drift-check.md#the-gap-round) adds its lines" in reading
    assert "[the rename ticket](name-check.md#the-rename-ticket) adds its lines" in reading


def test_the_steps_page_holds_the_steps_an_edit_the_run_by_hand_and_the_suite():
    text = (ROOT / STEPS_PAGE).read_text(encoding="utf-8")
    page = " ".join(text.split())

    assert text.startswith("# The steps of one ticket\n")
    assert "\n## The Suite\n" in text
    assert "**An Edit.**" in page
    assert "**The run by hand.**" in page
    assert "[The Suite](../suite.md) has the whole file." in page
    assert "When [the full run](full-run.md) left its worktree in place" in page
    overview = (ROOT / LOOP_OVERVIEW).read_text(encoding="utf-8")
    assert "### The steps of one ticket" not in overview
    assert "### The Suite" not in overview


def test_the_steps_page_says_the_reviews_start_fresh_and_fix_and_finish_resume():
    page = " ".join((ROOT / STEPS_PAGE).read_text(encoding="utf-8").split())

    assert ("The three reviews start Fresh. A review that resumed the build Session would mark its "
            "own work. `fix` and `finish` resume the build Session") in page


def test_the_landing_page_holds_rebasing_and_landing_with_the_push_race_and_the_turn():
    text = (ROOT / LANDING_PAGE).read_text(encoding="utf-8")
    page = " ".join(text.split())

    assert text.startswith("# Rebasing and Landing\n")
    assert "\n## The push race and the Turn\n" in text
    assert "Nothing is pushed unless every step passes." in page
    assert "The **Turn** is the right to push" in page
    assert "## Rebasing and Landing" not in (ROOT / LOOP_OVERVIEW).read_text(encoding="utf-8")


def test_the_stops_page_links_the_round_a_red_suite_goes_on_the_steps_page():
    stopping = flat(page_text(STOPS_PAGE))

    assert "the round a red Suite goes, in [the Suite](steps.md#the-suite)." in stopping


def loop_pages():
    return [ROOT / LOOP_OVERVIEW] + loop_folder_pages()


def session_of_each_call():
    table = page_section(page_text(SESSIONS_PAGE), "## Every call in a run")
    return dict(re.findall(r"^\| `([^`]+)` \| ([^|]+?) \|", table, re.MULTILINE))


def session_the_driver_gives(step):
    if not step.session:
        return "No Session"
    return "Resumed" if step.resumes else "Fresh"


def test_the_sessions_page_says_resumed_exactly_where_the_driver_resumes():
    said = session_of_each_call()

    assert {step.name: said.get(step.name) for step in spec_loop.STEPS} == {
        step.name: session_the_driver_gives(step) for step in spec_loop.STEPS}


def test_the_sessions_page_holds_a_sequence_chart_the_two_call_shapes_and_the_word_fresh():
    text = page_text(SESSIONS_PAGE)

    assert "```mermaid\nsequenceDiagram\n" in text
    assert '`claude -p "<prompt>" --session-id <new id>`' in text
    assert '`claude -p "<prompt>" --resume <build session>`' in text
    assert re.search(r"\bFresh\b", text)


def test_no_page_of_the_loop_says_cold_of_a_session():
    saying = [page.name for page in loop_pages()
              if re.search(r"\bcold\b", page.read_text(encoding="utf-8"), re.IGNORECASE)]

    assert saying == []


def test_no_page_of_the_loop_says_fresh_in_lower_case():
    saying = [page.name for page in loop_pages()
              if re.search(r"\bfresh\b", page.read_text(encoding="utf-8"))]

    assert saying == []


def test_the_grill_page_holds_stage_one_the_grill_the_gate_and_the_spec():
    text = (ROOT / GRILL_PAGE).read_text(encoding="utf-8")

    assert text.startswith("# Stage one: settle the design\n")
    for heading in ["\n## The grill\n", "\n## The gate\n", "\n## The spec\n"]:
        assert heading in text, heading
    assert "## Stage one" not in (ROOT / LOOP_OVERVIEW).read_text(encoding="utf-8")


def test_the_tickets_page_holds_the_cut_picking_claiming_and_the_worktrees():
    text = (ROOT / TICKETS_PAGE).read_text(encoding="utf-8")
    page = " ".join(text.split())

    assert text.startswith("# The tickets\n")
    assert "\n## Worktrees and Job branches\n" in text
    assert "the **Cut**" in page
    assert "**Picking a ticket** is a query, not a judgement." in page
    assert "as [the Tracker](tracker.md#a-claim-and-a-close) says." in page
    assert "| The Job branch | `spec-loop/<spec>/ticket-<n>` |" in text
    overview = (ROOT / LOOP_OVERVIEW).read_text(encoding="utf-8")
    assert "### The tickets" not in overview
    assert "### Worktrees and Job branches" not in overview


def overview_table_links():
    table = page_section((ROOT / LOOP_OVERVIEW).read_text(encoding="utf-8"), "## The pages of the loop")
    return re.findall(r"^\| \[[^\]]+\]\(([^)]+)\) \|", table, re.MULTILINE)


def test_the_overview_s_table_lists_the_pages_in_run_order():
    assert overview_table_links() == ["the-loop/target-branch.md", "the-loop/tracker.md",
                                      "the-loop/the-grill.md", "the-loop/tickets.md",
                                      "the-loop/steps.md", "the-loop/landing.md",
                                      "the-loop/drift-check.md", "the-loop/name-check.md",
                                      "the-loop/full-run.md", "the-loop/stops.md",
                                      "the-loop/reading-a-run.md", "the-loop/stage-map.md",
                                      "the-loop/sessions.md"]


def test_each_page_in_the_loop_folder_opens_with_a_link_back_to_the_overview():
    for page in loop_folder_pages():
        lines = [line for line in page.read_text(encoding="utf-8").split("\n") if line.strip()]

        assert lines[0].startswith("# "), page.name
        assert "](../the-loop.md)" in lines[1], page.name


def test_the_target_branch_page_explains_both_kinds_of_target_branch():
    text = (ROOT / TARGET_BRANCH_PAGE).read_text(encoding="utf-8")

    assert text.startswith("# The Target branch\n")
    for named in ["`docs/agents/loop.json`", "`target-branch`", "`spec`", "`spec/<slug>`"]:
        assert named in text, named
    assert "Pick a branch name when" in text
    assert "Pick `spec` when" in text


def test_the_tracker_page_explains_the_files_tracker_beside_github():
    text = (ROOT / TRACKER_PAGE).read_text(encoding="utf-8")

    assert text.startswith("# The Tracker\n")
    for named in ["`docs/agents/loop.json`", "`tracker`", "`github`", "`files`", "`.specs/`",
                  "status: open", "blocked-by:", "claimed-by:", "gitignored", "## Closing note"]:
        assert named in text, named
    assert "Pick `github` when" in text
    assert "Pick `files` when" in text


def test_the_grill_page_gives_the_counted_shape():
    the_spec = " ".join(page_section((ROOT / GRILL_PAGE).read_text(encoding="utf-8"),
                                     "## The spec").split())

    for named in ["**User Stories**", "**Implementation Decisions**", "**Surfaces**", "`S1`", "`D1`",
                  "starts at 1", "in bold", '"None"', "Testing Decisions are not counted",
                  "turned down"]:
        assert named in the_spec, named


def test_the_stops_page_gives_the_stop_for_a_spec_in_another_shape():
    stopping = flat(page_text(STOPS_PAGE))

    assert "the spec's [counted shape](the-grill.md#the-spec)" in stopping
    assert "ABORT spec #200 is not in the shape the loop counts" in stopping


def test_the_reading_a_run_page_gives_the_shape_line_and_its_abort():
    reading = page_text(READING_A_RUN_PAGE)

    assert "SHAPE spec #200 holds" in reading
    assert "`ABORT` line" in reading


def test_the_tracker_page_shows_a_spec_file_and_a_ticket_file():
    text = (ROOT / TRACKER_PAGE).read_text(encoding="utf-8")
    shown = re.findall(r"```markdown\n(.*?)```", text, re.DOTALL)

    assert any(block.startswith("---\n") and "# SPEC:" in block for block in shown)
    assert any(block.startswith("---\n") and "# TICKET:" in block for block in shown)


@pytest.mark.parametrize("page", ["docs/usage/setup.md", "docs/usage/steering.md"])
def test_the_setup_and_steering_pages_describe_the_tracker_setting(page):
    text = (ROOT / page).read_text(encoding="utf-8")

    for named in ["`tracker`", "`github`", "`files`", "`.specs/`"]:
        assert named in text, named


def test_the_setup_page_links_the_tracker_page_and_the_target_branch_page():
    text = (ROOT / "docs/usage/setup.md").read_text(encoding="utf-8")

    assert "[The loop](the-loop/tracker.md) says how to choose a Tracker" in text
    assert "[the Target branch](the-loop/target-branch.md) how to choose a Target branch" in text


def test_the_steering_page_links_the_tracker_page():
    text = (ROOT / "docs/usage/steering.md").read_text(encoding="utf-8")

    assert "(the-loop/tracker.md) says how to choose each one." in text


def test_the_steering_page_links_the_stage_map_page():
    assert "](the-loop/stage-map.md)" in page_text("docs/usage/steering.md")


def test_the_index_of_the_user_docs_has_one_row_for_the_loop_saying_the_overview_links_each_part():
    rows = [line for line in (ROOT / "docs/usage/README.md").read_text(encoding="utf-8").split("\n")
            if "the-loop" in line]

    assert len(rows) == 1
    assert rows[0].startswith("| [The loop](the-loop.md) |")
    assert "links each part" in rows[0]


def test_the_landing_chart_names_the_target_branch_and_never_main():
    landing = (ROOT / LANDING_PAGE).read_text(encoding="utf-8")
    chart = landing.split("```mermaid\n", 1)[1].split("```", 1)[0]

    assert "Target branch" in chart
    assert re.search(r"\bmain\b", chart) is None


def test_the_loop_page_never_names_main():
    assert re.search(r"\bmain\b", (ROOT / LOOP_OVERVIEW).read_text(encoding="utf-8")) is None


def test_no_page_in_the_loop_folder_but_the_target_branch_page_names_main():
    naming = [page.name for page in loop_folder_pages()
              if re.search(r"\bmain\b", page.read_text(encoding="utf-8"))]

    assert naming == ["target-branch.md"]


def test_the_target_branch_page_names_main_only_as_an_example_of_a_target_branch():
    paragraphs = (ROOT / TARGET_BRANCH_PAGE).read_text(encoding="utf-8").split("\n\n")
    naming = [paragraph for paragraph in paragraphs if re.search(r"\bmain\b", paragraph)]

    assert [paragraph.split("\n")[0] for paragraph in naming] == [
        "**A branch name**, such as `main`, `master` or `develop`. That branch is the Target branch for every",
        "```json"]
    assert '{ "target-branch": "main" }' in naming[1]


# --- what the landing says, and when ----------------------------------------

WAITS = "waits for the Turn"

STAMP = r"[0-9]{2}:[0-9]{2}:[0-9]{2} "


def given_a_run_that_lands(loop):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(committed(loop.runner), closed(tracker))
    return tracker


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


# --- the full run after a run that landed a ticket ---------------------------

TWO_OPEN_TICKETS = (("168", "open", "TICKET: The dry run prints the plan"),
                    ("169", "open", "TICKET: Blocked behind somebody else's"))


def full_run_tree(loop):
    return loop.repo.tree(SPEC, "full-run").as_posix()


def full_run_calls(loop, name):
    return [call.args for call in loop.runner.made
            if call.args[0] == name and call.where == full_run_tree(loop)]


def full_run_outputs(loop):
    return sorted(loop.records().glob("full-run-*.out"))


# Red in the full run alone, so the ticket's own Suite step still passes.
def given_a_full_run_that_goes_red(loop):
    def answer():
        if loop.runner.where == full_run_tree(loop):
            return Ran(1, "a test failed on this OS\n", "")
        return None
    loop.runner.stub("dotnet", says="the solution passed", does=answer)


# Blocked on another spec, so the loop lands 168 and then stops, stuck on 169.
def given_a_run_that_lands_one_ticket_then_sticks(loop):
    tracker = given_the_tracker_holds(loop, TWO_OPEN_TICKETS)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(committed(loop.runner), closed(tracker))
    asked = tracker.answer

    def answer():
        if "issues/169" in " ".join(loop.runner.calls[-1]) and "blocked_by" in " ".join(
                loop.runner.calls[-1]):
            return Ran(0, "1\n", "")
        return asked()
    loop.runner.stub("gh", does=answer)


# The Proof made on main holds every input the ticket leaves, so only a full run starts dotnet.
def test_a_run_that_landed_a_ticket_runs_the_whole_suite_after_it_trusting_no_proof(loop, runner):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_suite_on_the_target(
        loop, check("dotnet", "test", "Skillworks.slnx", ignores=["built.txt"]))
    earlier = RecordingRunner()
    earlier.stub("dotnet")
    assert Suite(earlier, loop.repo.work).run().passed
    runner.stub("dotnet")
    sessions = Sessions(loop.repo, runner)
    sessions.then[FINISH] = all_of(committed(runner), closed(tracker))

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    assert [call.where for call in runner.made if call.args[0] == "dotnet"] == [
        full_run_tree(loop)]


def given_the_target_moves_once_the_ticket_has_landed(loop, tracker):
    def answer():
        asked = " ".join(loop.runner.calls[-1])
        if 'select(.state=="open")' in asked and "168" in tracker.closed:
            loop.repo.advance_origin("late")
        return tracker.answer()
    loop.runner.stub("gh", does=answer)


def test_the_full_run_is_on_a_new_worktree_of_the_newest_origin_main(loop, runner):
    tracker = given_a_run_that_lands(loop)
    given_the_target_moves_once_the_ticket_has_landed(loop, tracker)
    heads = []

    def head_of_the_full_run():
        if runner.where == full_run_tree(loop):
            heads.append(git(runner.where, "rev-parse", "HEAD").strip())
    runner.stub("dotnet", does=head_of_the_full_run)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    assert heads == [git(loop.repo.origin, "rev-parse", "main").strip()]
    assert "late.txt" in git(loop.repo.origin, "ls-tree", "--name-only", heads[0])
    assert not Path(full_run_tree(loop)).exists()


def test_a_run_that_landed_no_ticket_has_no_full_run(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert full_run_calls(loop, "dotnet") == []
    assert "FULL" not in loop.log()


def test_a_run_that_stopped_early_after_landing_a_ticket_still_has_a_full_run(loop):
    given_a_run_that_lands_one_ticket_then_sticks(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "STUCK" in said(ran)
    assert full_run_calls(loop, "dotnet") == [["dotnet", "test", "Skillworks.slnx"]]


def test_a_red_full_run_stops_the_loop_naming_the_red_checks_and_the_landed_tickets(loop):
    given_a_run_that_lands(loop)
    given_a_full_run_that_goes_red(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "the full run of the Suite went red" in said(ran)
    assert "Red: dotnet test Skillworks.slnx" in said(ran)
    assert "Landed in this run: #168" in said(ran)
    [held] = full_run_outputs(loop)
    assert "a test failed on this OS" in held.read_text(encoding="utf-8")


def test_a_red_full_run_tries_no_fix_and_leaves_the_spec_open(loop, runner):
    given_a_run_that_lands(loop)
    given_a_full_run_that_goes_red(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert len(prompts_asking(runner, "/skillworks:implement 168 --fix")) == 1
    assert not runner.built("issue close")
    assert "END" not in loop.log()


def test_the_full_run_runs_once_and_last_after_the_drift_check_and_its_count(loop, runner):
    given_a_run_that_lands(loop)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    assert len(full_run_calls(loop, "dotnet")) == 1
    log = loop.log()
    assert log.count("FULL  #168 landed in this run") == 1
    assert log.index("DRIFT") < log.index("COUNT") < log.index("FULL  #168 landed in this run")
    drift = next(at for at, call in enumerate(runner.made)
                 if call.args[0] == "claude" and call.args[2].startswith("/skillworks:spec-drift"))
    full = next(at for at, call in enumerate(runner.made)
                if call.args[0] == "dotnet" and call.where == full_run_tree(loop))
    assert drift < full


def given_a_run_that_lands_and_goes_round(loop, *reports):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(committed(loop.runner), closed(tracker))
    given_a_filed_ticket_that_lands(loop, tracker, sessions, "169")
    given_drift_reports(sessions, tracker, *reports)
    return tracker


def test_a_gap_left_after_the_round_still_gets_the_full_run_and_writes_no_end(loop):
    given_a_run_that_lands_and_goes_round(loop, drift_report(S1="Missing. Not there."),
                                          verdicts_alone(S1="Missing. Not there."))

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert full_run_calls(loop, "dotnet") == [["dotnet", "test", "Skillworks.slnx"]]
    log = loop.log()
    assert "      Gap: S1 is Missing: Not there.\n" in log
    assert "FULL  #168, #169 landed in this run" in log
    assert "FULL  main at" in log
    assert "END" not in log


def test_the_full_run_runs_once_and_last_after_the_gap_round(loop, runner):
    given_a_run_that_lands_and_goes_round(loop, drift_report(S1="Missing"), verdicts_alone(S1="Done"))

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    assert len(full_run_calls(loop, "dotnet")) == 1
    log = loop.log()
    assert log.index("DONE  #169") < log.index("COUNT the re-check") < log.index("FULL  #168, #169")
    re_check = max(at for at, call in enumerate(runner.made) if call.args[0] == "claude"
                   and call.args[2].startswith("/skillworks:spec-drift"))
    full = next(at for at, call in enumerate(runner.made)
                if call.args[0] == "dotnet" and call.where == full_run_tree(loop))
    assert re_check < full


def test_the_full_run_runs_after_the_name_check(loop, runner):
    given_a_run_that_lands(loop)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    log = loop.log()
    assert log.index("NAMES no rename is owed") < log.index("FULL  #168 landed in this run")
    names = next(at for at, call in enumerate(runner.made)
                 if call.args[0] == "claude" and call.args[2].startswith(NAME_CHECK))
    full = next(at for at, call in enumerate(runner.made)
                if call.args[0] == "dotnet" and call.where == full_run_tree(loop))
    assert names < full


def given_a_run_that_lands_and_renames(loop, *reports):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(committed(loop.runner), closed(tracker))
    given_a_filed_ticket_that_lands(loop, tracker, sessions, "169")
    given_name_reports(sessions, tracker, *reports)
    return tracker


def test_a_rename_not_made_still_gets_the_full_run_once_and_last_and_writes_no_end(loop, runner):
    given_a_run_that_lands_and_renames(loop, name_report("`Batch`: it now holds a whole spec."),
                                       rename_verdicts(Batch="Not done. It is still there."))

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert full_run_calls(loop, "dotnet") == [["dotnet", "test", "Skillworks.slnx"]]
    log = loop.log()
    assert "      Not made: Batch is Not done: It is still there.\n" in log
    assert "FULL  #168, #169 landed in this run" in log
    assert "END" not in log
    name_re_check = max(at for at, call in enumerate(runner.made) if call.args[0] == "claude"
                       and call.args[2].startswith(NAME_CHECK))
    full = next(at for at, call in enumerate(runner.made)
                if call.args[0] == "dotnet" and call.where == full_run_tree(loop))
    assert name_re_check < full


def test_every_rename_made_is_a_clean_finish_after_the_full_run(loop):
    given_a_run_that_lands_and_renames(loop, name_report("`Batch`: it now holds a whole spec."),
                                       rename_verdicts(Batch="Done"))

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    log = loop.log()
    assert log.index("NAMES every rename is made") < log.index("FULL  #168, #169 landed")
    assert log.index("FULL  main at") < log.index("END   spec #{}".format(SPEC))


def test_a_red_full_run_after_every_verdict_done_writes_no_end(loop):
    given_a_run_that_lands(loop)
    given_a_full_run_that_goes_red(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    log = loop.log()
    assert "COUNT the spec holds 5 items, and the drift report gives 5 Verdicts" in log
    assert "RED   the full run of the Suite went red" in log
    assert "END" not in log


def test_a_red_full_run_after_an_early_stop_names_why_the_loop_stopped_too(loop):
    given_a_run_that_lands_one_ticket_then_sticks(loop)
    given_a_full_run_that_goes_red(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "Red: dotnet test Skillworks.slnx" in said(ran)
    assert "STUCK" in said(ran)


def test_the_log_shows_the_full_run_and_its_result_before_the_end_line(loop):
    given_a_run_that_lands(loop)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    log = loop.log()
    started = log.index("FULL  #168 landed in this run")
    passed = log.index("FULL  run 1 passed")
    assert started < passed < log.index("END   spec #158 complete")


# --- a full run with a red or a Flake leaves its worktree --------------------

def given_a_full_run_that_flakes(loop):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop, runs=2)
    sessions.then[FINISH] = all_of(committed(loop.runner), closed(tracker))
    red = []

    def answer():
        if loop.runner.where == full_run_tree(loop) and not red:
            red.append(True)
            return Ran(1, "a full run test failed once\n", "")
        return None
    loop.runner.stub("dotnet", says="the solution passed", does=answer)
    return tracker


# 169 is blocked in the first loop alone, so each loop lands one ticket and has a full run.
def given_two_loops_that_each_land_a_ticket(loop):
    tracker = given_the_tracker_holds(loop, TWO_OPEN_TICKETS)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(committed(loop.runner), closed(tracker))
    given_a_filed_ticket_that_lands(loop, tracker, sessions, "169")
    blocked = {"169"}
    asked = tracker.answer

    def answer():
        call = " ".join(loop.runner.calls[-1])
        if "blocked_by" in call and any("issues/" + n in call for n in blocked):
            return Ran(0, "1\n", "")
        return asked()
    loop.runner.stub("gh", does=answer)
    return blocked


def given_a_first_loop_whose_full_run_went_red(loop):
    blocked = given_two_loops_that_each_land_a_ticket(loop)
    given_a_full_run_that_goes_red(loop)
    assert loop.run(SPEC).status == 1
    assert Path(full_run_tree(loop)).exists()
    blocked.clear()
    loop.runner.stub("dotnet", says="the solution passed")


def full_run_flake_files(loop):
    return sorted(loop.records().glob("flake-full-run-*.out"))


def test_each_full_run_writes_a_file_of_its_own_and_a_later_loop_empties_none(loop):
    given_a_first_loop_whose_full_run_went_red(loop)
    [first] = full_run_outputs(loop)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    assert re.fullmatch("full-run-" + FLAKE_STAMP + r"\.out", first.name)
    assert len(full_run_outputs(loop)) == 2
    assert "a test failed on this OS" in first.read_text(encoding="utf-8")


def test_a_full_run_flake_gets_a_flake_line_and_a_kept_red_output_file(loop):
    given_a_full_run_that_flakes(loop)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    [line] = flake_lines(loop)
    assert "FLAKE full-run          dotnet test Skillworks.slnx went red and then passed" in line
    [kept] = full_run_flake_files(loop)
    assert re.fullmatch("flake-full-run-" + FLAKE_STAMP + r"\.out", kept.name)
    assert "a full run test failed once" in kept.read_text(encoding="utf-8")
    assert kept.as_posix() in line


def test_a_full_run_with_a_flake_leaves_its_worktree_and_the_log_names_it(loop):
    given_a_full_run_that_flakes(loop)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    assert Path(full_run_tree(loop)).exists()
    assert "FULL  its worktree is left at {}".format(full_run_tree(loop)) in loop.log()
    assert "END   spec #158 complete" in loop.log()


def test_a_red_full_run_leaves_its_worktree_and_the_log_names_it(loop):
    given_a_run_that_lands(loop)
    given_a_full_run_that_goes_red(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert Path(full_run_tree(loop)).exists()
    assert "FULL  its worktree is left at {}".format(full_run_tree(loop)) in loop.log()


def test_a_clean_full_run_leaves_no_worktree(loop):
    given_a_run_that_lands(loop)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    assert not Path(full_run_tree(loop)).exists()
    assert "its worktree is left" not in loop.log()


def test_the_next_full_run_removes_a_left_full_run_worktree_before_it_opens_its_own(loop):
    given_a_first_loop_whose_full_run_went_red(loop)
    (Path(full_run_tree(loop)) / "crash.dmp").write_text("dump\n", encoding="utf-8")

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    log = loop.log()
    removed = log.index("FULL  removed the worktree the last full run left at {}".format(
        full_run_tree(loop)))
    assert log.index("FULL  #169 landed in this run") < removed < log.index("FULL  run 1 passed")
    assert not Path(full_run_tree(loop)).exists()
    assert "KEPT  full-run" not in log
    assert "full-run-kept" not in git(loop.repo.work, "branch", "--list", "spec-loop/*")


def test_a_left_full_run_worktree_that_will_not_go_stops_the_run_naming_it(loop, runner):
    given_a_first_loop_whose_full_run_went_red(loop)
    runner.refuse("worktree remove --force " + full_run_tree(loop), "the folder is in use")
    started = len(runner.made)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert ("FAIL  the worktree the last full run left at {} would not go, so this full run "
            "did not start.".format(full_run_tree(loop))) in said(ran)
    assert [call for call in runner.made[started:]
            if call.args[0] == "dotnet" and call.where == full_run_tree(loop)] == []


# --- the spec's note of the run's Flakes -------------------------------------

def note_calls(runner):
    return [call for call in runner.calls if call[:2] == ["gh", "issue"] and call[2] == "comment"]


def test_a_run_with_flakes_in_a_suite_step_and_the_full_run_adds_one_note_naming_each(loop):
    tracker = given_a_full_run_that_flakes(loop)
    given_a_suite_red_on_its_first_run_alone(loop.runner)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    [note] = tracker.notes
    assert note.startswith("## Flakes\n")
    [in_suite] = flake_files(loop, "suite")
    [in_full_run] = full_run_flake_files(loop)
    assert "- dotnet test Skillworks.slnx, in #168 suite: {}\n".format(in_suite.as_posix()) in note
    assert "- dotnet test Skillworks.slnx, in the full run: {}\n".format(
        in_full_run.as_posix()) in note
    assert "NOTE  spec #158 has a note listing the 2 Flakes of this run" in loop.log()


def test_the_note_names_the_full_runs_left_worktree(loop):
    tracker = given_a_full_run_that_flakes(loop)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    [note] = tracker.notes
    assert "The full run's worktree is left at {}.".format(full_run_tree(loop)) in note


def test_a_run_that_stops_early_with_a_flake_still_adds_the_note(loop, runner):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop, runs=2)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    [note] = tracker.notes
    [kept] = flake_files(loop, "suite")
    assert "in #168 suite: " + kept.as_posix() in note
    assert "worktree" not in note


def test_a_run_with_no_flake_adds_no_note(loop, runner):
    tracker = given_a_run_that_lands(loop)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    assert tracker.notes == []
    assert note_calls(runner) == []


def test_a_note_the_tracker_turns_down_is_warned_of_and_ends_nothing(loop, runner):
    given_a_full_run_that_flakes(loop)
    runner.refuse("issue comment", "GitHub is down")

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    assert "WARN  the note listing the Flakes of this run did not reach spec #158" in loop.log()
    assert "END   spec #158 complete" in loop.log()


# --- the Target branch ------------------------------------------------------

def test_a_run_with_no_loop_file_stops_before_it_starts_a_ticket_and_names_the_fix(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    (loop.repo.work / "docs" / "agents" / "loop.json").unlink()

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "FAIL  docs/agents/loop.json is missing. Run seed-steering to write it.\n" in loop.log()
    assert "\n\n" not in loop.log()
    assert not runner.built("issue edit")


# --- a Target branch named master --------------------------------------------

# A whole word, since a temporary folder named for a case can hold "main" inside a longer one.
def names_main(said):
    return re.search(r"\bmain\b", said) is not None


def test_a_run_on_master_lands_its_ticket_on_master_and_makes_no_main(master):
    given_a_run_that_lands(master)

    ran = master.run(SPEC)

    assert ran.status == 0, said(ran)
    assert git(master.repo.origin, "log", "-1", "--format=%s", "master").strip() == "Built"
    assert git(master.repo.origin, "for-each-ref", "--format=%(refname)",
               "refs/heads").split() == ["refs/heads/master"]


def test_a_run_on_master_runs_the_full_suite_on_the_newest_origin_master(master, runner):
    tracker = given_a_run_that_lands(master)
    given_the_target_moves_once_the_ticket_has_landed(master, tracker)
    heads = []

    def head_of_the_full_run():
        if runner.where == full_run_tree(master):
            heads.append(git(runner.where, "rev-parse", "HEAD").strip())
    runner.stub("dotnet", does=head_of_the_full_run)

    ran = master.run(SPEC)

    assert ran.status == 0, said(ran)
    assert heads == [git(master.repo.origin, "rev-parse", "master").strip()]
    assert "late.txt" in git(master.repo.origin, "ls-tree", "--name-only", heads[0])


def test_a_run_on_master_names_master_and_never_main(master):
    given_a_run_that_lands(master)
    base = git(master.repo.origin, "rev-parse", "master").strip()

    ran = master.run(SPEC)

    assert ran.status == 0, said(ran)
    assert "the whole Suite runs on the newest origin/master" in master.log()
    assert re.search(r"FULL  master at [0-9a-f]+ passed the whole Suite", master.log())
    assert "Every ticket is on master." in master.log()
    assert "git log --oneline {}..origin/master".format(base) in master.log()
    assert not names_main(said(ran)), said(ran)


def test_a_landing_on_master_that_fails_says_it_did_not_reach_master(master):
    given_a_run_that_lands(master)
    master.repo.refuse_pushes()

    ran = master.run(SPEC)

    assert ran.status == 1
    assert "FAIL  #168 did not reach master." in said(ran)
    assert not names_main(said(ran)), said(ran)


def test_a_red_full_run_on_master_names_master(master):
    given_a_run_that_lands(master)
    given_a_full_run_that_goes_red(master)

    ran = master.run(SPEC)

    assert ran.status == 1
    assert re.search(r"RED   the full run of the Suite went red on master at [0-9a-f]+", said(ran))
    assert not names_main(said(ran)), said(ran)


# --- a spec reviewed as one pull request ------------------------------------

def pull_request_calls(runner):
    return [call for call in runner.started("gh") if call[1] == "pr"]


def test_in_spec_mode_a_ticket_is_cut_from_and_lands_on_the_spec_branch_and_not_main(spec_mode):
    given_a_run_that_lands(spec_mode)
    suite_commit = git(spec_mode.repo.origin, "rev-parse", SPEC_BRANCH).strip()
    main = git(spec_mode.repo.origin, "rev-parse", "main").strip()

    ran = spec_mode.run(SPEC)

    assert ran.status == 0, said(ran)
    assert git(spec_mode.repo.origin, "log", "-1", "--format=%s", SPEC_BRANCH).strip() == "Built"
    assert git(spec_mode.repo.origin, "rev-parse", SPEC_BRANCH + "^").strip() == suite_commit
    assert git(spec_mode.repo.origin, "rev-parse", "main").strip() == main
    assert "Every ticket is on {}.".format(SPEC_BRANCH) in spec_mode.log()


def test_in_spec_mode_the_pull_request_is_marked_ready_after_the_drift_check(spec_mode, runner):
    given_a_run_that_lands(spec_mode)

    ran = spec_mode.run(SPEC)

    assert ran.status == 0, said(ran)
    assert pull_request_calls(runner) == [["gh", "pr", "ready", SPEC_BRANCH]]
    assert call_at(runner, "/skillworks:spec-drift") < call_at(runner, "pr ready")
    assert "READY the pull request from {} is ready for review".format(
        SPEC_BRANCH) in spec_mode.log()


def test_in_spec_mode_the_driver_never_merges_the_pull_request(spec_mode, runner):
    given_a_run_that_lands(spec_mode)

    ran = spec_mode.run(SPEC)

    assert ran.status == 0, said(ran)
    assert [call for call in runner.started("gh") if "merge" in call] == []
    assert [call[2] for call in pull_request_calls(runner)] == ["ready"]


def test_in_spec_mode_a_pull_request_that_would_not_be_marked_ready_stops_and_names_the_command(
        spec_mode):
    tracker = given_a_run_that_lands(spec_mode)
    tracker.ready = Ran(1, "", "no pull requests found for branch \"{}\"\n".format(SPEC_BRANCH))

    ran = spec_mode.run(SPEC)

    assert ran.status == 1
    assert "gh pr ready {}".format(SPEC_BRANCH) in said(ran)
    assert "no pull requests found" in said(ran)


def test_in_spec_mode_a_spec_that_names_no_branch_stops_before_a_ticket_is_claimed(
        spec_mode, runner):
    tracker = given_the_tracker_holds(spec_mode, ONE_OPEN_TICKET)
    tracker.body = COUNTED

    ran = spec_mode.run(SPEC)

    assert ran.status == 1
    assert "names no branch under ## Branch" in spec_mode.log()
    assert not runner.built("issue edit")


def test_in_spec_mode_the_stop_for_a_spec_that_names_no_branch_says_the_grill_writes_it(spec_mode):
    tracker = given_the_tracker_holds(spec_mode, ONE_OPEN_TICKET)
    tracker.body = COUNTED

    spec_mode.run(SPEC)

    assert "/skillworks:grill writes it" in spec_mode.log()


def test_with_a_branch_name_the_driver_touches_no_pull_request(loop, runner):
    given_a_run_that_lands(loop)

    ran = loop.run(SPEC)

    assert ran.status == 0, said(ran)
    assert call_asking(runner, "/skillworks:spec-drift") is not None
    assert pull_request_calls(runner) == []
    assert "READY" not in loop.log()


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
    STEPS_PAGE,
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


def test_the_step_list_is_marked_in_the_user_docs_on_the_steps_page_alone():
    marking = [page.relative_to(ROOT).as_posix()
               for page in sorted((ROOT / "docs" / "usage").rglob("*.md"))
               if STEP_MARK in page.read_text(encoding="utf-8")]

    assert marking == [STEPS_PAGE]


# --- the stage map held to the step list ---------------------------------------

MAP_MARK = "<!-- stage map -->"

SEEDS = ROOT / "plugins" / "skillworks" / "skills" / "skillworks-setup" / "seeds"


# A step is named in backticks in the first cell of its row, so a word in the prose never counts.
def stages_in_the_map(text):
    lines = [line.strip() for line in text.splitlines()]
    marked = [at for at, line in enumerate(lines) if line == MAP_MARK]
    assert len(marked) == 1, "expected one stage map, found {}".format(len(marked))
    rows = []
    for line in lines[marked[0] + 1:]:
        if not line.startswith("|"):
            break
        rows.append(line)
    first_cells = [row.split("|")[1] for row in rows[2:]]
    return {name for cell in first_cells for name in re.findall(r"`([^`]+)`", cell)}


def steps_missing_from(text):
    named = stages_in_the_map(text)
    return [step.name for step in spec_loop.STEPS if step.name not in named]


def given_a_map_naming(names):
    rows = "".join("| `{}` | a | b | c |\n".format(name) for name in names)
    return "Prose.\n\n{}\n| Stage | Always | On demand | Change |\n|---|---|---|---|\n{}\nMore.\n".format(
        MAP_MARK, rows)


def test_the_stage_map_is_marked_in_the_user_docs_on_the_stage_map_page_alone():
    marking = [page.relative_to(ROOT).as_posix()
               for page in sorted((ROOT / "docs" / "usage").rglob("*.md"))
               if MAP_MARK in page.read_text(encoding="utf-8")]

    assert marking == [STAGE_MAP_PAGE]


def test_the_stage_map_names_every_step_the_loop_runs():
    held = (ROOT / STAGE_MAP_PAGE).read_text(encoding="utf-8")

    assert steps_missing_from(held) == []


def test_a_map_that_missed_a_step_added_to_the_driver_is_caught():
    short = given_a_map_naming(step.name for step in spec_loop.STEPS[:-1])

    assert steps_missing_from(short) == [spec_loop.STEPS[-1].name]


def test_a_step_named_only_outside_the_first_cell_is_not_counted():
    elsewhere = given_a_map_naming(step.name for step in spec_loop.STEPS[:-1]).replace(
        "| c |", "| `{}` |".format(spec_loop.STEPS[-1].name), 1)

    assert steps_missing_from(elsewhere) == [spec_loop.STEPS[-1].name]


# The map describes Machinery, so a copy seeded into a team's repo would go stale there.
def test_no_seed_holds_a_stage_map():
    seeds = list(SEEDS.iterdir())
    holding = [seed.name for seed in seeds if MAP_MARK in seed.read_text(encoding="utf-8")]

    assert seeds != []
    assert holding == []


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
