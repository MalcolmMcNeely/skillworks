# Driven through the loop and the Tracker's commands, so each case checks what the Sidecar and origin hold.

import contextlib
import io
import json
import re
import threading
from pathlib import Path

import pytest

import spec_loop
from clock.held_clock import HeldClock
from conftest import Ran, RecordingRunner, Repo, git, write_steering
from runner import Subprocess
from sidecar.locator import sidecar_of
from sidecar.sidecar import Sidecar
from spec_loop_test import Sessions, given_a_suite_that_passes
from steering.target_branch import LOOP_FILE
from stop import REFUSED, Stop
from tracker import close, publish
from tracker.files import Files

SPEC = "7"
FOLDER = ".specs/0007-local-tracker"
SPEC_BRANCH = "spec/local-tracker"

RIVAL = "rival@example.invalid"


def next_is(ticket):
    return "DRY   the next ticket is {}/{}\n".format(SPEC, ticket)


COUNTED = ("## User Stories\n\n1. As a team member, I want a local tracker.\n\n"
           "## Implementation Decisions\n\n1. The tracker is files.\n\n## Surfaces\n\nNone\n")


def spec_file(status="open", branch=None, body=COUNTED):
    lines = ["---", "status: " + status]
    if branch is not None:
        lines.append("branch: " + branch)
    return "\n".join(lines + ["---", "", "# SPEC: A local tracker", "", body])


def ticket_file(title, status="open", blocked_by=(), more=()):
    return "\n".join([
        "---",
        "status: " + status,
        "blocked-by: [{}]".format(", ".join(str(number) for number in blocked_by)),
        *more,
        "---",
        "",
        "# " + title,
        "",
    ])


def ticket_path(name):
    return "{}/tickets/{}.md".format(FOLDER, name)


def write_loop(top, target):
    path = Path(top) / LOOP_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tracker": "files", "target-branch": target}, indent=2),
                    encoding="utf-8", newline="\n")


def write_files(where, files):
    for name, text in files.items():
        path = Path(where) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def commit_files(where, files, message):
    write_files(where, files)
    git(where, "add", "-A")
    git(where, "commit", "--quiet", "-m", message)


# Every ref and the commit it names, so a case sees any push or new branch at all.
def refs_of(repo):
    return git(repo.origin, "for-each-ref", "--format=%(refname) %(objectname)")


def run_loop(runner, checkout, *flags, spec=SPEC):
    if "claude" not in runner.stubs:
        runner.stub("claude")
    write_steering(checkout)
    out, err = io.StringIO(), io.StringIO()
    with contextlib.chdir(checkout):
        status = spec_loop.main([spec, *flags], runner, out, err, lambda seconds: None,
                                HeldClock())
    return Ran(status, out.getvalue(), err.getvalue())


class Driver:
    def __init__(self, repo, runner):
        self.repo = repo
        self.runner = runner
        self.sidecar = sidecar_of(Subprocess(), repo.work)

    def dry_run(self):
        return run_loop(self.runner, self.repo.work, "--dry-run")

    def run(self, spec=SPEC):
        return run_loop(self.runner, self.repo.work, spec=spec)

    # The first loop's Session holds until the case lets it go, so the loop is running while the case acts.
    @contextlib.contextmanager
    def running(self, spec=SPEC):
        holding, release = threading.Event(), threading.Event()
        runner = RecordingRunner()

        def session():
            holding.set()
            release.wait()
        runner.stub("claude", does=session)
        first = threading.Thread(target=run_loop, args=(runner, self.repo.work), kwargs={"spec": spec})
        first.start()
        try:
            assert holding.wait(120), "the first loop never reached a Session"
            yield
        finally:
            release.set()
            first.join()

    # Written as the Tracker writes, one commit under the lock, so the loop reads it as it would its own.
    def put(self, files):
        Sidecar.of(Subprocess(), self.repo.work, HeldClock()).write(
            "Tracker state", lambda folder: write_files(folder, files))

    def held(self, path):
        return (self.sidecar / path).read_text(encoding="utf-8")

    def field(self, path, name):
        return next(line[len(name) + 1:].strip() for line in self.held(path).split("\n")
                    if line.startswith(name + ":"))

    def status_of(self, path):
        return self.field(path, "status")


