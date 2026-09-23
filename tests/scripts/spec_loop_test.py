#
# The spec loop's plan and its steps, read against a throwaway repository.

import io
import json
from pathlib import Path

import pytest

import spec_loop
import ticket_worktree
from conftest import ROOT, Ran, git

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
    return Driver(repo, runner)


# A reason on stderr and what the loop said on stdout are one report, and a case reads it whole.
def said(ran):
    return ran.out + ran.err


class Tracker:
    # Every answer the loop asks for and no others, so an unplanned call fails rather than guesses.
    def __init__(self, runner, tickets):
        self.runner = runner
        self.tickets = tickets
        runner.stub("gh", does=self.answer)

    def numbers(self, only_open=False):
        return "".join(row[0] + "\n" for row in self.tickets
                       if not only_open or row[1] == "open")

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
            return Ran(0, "open\n", "")
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
        self.folder = repo.root / "claude" / "projects" / "one"
        self.folder.mkdir(parents=True, exist_ok=True)
        runner.stub("claude", does=self.answer)

    def answer(self):
        asked = next(arg for arg in self.runner.calls[-1] if arg.startswith("/"))
        command = asked.split(" ")[0]
        args = asked[len(command):]
        args = args[1:] if args.startswith(" ") else args
        step = command[1:]

        if step in self.refuses:
            return Ran(1, "", "the {} session was turned down\n".format(step))
        if step in self.removes:
            Path(self.removes[step]).unlink(missing_ok=True)
        if step in self.writes:
            name, text = self.writes[step]
            (Path(self.runner.where) / name).write_text(text, encoding="utf-8", newline="\n")
        if step in self.stages:
            git(self.runner.where, "add", "-N", ".")

        self.count += 1
        session = "session-{}".format(self.count)
        self.record(session, command, args)

        # The step that builds leaves the worktree changed, which is what its check reads.
        if asked.endswith("--stop-after-tests"):
            (Path(self.runner.where) / "built.txt").write_text(
                "built\n", encoding="utf-8", newline="\n")

        return Ran(0, json.dumps({
            "is_error": False,
            "session_id": session,
            "result": self.says.get(step, AXIS_REPORTS.get(step, "did the " + step)),
        }) + "\n", "")

    def record(self, session, command, args):
        entry = {"type": "user", "message": {"content":
                 "<command-name>{}</command-name><command-args>{}</command-args>".format(
                     command, args)}}
        (self.folder / (session + ".jsonl")).write_text(
            json.dumps(entry) + "\n", encoding="utf-8", newline="\n")


# A worktree is cut from the remote, so the marker the suite looks for has to reach it first.
def given_a_suite_that_passes(loop):
    loop.repo.write_commit(loop.repo.work, "Skillworks.slnx", "<Solution />", "A solution")
    git(loop.repo.work, "push", "--quiet", "origin", "main")
    loop.runner.stub("docker")
    loop.runner.stub("dotnet", says="the solution passed")


# The driver runs the suite itself, so a case about the steps needs one it can run.
def given_sessions_that_report(loop):
    given_a_suite_that_passes(loop)
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

def session_calls(runner):
    return [call for call in runner.calls if call[0] == "claude"]


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
            if call[2].startswith("/implement 168 ")]


# --- reading the plan -------------------------------------------------------

# The plan indents every line it gives a step, and these two name where a ticket is built.
WHERE_IT_IS_BUILT = ("worktree", "branch")


def indented(ran):
    return [line for line in ran.out.split("\n") if line.startswith("      ") and line.strip()]


# The driver's steps print before the landing's, so a name both lists hold reads as the driver's.
def plan_calls(ran):
    return [line.strip() for line in indented(ran)
            if not line.strip().startswith("checks: ")
            and line.split()[0] not in WHERE_IT_IS_BUILT]


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
        "git push origin HEAD:main",
        "checks: pushed (up to 3 attempts)",
    ):
        assert line in said(ran)