@pytest.fixture
def driver(tmp_path, monkeypatch):
    repo = Repo(tmp_path)
    monkeypatch.chdir(repo.work)
    monkeypatch.delenv("SPEC_LOOP_PERMISSION_MODE", raising=False)
    # A session is looked for under this case's own folder, so no real one can answer a check here.
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", (tmp_path / "claude").as_posix())
    write_loop(repo.work, "main")
    return Driver(repo, RecordingRunner())


def said(ran):
    return ran.out + ran.err


def test_the_dry_run_names_the_first_ticket_whose_blockers_are_all_closed(driver):
    driver.put({
        FOLDER + "/spec.md": spec_file(),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json", status="closed"),
        ticket_path("02-close-in-worktree"): ticket_file("Close in the worktree", blocked_by=[1]),
        ticket_path("03-claim"): ticket_file("Claim", blocked_by=[2]),
    })

    ran = driver.dry_run()

    assert ran.status == 0, said(ran)
    assert next_is(2) in ran.out
    assert "7/1 [closed] Read loop.json" in ran.out
    assert "7/2 [open] Close in the worktree" in ran.out


def test_a_ticket_whose_blocker_is_open_is_not_picked_until_the_sidecar_closes_it(driver):
    blocker = ticket_path("01-read-loop-json")
    driver.put({
        FOLDER + "/spec.md": spec_file(),
        blocker: ticket_file("Read loop.json"),
        ticket_path("02-close-in-worktree"): ticket_file("Close in the worktree", blocked_by=[1]),
    })

    blocked = driver.dry_run()
    driver.put({blocker: ticket_file("Read loop.json", status="closed")})
    unblocked = driver.dry_run()

    assert next_is(1) in blocked.out, said(blocked)
    assert next_is(2) in unblocked.out, said(unblocked)


def test_a_spec_folder_committed_in_the_repo_is_not_read(driver):
    commit_files(driver.repo.work, {
        FOLDER + "/spec.md": spec_file(),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    }, "Written in the repo")
    git(driver.repo.work, "push", "--quiet", "origin", "main")

    ran = driver.dry_run()

    assert ran.status == 1
    assert "cannot read spec 7" in said(ran)


def test_a_spec_the_sidecar_does_not_hold_stops_the_loop_naming_the_sidecar(driver):
    ran = driver.dry_run()

    assert "ABORT cannot read spec 7 from {}".format(driver.sidecar.as_posix()) in said(ran)


def test_in_pr_mode_the_dry_run_reads_the_tickets_from_the_sidecar(driver):
    write_loop(driver.repo.work, "pr")
    driver.put({
        FOLDER + "/spec.md": spec_file(branch=SPEC_BRANCH),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json", status="closed"),
        ticket_path("02-close-in-worktree"): ticket_file("Close in the worktree", blocked_by=[1]),
    })

    ran = driver.dry_run()

    assert ran.status == 0, said(ran)
    assert next_is(2) in ran.out


def two_free_tickets():
    return {
        FOLDER + "/spec.md": spec_file(),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
        ticket_path("02-close-in-worktree"): ticket_file("Close in the worktree"),
    }


def test_a_run_writes_nothing_to_the_ticket_it_starts_and_pushes_nothing(driver):
    driver.put(two_free_tickets())
    before = refs_of(driver.repo)

    ran = driver.run()

    assert "START 7/1" in ran.out, said(ran)
    assert (driver.held(ticket_path("01-read-loop-json")), refs_of(driver.repo)) == (
        ticket_file("Read loop.json"), before)


def test_a_ticket_file_that_still_names_a_claim_is_picked_as_any_other(driver):
    driver.put(two_free_tickets())
    driver.put({ticket_path("01-read-loop-json"): ticket_file(
        "Read loop.json", more=["claimed-by: " + RIVAL])})

    ran = driver.run()

    assert "START 7/1" in ran.out, said(ran)


def test_git_with_no_user_email_does_not_stop_the_loop(driver, tmp_path, monkeypatch):
    empty = tmp_path / "no-identity.gitconfig"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", empty.as_posix())
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    git(driver.repo.work, "config", "--unset", "user.email")
    git(driver.repo.work, "config", "--unset", "user.name")
    driver.put(two_free_tickets())

    ran = driver.run()

    assert "START 7/1" in ran.out, said(ran)


# --- one loop to a spec on this machine --------------------------------------

def test_a_second_loop_on_a_spec_with_a_loop_running_stops_before_it_builds_and_names_the_log(driver):
    driver.put(two_free_tickets())

    with driver.running():
        ran = driver.run()

    assert (ran.status, "START" in ran.out) == (1, False), said(ran)
    assert "spec 7 already has a loop running on this machine" in said(ran)
    assert ".spec-loop/7/loop.log" in said(ran)


def test_a_second_loop_on_a_spec_from_another_worktree_of_the_clone_stops_and_names_the_first_log(
        driver, tmp_path):
    driver.put(two_free_tickets())
    other = tmp_path / "other"
    git(driver.repo.work, "worktree", "add", "--quiet", "--detach", other.as_posix())
    write_loop(other, "main")
    first_log = (driver.repo.work / ".spec-loop" / SPEC / "loop.log").as_posix()

    with driver.running():
        ran = run_loop(RecordingRunner(), other)

    assert (ran.status, "START" in ran.out) == (1, False), said(ran)
    assert first_log in said(ran)


def test_a_loop_on_a_spec_whose_earlier_loop_has_ended_starts(driver):
    driver.put(two_free_tickets())
    driver.run()

    ran = driver.run()

    assert "START 7/1" in ran.out, said(ran)


def test_two_loops_on_two_specs_start_side_by_side(driver):
    driver.put(two_free_tickets())
    driver.put({
        ".specs/0008-another/spec.md": spec_file(),
        ".specs/0008-another/tickets/01-another.md": ticket_file("Another"),
    })

    with driver.running():
        ran = driver.run(spec="8")

    assert "START 8/1" in ran.out, said(ran)


def test_in_pr_mode_a_spec_that_names_no_branch_stops_before_a_ticket_and_says_the_grill_writes_it(
        driver):
    write_loop(driver.repo.work, "pr")
    driver.put({
        FOLDER + "/spec.md": spec_file(),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    })

    ran = driver.run()

    assert (ran.status, "START" in ran.out) == (1, False)
    assert "branch in its spec.md frontmatter" in said(ran)
    assert "/skillworks:grill writes it" in said(ran)


# --- a close, in the Sidecar before the Land ---------------------------------

REFERENCE = "7/1"
FINISH = "implement {} --finish".format(REFERENCE)
NOTE = "Built the reader. Proved by the reader tests."
CODE = "reader.txt"


# What /skillworks:implement does at Finishing: commit, then close through tracker-close.
def finishing(runner, trailer=REFERENCE, closes=True, ticket=REFERENCE, code=CODE):
    def finish():
        tree = Path(runner.where)
        (tree / code).write_text("read\n", encoding="utf-8", newline="\n")
        git(tree, "add", "-A")
        git(tree, "commit", "--quiet", "-m", "Built the reader\n\nTicket: " + trailer)
        if closes:
            closed_by_command(tree, ticket)
    return finish


def closed_by_command(tree, ticket, note=NOTE):
    # Beside the worktree, so the note leaves its tree clean as an ignored file does.
    held = Path(tree).parent / "closing-note.md"
    held.write_text(note + "\n", encoding="utf-8", newline="\n")
    out, err = io.StringIO(), io.StringIO()
    status = close.main([ticket, held.as_posix()], RecordingRunner(), out, err, Path(tree).as_posix())
    return Ran(status, out.getvalue(), err.getvalue())