def test_the_dry_run_still_prints_the_sessions_it_would_start(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    for line in (
        "/implement 168 --stop-after-tests",
        "/implement 168 --fix",
        "/comment-sweep",
        "/implement 168 --finish",
        "checks: no-error command-loaded ticket-open tree-changed",
        "checks: no-error command-loaded new-commit tree-clean ticket-closed",
    ):
        assert line in said(ran)


def test_the_dry_run_prints_all_eight_steps_in_order(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    for line in ("/review-standards 168", "/review-spec 168", "/review-architecture 168"):
        assert line in said(ran)
    assert planned_steps(ran)[:8] == [
        "build", "standards", "spec", "architecture", "fix", "sweep", "suite", "finish"]


def test_the_dry_run_gives_the_suite_step_no_session(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    ran = loop.run(SPEC, "--dry-run")

    assert ran.status == 0
    planned = planned_call(ran, "suite")
    assert "as the README names it" in planned
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
        ["open", loop.repo.work.as_posix(), SPEC, job], loop.runner, out, err) == 0


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
    for asked in ("/review-standards 168", "/review-spec 168", "/review-architecture 168",
                  "/comment-sweep"):
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
    assert call_asking(runner, "/review-spec") is None


def test_a_review_step_that_reported_no_findings_passes_its_check(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.says["review-standards"] = "## Standards. No findings on this change."

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert call_asking(runner, "/review-spec 168") is not None
    assert "step standards failed" not in said(ran)


def test_a_review_step_that_errored_stops_the_loop_and_keeps_the_worktree(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.refuses.add("review-spec")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step spec exited non-zero" in said(ran)
    assert ticket_worktree_of(loop).as_posix() in said(ran)
    assert ticket_worktree_of(loop).is_dir()
    assert call_asking(runner, "/implement 168 --fix") is None
    assert call_asking(runner, "/implement 168 --finish") is None


# --- the reports reaching the fix step --------------------------------------

def test_the_fix_step_is_given_what_all_three_axes_found(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_three_axes_with_something_to_say(given_sessions_that_report(loop))

    ran = loop.run(SPEC)

    assert ran.status == 1
    asked = prompt_asking(runner, "/implement 168 --fix")
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
            runner, "/implement 168 --fix")


# The reports stop at `fix`, which reconciles, so carrying them on would be the same work twice.
def test_the_finishing_step_is_given_no_axis_report(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_three_axes_with_something_to_say(given_sessions_that_report(loop))

    ran = loop.run(SPEC)

    assert ran.status == 1
    asked = prompt_asking(runner, "/implement 168 --finish")
    assert asked != ""
    assert "axis reported" not in asked


def test_the_fix_step_and_the_finishing_step_both_resume_the_build_session(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    for mark in ("/implement 168 --fix", "/implement 168 --finish"):
        call = call_asking(runner, mark)
        assert call[call.index("--resume") + 1] == "session-1"


def test_a_missing_axis_report_stops_the_loop_before_the_fix_step(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    given_a_report_lost_after_the_last_axis(loop, sessions, "standards")

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step fix was short of a review axis report" in said(ran)
    assert call_asking(runner, "/implement 168 --fix") is None


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
    assert call_asking(runner, "/review-spec 168") is not None


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
    asked = prompt_asking(runner, "/implement 168 --fix")
    assert "The standards axis changed named.txt." in asked
    assert "The spec axis changed nothing." in asked
    assert "The architecture axis changed built.txt." in asked


def test_an_axis_that_edits_does_not_stop_the_loop(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_writes(
        given_sessions_that_report(loop), "standards", "named.txt", "the name box\n")

    ran = loop.run(SPEC)

    assert "step standards failed" not in said(ran)
    assert call_asking(runner, "/review-spec 168") is not None
    assert call_asking(runner, "/implement 168 --fix") is not None


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
    assert len(session_calls(runner)) == 7


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
    assert call_at(runner, "/comment-sweep") < call_at(runner, SOLUTION)
    assert call_at(runner, SOLUTION) < call_at(runner, "/implement 168 --finish")


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
    assert call_asking(runner, "/implement 168 --finish") is None


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

# The second run falls through to the passing stub, so one case holds a flake and nothing else.
def given_a_suite_red_on_its_first_run_alone(runner):
    runner.refuse(SOLUTION, "a Span test failed", times=1)


def given_a_suite_red_on_every_run(runner):
    runner.stub("dotnet", says="a test failed", status=1)


def test_a_red_suite_is_run_a_second_time_before_it_is_believed(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert len(runner.started("dotnet")) == 2


def test_a_green_first_run_is_never_run_again(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert len(runner.started("dotnet")) == 1


def test_a_second_run_that_passes_carries_the_loop_on_to_the_finishing_step(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert call_asking(runner, "/implement 168 --finish") is not None
    assert "failed check suite-green" not in said(ran)


def test_the_log_names_which_of_the_two_runs_each_one_is(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "suite run 1 went red" in loop.log()
    assert "suite run 2 went red" in loop.log()


def test_the_log_names_the_one_run_a_green_suite_took(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "suite run 1 passed" in loop.log()
    assert "suite run 2" not in loop.log()


def test_a_second_run_that_passes_says_the_first_was_a_flake(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "suite run 2 passed, so the first was a flake" in loop.log()


def test_both_runs_are_kept_where_the_other_step_records_are(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "a Span test failed" in suite_output(loop)
    assert "the solution passed" in suite_output(loop)


# A second run cannot start Docker either, so nothing is spent proving that twice.
def test_a_machine_short_of_what_the_suite_needs_is_never_run_again(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
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
    given_sessions_that_report(loop)
    given_a_suite_red_until_the_loop_goes_round(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    went_round = every_call_at(runner, "/implement 168 --fix")[1]
    swept = every_call_at(runner, "/comment-sweep")[1]
    assert went_round < swept < every_call_at(runner, SOLUTION)[2]


def test_the_failure_output_reaches_the_fix_prompt(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "a test failed" in prompts_asking(runner, "/implement 168 --fix")[1]


def test_the_fix_step_before_the_suite_is_told_of_no_failure(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "a test failed" not in prompts_asking(runner, "/implement 168 --fix")[0]


def test_the_retry_runs_under_the_fix_flag_and_no_other(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_until_the_loop_goes_round(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert implement_flags(runner) == [
        "--stop-after-tests", "--fix", "--fix", "--finish"]


def test_a_suite_green_after_the_circuit_carries_the_loop_on(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_until_the_loop_goes_round(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert call_asking(runner, "/implement 168 --finish") is not None
    assert "failed check suite-green" not in said(ran)


def test_a_second_circuit_never_happens(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert len(prompts_asking(runner, "/implement 168 --fix")) == 2
    assert len(prompts_asking(runner, "/comment-sweep")) == 2
    assert len(runner.started("dotnet")) == 4


def test_red_after_the_circuit_stops_the_loop_before_the_finishing_step(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "step suite failed check suite-green" in said(ran)
    assert call_asking(runner, "/implement 168 --finish") is None


def test_a_stop_after_the_circuit_leaves_the_worktree_and_names_it_in_the_log(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert ticket_worktree_of(loop).is_dir()
    assert ticket_worktree_of(loop).as_posix() in loop.log()


def test_the_log_says_the_loop_went_round_and_where_it_went(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_on_every_run(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "goes round once: fix, then sweep, then suite" in loop.log()


def test_the_record_keeps_what_the_suite_said_on_both_sides_of_the_circuit(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_until_the_loop_goes_round(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert suite_output(loop).count("the runs before the circuit failed") == 2
    assert "the solution passed" in suite_output(loop)


# --- the passing suite reaching the finishing step ---------------------------

def finish_prompt(runner):
    return prompt_asking(runner, "/implement 168 --finish")


def test_the_finishing_step_is_handed_the_output_of_the_suite_that_passed(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "the solution passed" in finish_prompt(runner)


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
    assert call_at(runner, SOLUTION) < call_at(runner, "/implement 168 --finish")


# A flake spends a run, and the run that proved the work is the one the closing comment names.
def test_the_finishing_step_is_handed_the_run_that_passed_and_not_the_one_that_failed(loop, runner):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)
    given_a_suite_red_on_its_first_run_alone(runner)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "the solution passed" in finish_prompt(runner)
    assert "a Span test failed" not in finish_prompt(runner)


# --- the way past a refused write -------------------------------------------

# A session that met the wall leaves the ticket open, so any stop the loop makes may be that wall.
def test_a_ticket_left_open_is_told_the_way_past_the_wall(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "SPEC_LOOP_PERMISSION_MODE=bypassPermissions" in said(ran)
    assert ticket_worktree_of(loop).as_posix() in said(ran)


def test_the_way_past_the_wall_reaches_the_log_as_well(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop)

    ran = loop.run(SPEC)

    assert ran.status == 1
    assert "SPEC_LOOP_PERMISSION_MODE=bypassPermissions" in loop.log()


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
    asked = [call[2].split(" ")[0] for call in session_calls(runner)]
    assert asked == ["/implement", "/review-standards", "/review-spec", "/review-architecture",
                     "/implement", "/comment-sweep", "/implement"]
    for changes in changes_given_to_sessions(runner):
        assert changes.get("OTEL_RESOURCE_ATTRIBUTES") == PARENT


def test_the_drift_session_names_the_session_that_started_the_driver(loop, runner, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "parent-session")
    given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    given_sessions_that_report(loop)

    loop.run(SPEC)

    assert call_asking(runner, "/spec-drift") is not None
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
    ".claude/skills/what-next/SKILL.md",
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