def given_sessions_that_finish(driver, runs=None, **finish):
    given_a_suite_that_passes(driver, runs)
    sessions = Sessions(driver.repo, driver.runner)
    sessions.then[FINISH] = finishing(driver.runner, **finish)
    sessions.then["spec-drift"] = drifting(driver)
    sessions.then["spec-names"] = naming(driver)
    driver.put({
        FOLDER + "/spec.md": spec_file(),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    })
    return sessions


def asked_of_claude(driver):
    return [call[-1] for call in driver.runner.started("claude")]


def test_a_landed_ticket_is_closed_in_the_sidecar_with_its_closing_note(driver):
    given_sessions_that_finish(driver)

    ran = driver.run()

    assert "DONE  7/1" in ran.out, said(ran)
    assert driver.status_of(ticket_path("01-read-loop-json")) == "closed"
    assert "## Closing note\n\n" + NOTE in driver.held(ticket_path("01-read-loop-json"))


def test_a_whole_run_pushes_nothing_of_the_tracker_to_origin(driver):
    given_sessions_that_finish(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    assert git(driver.repo.origin, "log", "--format=%H", "main", "--", ".specs") == ""
    assert sorted(git(driver.repo.origin, "for-each-ref", "--format=%(refname)").split()) == [
        "refs/heads/main"]
    assert CODE in git(driver.repo.origin, "ls-tree", "--name-only", "main").split()


def test_each_session_is_handed_the_ticket_by_its_spec_and_its_number(driver):
    given_sessions_that_finish(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    commands = [prompt.split("\n", 1)[0] for prompt in asked_of_claude(driver)]
    assert "/skillworks:implement 7/1 --stop-after-tests" in commands
    assert "/skillworks:review-spec 7/1" in commands
    assert "/skillworks:implement 7/1 --finish" in commands


def test_the_landed_commit_names_the_spec_and_the_ticket_in_its_trailer(driver):
    given_sessions_that_finish(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    trailer = git(driver.repo.origin, "log", "-1", "--grep=Built the reader",
                  "--format=%(trailers:key=Ticket,valueonly)", "main")
    assert trailer.strip() == REFERENCE


def test_a_commit_naming_the_ticket_alone_is_not_landed_and_the_ticket_is_open_again(driver):
    given_sessions_that_finish(driver, trailer="#1")

    ran = driver.run()

    assert ran.status == 1
    assert "step finish failed check ticket-trailer" in said(ran)
    assert driver.status_of(ticket_path("01-read-loop-json")) == "open"


def test_a_ticket_whose_land_fails_is_open_again_in_the_sidecar(driver):
    given_sessions_that_finish(driver)
    driver.runner.refuse("HEAD:main", "remote: the push was turned down")

    ran = driver.run()

    assert ran.status == 1
    assert "did not reach main" in said(ran)
    assert "7/1 is open again" in ran.out
    assert driver.status_of(ticket_path("01-read-loop-json")) == "open"
    assert CODE not in git(driver.repo.origin, "ls-tree", "--name-only", "main").split()


def test_a_finish_that_left_its_ticket_open_is_nudged_to_close_it_with_tracker_close(driver):
    given_sessions_that_finish(driver, closes=False)

    ran = driver.run()

    assert ran.status == 1
    nudges = [prompt for prompt in asked_of_claude(driver) if not prompt.startswith("/")]
    assert nudges, said(ran)
    assert "tracker-close 7/1" in nudges[0]
    assert driver.status_of(ticket_path("01-read-loop-json")) == "open"


def test_after_the_last_ticket_and_the_drift_check_the_spec_is_closed_in_the_sidecar(driver):
    given_sessions_that_finish(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    assert driver.status_of(FOLDER + "/spec.md") == "closed"
    assert (ran.out.index("DRIFT") < ran.out.index("FULL  main at")
            < ran.out.index("CLOSE spec 7 is closed in the Sidecar") < ran.out.index("END   spec 7"))


def test_a_red_full_run_after_every_verdict_done_leaves_the_spec_open(driver):
    given_sessions_that_finish(driver)
    full_run = driver.repo.tree(SPEC, "full-run").as_posix()

    def red_in_the_full_run():
        if driver.runner.where == full_run:
            return Ran(1, "a test failed on this OS\n", "")
        return None
    driver.runner.stub("dotnet", says="the solution passed", does=red_in_the_full_run)

    ran = driver.run()

    assert ran.status == 1
    assert "RED   the full run of the Suite went red" in ran.out
    assert "CLOSE" not in ran.out
    assert driver.status_of(FOLDER + "/spec.md") == "open"


# The loop runs from the default branch, and only the spec's branch is Landed on.
def given_sessions_that_finish_on_the_spec_branch(driver):
    write_loop(driver.repo.work, "pr")
    driver.put({
        FOLDER + "/spec.md": spec_file(branch=SPEC_BRANCH),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    })
    given_a_suite_that_passes(driver)
    git(driver.repo.work, "push", "--quiet", "origin", "main:" + SPEC_BRANCH)
    sessions = Sessions(driver.repo, driver.runner)
    sessions.then[FINISH] = finishing(driver.runner)
    sessions.then["spec-drift"] = drifting(driver)
    sessions.then["spec-names"] = naming(driver)
    return sessions


def test_in_pr_mode_the_ticket_lands_on_the_branch_the_spec_names(driver):
    given_sessions_that_finish_on_the_spec_branch(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    assert CODE in git(driver.repo.origin, "ls-tree", "--name-only", SPEC_BRANCH).split()
    assert CODE not in git(driver.repo.origin, "ls-tree", "--name-only", "main").split()


def test_in_pr_mode_the_run_closes_the_spec_in_the_sidecar_and_never_calls_gh(driver):
    given_sessions_that_finish_on_the_spec_branch(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    assert driver.runner.started("gh") == []
    assert driver.status_of(FOLDER + "/spec.md") == "closed"
    assert "CLOSE spec 7" in ran.out


def test_in_pr_mode_the_last_lines_ask_for_the_pull_request_from_the_spec_branch(driver):
    given_sessions_that_finish_on_the_spec_branch(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    last = "\n".join(ran.out.rstrip("\n").split("\n")[-3:])
    assert "PR    open the pull request from {}. A person reviews and merges it.".format(
        SPEC_BRANCH) in last
    assert "Closes #" not in ran.out


# The Seed's Surfaces hold the README, so the drift check judges it on every spec.
VERDICTS = "### Verdicts\n\n- S1: Done\n- D1: Done\n- The README: In step\n"

REPORT = "## Drift report\n\n" + VERDICTS


def recording(driver, command, report):
    def record():
        held = driver.repo.root / (command + "-report.md")
        held.write_text(report, encoding="utf-8", newline="\n")
        publish.main([command, SPEC, held.as_posix()], RecordingRunner(), io.StringIO(),
                     io.StringIO(), HeldClock(), driver.repo.work.as_posix())
    return record


def drifting(driver, report=REPORT):
    return recording(driver, "drift", report)


RENAMES = "### Renames\n\n- None\n"

NAMES = "## Name report\n\n" + RENAMES


def naming(driver, report=NAMES):
    return recording(driver, "names", report)


def test_the_loop_reads_back_the_drift_report_recorded_with_the_spec(driver):
    given_sessions_that_finish(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    assert REPORT + "\n" + NAMES in driver.held(FOLDER + "/spec.md")
    held = driver.repo.work / ".spec-loop" / SPEC / "drift.md"
    assert held.read_text(encoding="utf-8") == VERDICTS
    assert "DRIFT the report is recorded on spec 7" in ran.out
    assert "COUNT the spec holds 3 items, and the drift report gives 3 Verdicts" in ran.out


def test_the_loop_reads_back_the_name_report_recorded_below_the_drift_report(driver):
    given_sessions_that_finish(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    assert driver.held(FOLDER + "/spec.md").endswith(NAMES)
    held = driver.repo.work / ".spec-loop" / SPEC / "names.md"
    assert held.read_text(encoding="utf-8") == RENAMES
    assert "NAMES no rename is owed on spec 7" in ran.out


def test_a_name_check_that_recorded_no_report_stops_and_leaves_the_spec_open(driver):
    sessions = given_sessions_that_finish(driver)
    del sessions.then["spec-names"]

    ran = driver.run()

    assert ran.status == 1
    assert "STOP  the Name check recorded no report on spec 7" in ran.out
    assert driver.status_of(FOLDER + "/spec.md") == "open"


def test_a_drift_check_that_recorded_no_report_stops_and_leaves_the_spec_open(driver):
    sessions = given_sessions_that_finish(driver)
    del sessions.then["spec-drift"]

    ran = driver.run()

    assert ran.status == 1
    assert "STOP  the drift check recorded no report on spec 7" in ran.out
    assert driver.status_of(FOLDER + "/spec.md") == "open"


def test_the_flakes_of_a_run_are_noted_in_the_spec_file_above_its_reports(driver):
    given_sessions_that_finish(driver, runs=2)
    driver.runner.refuse("dotnet test Skillworks.slnx", "a Span test failed", times=1)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    text = driver.held(FOLDER + "/spec.md")
    [kept] = sorted((driver.repo.work / ".spec-loop" / SPEC).glob("flake-ticket-1-suite-*.out"))
    note = text[text.index("## Flakes\n"):text.index(REPORT)]
    assert "- dotnet test Skillworks.slnx, in 7/1 suite: {}\n".format(kept.as_posix()) in note
    assert text.endswith(REPORT + "\n" + NAMES)
    assert driver.status_of(FOLDER + "/spec.md") == "closed"


def files_tracker(driver, target="main"):
    return Files(RecordingRunner(), driver.repo.work, target, SPEC, HeldClock())


def test_a_later_note_takes_the_place_of_an_earlier_one_and_leaves_the_reports(driver):
    driver.put({FOLDER + "/spec.md": spec_file(body=COUNTED + "\n" + REPORT + "\n" + NAMES)})
    tracker = files_tracker(driver)

    tracker.record_flakes(SPEC, "## Flakes\n\n- the first run's Flake\n")
    tracker.record_flakes(SPEC, "## Flakes\n\n- the second run's Flake\n")

    text = driver.held(FOLDER + "/spec.md")
    assert text.count("## Flakes") == 1
    assert "the first run's Flake" not in text
    assert text.index("the second run's Flake") < text.index(REPORT)
    assert tracker.drift_report(SPEC) == VERDICTS.strip("\n")
    assert tracker.name_report(SPEC) == RENAMES.strip("\n")


GAP_TICKET = "02-ticket-build-the-gaps-the-drift-check-found"

D1_MISSING = ("## Drift report\n\n### Verdicts\n\n- S1: Done\n- D1: Missing. Not there.\n"
              "- The README: In step\n")


# A file of its own, since the ticket landed before it already holds what every build writes.
def given_a_filed_ticket_that_lands(driver, sessions):
    def build():
        (Path(driver.runner.where) / "filed.txt").write_text("built\n", encoding="utf-8",
                                                             newline="\n")

    sessions.then["implement {}/2 --stop-after-tests".format(SPEC)] = build
    sessions.then["implement {}/2 --finish".format(SPEC)] = finishing(
        driver.runner, trailer=SPEC + "/2", ticket=SPEC + "/2", code="filed-done.txt")


def given_a_gap_round(driver, *reports):
    sessions = given_sessions_that_finish(driver)
    given_a_filed_ticket_that_lands(driver, sessions)
    waiting = list(reports)
    sessions.then["spec-drift"] = lambda: drifting(driver, waiting.pop(0))()
    return sessions


def test_a_gap_is_filed_as_a_ticket_file_in_the_sidecar_and_a_closed_round_closes_it(driver):
    given_a_gap_round(driver, D1_MISSING, "## Drift report\n\n### Verdicts\n\n- D1: Done\n")

    ran = driver.run()

    assert ran.status == 0, said(ran)
    assert "FILED {}/2 under spec {} builds 1 Gap".format(SPEC, SPEC) in ran.out
    filed = driver.held(ticket_path(GAP_TICKET))
    assert "### D1\n\n> The tracker is files.\n\nVerdict: Missing. Not there.\n" in filed
    assert driver.status_of(ticket_path(GAP_TICKET)) == "closed"
    assert driver.status_of(FOLDER + "/spec.md") == "closed"


def test_a_gap_left_after_the_round_leaves_the_spec_open(driver):
    given_a_gap_round(driver, D1_MISSING,
                      "## Drift report\n\n### Verdicts\n\n- D1: Missing. Not there.\n")

    ran = driver.run()

    assert ran.status == 1
    assert "      Gap: D1 is Missing: Not there.\n" in ran.out
    assert "CLOSE" not in ran.out
    assert driver.status_of(FOLDER + "/spec.md") == "open"


RENAME_TICKET = "02-ticket-make-the-renames-the-name-check-found"

BATCH_MOVED = "## Name report\n\n### Renames\n\n- `Batch`: it now holds a whole spec.\n"


def given_a_rename_round(driver, *reports):
    sessions = given_sessions_that_finish(driver)
    given_a_filed_ticket_that_lands(driver, sessions)
    waiting = list(reports)
    sessions.then["spec-names"] = lambda: naming(driver, waiting.pop(0))()
    return sessions


def test_a_rename_is_filed_as_a_ticket_file_in_the_sidecar_and_a_rename_made_closes_it(driver):
    given_a_rename_round(driver, BATCH_MOVED, "## Name report\n\n### Verdicts\n\n- Batch: Done\n")

    ran = driver.run()

    assert ran.status == 0, said(ran)
    assert "FILED {}/2 under spec {} makes 1 rename".format(SPEC, SPEC) in ran.out
    filed = driver.held(ticket_path(RENAME_TICKET))
    assert "### Batch\n\n> `Batch`: it now holds a whole spec.\n" in filed
    assert driver.status_of(ticket_path(RENAME_TICKET)) == "closed"
    assert "NAMES every rename is made on spec 7" in ran.out
    assert driver.status_of(FOLDER + "/spec.md") == "closed"


def test_a_rename_not_made_leaves_the_spec_open(driver):
    given_a_rename_round(driver, BATCH_MOVED,
                         "## Name report\n\n### Verdicts\n\n- Batch: Not done. Still there.\n")

    ran = driver.run()

    assert ran.status == 1
    assert "      Not made: Batch is Not done: Still there.\n" in ran.out
    assert "CLOSE" not in ran.out
    assert driver.status_of(FOLDER + "/spec.md") == "open"


def test_a_resolver_reads_how_a_landed_ticket_was_closed_from_its_closing_note(driver):
    given_sessions_that_finish(driver)
    ran = driver.run()

    read = files_tracker(driver).closing_note(REFERENCE)

    assert ran.status == 0, said(ran)
    assert read == NOTE


# --- filing a ticket under a spec --------------------------------------------

GAPS = "## What to build\n\nS2: Missing.\n"


def test_a_filed_ticket_is_written_next_in_number_and_open(driver):
    driver.put(two_free_tickets())

    number = files_tracker(driver).file_ticket(SPEC, "TICKET: Build the Gaps", GAPS)

    assert number == "3"
    assert driver.held(ticket_path("03-ticket-build-the-gaps")) == (
        "---\nstatus: open\nblocked-by: []\n---\n\n"
        "# TICKET: Build the Gaps\n\n" + GAPS)


def test_a_filed_ticket_is_listed_among_the_specs_open_tickets(driver):
    driver.put(two_free_tickets())
    tracker = files_tracker(driver)

    number = tracker.file_ticket(SPEC, "TICKET: Build the Gaps", GAPS)

    assert tracker.open_tickets(SPEC) == ["1", "2", number]
    assert tracker.title(number) == "TICKET: Build the Gaps"
    assert tracker.open_blockers(number) == 0


def test_a_ticket_filed_under_a_spec_with_no_folder_stops_and_says_so(driver):
    driver.put({"elsewhere.txt": "nothing about the spec\n"})

    with pytest.raises(Stop) as stopped:
        files_tracker(driver).file_ticket(SPEC, "TICKET: Build the Gaps", GAPS)

    assert stopped.value.status == REFUSED
    assert "holds no spec 7" in stopped.value.said


def test_filing_closing_and_reopening_leave_every_ref_on_origin_as_it_was(driver):
    driver.put(two_free_tickets())
    tracker = files_tracker(driver)
    before = refs_of(driver.repo)

    tracker.file_ticket(SPEC, "TICKET: Build the Gaps", GAPS)
    tracker.close("1", NOTE)
    tracker.reopen("1")
    tracker.record_flakes(SPEC, "## Flakes\n\n- one\n")
    tracker.close_spec(SPEC)

    assert refs_of(driver.repo) == before


def test_a_spec_whose_run_stopped_is_left_open(driver):
    given_sessions_that_finish(driver, closes=False)

    ran = driver.run()

    assert ran.status == 1
    assert driver.status_of(FOLDER + "/spec.md") == "open"


# --- the log, in the Tracker's words ------------------------------------------

GITHUB_WORDS = ("sub-issue", "issue_dependencies_summary")


def log_of(driver):
    return (driver.repo.work / ".spec-loop" / SPEC / "loop.log").read_text(encoding="utf-8")


def speaks_github(text):
    return re.search(r"#[0-9]", text) or any(word in text for word in GITHUB_WORDS)


def test_a_whole_run_logs_every_ticket_and_the_spec_by_the_files_trackers_names(driver):
    given_sessions_that_finish(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    log = log_of(driver)
    assert "START 7/1" in log
    assert "STEP  7/1 build" in log
    assert "LOOP  spec 7 " in log
    assert not speaks_github(log), log


def test_the_dry_run_names_every_ticket_by_the_files_trackers_names(driver):
    driver.put(two_free_tickets())

    ran = driver.dry_run()

    assert ran.status == 0, said(ran)
    assert "DRY   spec 7: " in ran.out
    assert not speaks_github(log_of(driver)), log_of(driver)


def test_a_spec_still_without_tickets_after_the_cut_stops_in_the_files_trackers_words(driver):
    driver.put({FOLDER + "/spec.md": spec_file()})

    ran = driver.run()

    assert ran.status == 1
    assert "STOP  spec 7 still has no tickets" in said(ran)
    assert not speaks_github(said(ran)), said(ran)


def test_a_spec_in_another_shape_is_turned_down_before_its_first_ticket_starts(driver):
    driver.put({
        FOLDER + "/spec.md": spec_file(body="## User Stories\n\n1. One.\n3. Three.\n"),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    })

    ran = driver.run()

    assert ran.status == 1
    assert "## User Stories skips 2: it goes from 1 to 3" in said(ran)
    assert "the spec has no ## Implementation Decisions heading" in said(ran)
    assert "START" not in ran.out


def test_a_spec_that_cannot_be_read_is_refused_naming_no_github_repo(driver):
    driver.put({"elsewhere.txt": "nothing about the spec\n"})

    ran = driver.dry_run()

    assert ran.status == 1
    assert "ABORT cannot read spec 7" in said(ran)
    assert not speaks_github(said(ran)), said(ran)
