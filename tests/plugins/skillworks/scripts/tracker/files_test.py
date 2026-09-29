# Driven through the dry run, so each case checks which ticket starts, not how it was found.

import contextlib
import io
import json
import re
from pathlib import Path

import pytest

import spec_loop
from conftest import Ran, RecordingRunner, Repo, git, write_steering
from spec_loop_test import Sessions, given_a_suite_that_passes
from steering.target_branch import LOOP_FILE
from stop import REFUSED, Stop
from tracker import publish
from tracker.files import Files

SPEC = "7"
FOLDER = ".specs/0007-local-tracker"
SPEC_BRANCH = "spec/local-tracker"

ME = "test@example.invalid"
RIVAL = "rival@example.invalid"

NO_TICKET = "DRY   no ticket is startable"


def next_is(ticket):
    return "DRY   the next ticket is {}/{}\n".format(SPEC, ticket)


COUNTED = ("## User Stories\n\n1. As a team member, I want a local tracker.\n\n"
           "## Implementation Decisions\n\n1. The tracker is files.\n\n## Surfaces\n\nNone\n")


def spec_file(status="open", branch=None, body=COUNTED):
    lines = ["---", "status: " + status]
    if branch is not None:
        lines.append("branch: " + branch)
    return "\n".join(lines + ["---", "", "# SPEC: A local tracker", "", body])


def ticket_file(title, status="open", blocked_by=(), claimed_by=""):
    return "\n".join([
        "---",
        "status: " + status,
        "blocked-by: [{}]".format(", ".join(str(number) for number in blocked_by)),
        "claimed-by: " + claimed_by,
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


class Racing(RecordingRunner):
    def __init__(self):
        super().__init__()
        self.before_push = None

    def run(self, args, where=None, env=None):
        if "push" in [str(a) for a in args] and self.before_push is not None:
            first, self.before_push = self.before_push, None
            first()
        return super().run(args, where, env)


# A run with a claude that answers nothing stops at the build, after its claim has reached origin.
def run_loop(runner, checkout, *flags):
    if "claude" not in runner.stubs:
        runner.stub("claude")
    write_steering(checkout)
    out, err = io.StringIO(), io.StringIO()
    with contextlib.chdir(checkout):
        status = spec_loop.main([SPEC, *flags], runner, out, err, lambda seconds: None)
    return Ran(status, out.getvalue(), err.getvalue())


class Driver:
    def __init__(self, repo, runner):
        self.repo = repo
        self.runner = runner

    def dry_run(self):
        return run_loop(self.runner, self.repo.work, "--dry-run")

    def run(self):
        return run_loop(self.runner, self.repo.work)

    def rival(self):
        other = self.repo.other_checkout()
        git(other, "config", "user.email", RIVAL)
        write_loop(other, json.loads((self.repo.work / LOOP_FILE).read_text(encoding="utf-8"))[
            "target-branch"])

        class Rival:
            def run(self):
                return run_loop(RecordingRunner(), other)
        return Rival()

    # Pushed from a clone of its own, so the main checkout never holds what the remote does.
    def push(self, files, branch="main"):
        other = self.repo.other_checkout()
        if branch != "main":
            git(other, "checkout", "--quiet", "-B", branch)
        commit_files(other, files, "Tracker state")
        git(other, "push", "--quiet", "origin", branch)


@pytest.fixture
def driver(tmp_path, monkeypatch):
    repo = Repo(tmp_path)
    monkeypatch.chdir(repo.work)
    monkeypatch.delenv("SPEC_LOOP_PERMISSION_MODE", raising=False)
    # A session is looked for under this case's own folder, so no real one can answer a check here.
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", (tmp_path / "claude").as_posix())
    write_loop(repo.work, "main")
    return Driver(repo, Racing())


def said(ran):
    return ran.out + ran.err


def test_the_dry_run_names_the_first_ticket_whose_blockers_are_all_closed(driver):
    driver.push({
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


def test_a_ticket_whose_blocker_is_open_is_not_picked_until_the_remote_closes_it(driver):
    blocker = ticket_path("01-read-loop-json")
    driver.push({
        FOLDER + "/spec.md": spec_file(),
        blocker: ticket_file("Read loop.json", claimed_by="someone@example.invalid"),
        ticket_path("02-close-in-worktree"): ticket_file("Close in the worktree", blocked_by=[1]),
    })

    blocked = driver.dry_run()
    driver.push({blocker: ticket_file("Read loop.json", status="closed")})
    unblocked = driver.dry_run()

    assert NO_TICKET in blocked.out, said(blocked)
    assert next_is(2) in unblocked.out, said(unblocked)


def test_a_blocker_closed_in_the_main_checkout_alone_changes_nothing(driver):
    blocker = ticket_path("01-read-loop-json")
    driver.push({
        FOLDER + "/spec.md": spec_file(),
        blocker: ticket_file("Read loop.json", claimed_by="someone@example.invalid"),
        ticket_path("02-close-in-worktree"): ticket_file("Close in the worktree", blocked_by=[1]),
    })
    git(driver.repo.work, "pull", "--quiet", "origin", "main")
    commit_files(driver.repo.work, {blocker: ticket_file("Read loop.json", status="closed")},
                 "Closed here and never pushed")

    ran = driver.dry_run()

    assert ran.status == 0, said(ran)
    assert NO_TICKET in ran.out


def test_a_spec_folder_only_in_the_main_checkout_is_not_read(driver):
    driver.push({"elsewhere.txt": "nothing about the spec\n"})
    commit_files(driver.repo.work, {
        FOLDER + "/spec.md": spec_file(),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    }, "Written here and never pushed")

    ran = driver.dry_run()

    assert ran.status == 1
    assert "cannot read" in said(ran)


def test_in_spec_mode_the_tickets_are_read_from_the_branch_the_spec_names(driver):
    write_loop(driver.repo.work, "spec")
    # A stale copy on another branch names the spec's branch and not its own, so it is not read.
    driver.push({
        FOLDER + "/spec.md": spec_file(branch=SPEC_BRANCH),
        ticket_path("01-read-loop-json"): ticket_file("Stale", status="closed"),
    }, branch="spec/stale")
    driver.push({
        FOLDER + "/spec.md": spec_file(branch=SPEC_BRANCH),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json", status="closed"),
        ticket_path("02-close-in-worktree"): ticket_file("Close in the worktree", blocked_by=[1]),
    }, branch=SPEC_BRANCH)

    ran = driver.dry_run()

    assert ran.status == 0, said(ran)
    assert next_is(2) in ran.out
    assert "Stale" not in ran.out


def claimed_on_remote(repo, name, branch="main"):
    text = git(repo.origin, "show", "{}:{}".format(branch, ticket_path(name)))
    return next(line[len("claimed-by:"):].strip() for line in text.split("\n")
                if line.startswith("claimed-by:"))


def two_free_tickets():
    return {
        FOLDER + "/spec.md": spec_file(),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
        ticket_path("02-close-in-worktree"): ticket_file("Close in the worktree"),
    }


def test_a_claim_pushes_a_commit_that_sets_claimed_by_on_the_target_branch(driver):
    driver.push(two_free_tickets())
    before = git(driver.repo.origin, "rev-parse", "main").strip()

    ran = driver.run()

    assert "START 7/1" in ran.out, said(ran)
    assert claimed_on_remote(driver.repo, "01-read-loop-json") == ME
    assert claimed_on_remote(driver.repo, "02-close-in-worktree") == ""
    assert git(driver.repo.origin, "log", "--format=%P", "{}..main".format(before)).split() == [before]
    changed = git(driver.repo.origin, "diff", "--name-only", before, "main").split()
    assert changed == [ticket_path("01-read-loop-json")]


def test_a_ticket_another_loop_claimed_is_not_picked(driver):
    driver.push(two_free_tickets())
    driver.push({ticket_path("01-read-loop-json"): ticket_file("Read loop.json",
                                                               claimed_by=RIVAL)})

    ran = driver.run()

    assert "START 7/2" in ran.out, said(ran)
    assert "START 7/1" not in ran.out
    assert claimed_on_remote(driver.repo, "01-read-loop-json") == RIVAL
    assert claimed_on_remote(driver.repo, "02-close-in-worktree") == ME


def test_two_loops_racing_for_one_ticket_build_different_tickets(driver):
    driver.push(two_free_tickets())
    rival = driver.rival()
    rivalled = []
    # The rival runs whole the moment this loop first pushes, so this loop's claim is the one that loses.
    driver.runner.before_push = lambda: rivalled.append(rival.run())

    ran = driver.run()

    assert "START 7/1" in rivalled[0].out, said(rivalled[0])
    assert len([call for call in driver.runner.calls if "push" in call]) == 2
    assert "START 7/2" in ran.out, said(ran)
    assert "START 7/1" not in ran.out
    assert claimed_on_remote(driver.repo, "01-read-loop-json") == RIVAL
    assert claimed_on_remote(driver.repo, "02-close-in-worktree") == ME


def test_in_spec_mode_a_claim_reaches_the_branch_the_spec_names(driver):
    write_loop(driver.repo.work, "spec")
    driver.push({
        FOLDER + "/spec.md": spec_file(branch=SPEC_BRANCH),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    }, branch=SPEC_BRANCH)

    ran = driver.run()

    assert "START 7/1" in ran.out, said(ran)
    assert claimed_on_remote(driver.repo, "01-read-loop-json", SPEC_BRANCH) == ME


def test_in_spec_mode_a_spec_that_names_no_branch_stops_the_dry_run(driver):
    write_loop(driver.repo.work, "spec")
    driver.push({
        FOLDER + "/spec.md": spec_file(),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    }, branch=SPEC_BRANCH)

    ran = driver.dry_run()

    assert ran.status == 1
    assert "branch in its spec.md frontmatter" in said(ran)


def test_in_spec_mode_the_stop_for_a_spec_that_names_no_branch_says_the_grill_writes_it(driver):
    write_loop(driver.repo.work, "spec")
    driver.push({
        FOLDER + "/spec.md": spec_file(),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    }, branch=SPEC_BRANCH)

    ran = driver.dry_run()

    assert "/skillworks:grill writes it" in said(ran)


# --- a close, in the commit that Lands ---------------------------------------

REFERENCE = "7/1"
FINISH = "implement {} --finish".format(REFERENCE)
NOTE = "Built the reader. Proved by the reader tests."
CODE = "reader.txt"


def closed_in_file(text):
    return text.replace("status: open", "status: closed") + "\n## Closing note\n\n" + NOTE + "\n"


def finishing(runner, trailer=REFERENCE, closes=True):
    def finish():
        tree = Path(runner.where)
        (tree / CODE).write_text("read\n", encoding="utf-8", newline="\n")
        if closes:
            held = tree / ticket_path("01-read-loop-json")
            held.write_text(closed_in_file(held.read_text(encoding="utf-8")), encoding="utf-8",
                            newline="\n")
        git(tree, "add", "-A")
        git(tree, "commit", "--quiet", "-m", "Built the reader\n\nTicket: " + trailer)
    return finish


def given_sessions_that_finish(driver, runs=None, **finish):
    given_a_suite_that_passes(driver, runs)
    sessions = Sessions(driver.repo, driver.runner)
    sessions.then[FINISH] = finishing(driver.runner, **finish)
    sessions.then["spec-drift"] = drifting(driver)
    sessions.then["spec-names"] = naming(driver)
    driver.push({
        FOLDER + "/spec.md": spec_file(),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    })
    return sessions


def on_remote(repo, path, branch="main"):
    return git(repo.origin, "show", "{}:{}".format(branch, path))


def status_on_remote_branch(repo, path, branch):
    return next(line[len("status:"):].strip() for line in on_remote(repo, path, branch).split("\n")
                if line.startswith("status:"))


def status_on_remote(repo, path):
    return status_on_remote_branch(repo, path, "main")


def asked_of_claude(driver):
    return [call[2] for call in driver.runner.started("claude")]


def test_a_landed_tickets_commit_holds_its_code_its_close_and_its_closing_note(driver):
    given_sessions_that_finish(driver)

    ran = driver.run()

    assert "DONE  7/1" in ran.out, said(ran)
    landed = git(driver.repo.origin, "log", "--format=%H", "--grep=Built the reader",
                 "main").split()
    assert len(landed) == 1
    changed = git(driver.repo.origin, "show", "--name-only", "--format=", landed[0]).split()
    assert CODE in changed
    assert ticket_path("01-read-loop-json") in changed
    assert status_on_remote(driver.repo, ticket_path("01-read-loop-json")) == "closed"
    assert NOTE in on_remote(driver.repo, ticket_path("01-read-loop-json"))


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


def test_a_commit_naming_the_ticket_alone_is_not_landed(driver):
    given_sessions_that_finish(driver, trailer="#1")

    ran = driver.run()

    assert ran.status == 1
    assert "names ticket #1, and this is 7/1" in said(ran)
    assert status_on_remote(driver.repo, ticket_path("01-read-loop-json")) == "open"


def test_a_ticket_whose_land_fails_is_still_open_on_the_remote(driver):
    given_sessions_that_finish(driver)
    driver.runner.refuse("HEAD:main", "remote: the push was turned down")

    ran = driver.run()

    assert ran.status == 1
    assert "did not reach main" in said(ran)
    assert status_on_remote(driver.repo, ticket_path("01-read-loop-json")) == "open"
    assert CODE not in git(driver.repo.origin, "ls-tree", "--name-only", "main").split()


def test_a_finish_that_left_its_ticket_file_open_is_nudged_to_close_it_there(driver):
    given_sessions_that_finish(driver, closes=False)

    ran = driver.run()

    assert ran.status == 1
    nudges = [prompt for prompt in asked_of_claude(driver) if not prompt.startswith("/")]
    assert nudges, said(ran)
    assert "status: closed" in nudges[0]
    assert "same commit" in nudges[0]
    assert status_on_remote(driver.repo, ticket_path("01-read-loop-json")) == "open"


def test_after_the_last_ticket_and_the_drift_check_the_spec_is_closed_on_the_remote(driver):
    given_sessions_that_finish(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    assert status_on_remote(driver.repo, FOLDER + "/spec.md") == "closed"
    assert (ran.out.index("DRIFT") < ran.out.index("FULL  main at")
            < ran.out.index("CLOSE spec 7") < ran.out.index("END   spec 7"))


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
    assert "END" not in ran.out
    assert status_on_remote(driver.repo, FOLDER + "/spec.md") == "open"


def given_sessions_that_finish_on_the_spec_branch(driver):
    git(driver.repo.work, "checkout", "--quiet", "-b", SPEC_BRANCH)
    driver.repo.target = SPEC_BRANCH
    write_loop(driver.repo.work, "spec")
    write_files(driver.repo.work, {
        FOLDER + "/spec.md": spec_file(branch=SPEC_BRANCH),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    })
    given_a_suite_that_passes(driver)
    sessions = Sessions(driver.repo, driver.runner)
    sessions.then[FINISH] = finishing(driver.runner)
    sessions.then["spec-drift"] = drifting(driver)
    sessions.then["spec-names"] = naming(driver)
    return sessions


def test_in_spec_mode_the_run_ends_at_the_close_and_never_calls_gh(driver):
    given_sessions_that_finish_on_the_spec_branch(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    assert driver.runner.started("gh") == []
    assert status_on_remote_branch(driver.repo, FOLDER + "/spec.md", SPEC_BRANCH) == "closed"
    assert "CLOSE spec 7" in ran.out


def test_in_spec_mode_the_last_lines_ask_for_the_pull_request_from_the_spec_branch(driver):
    given_sessions_that_finish_on_the_spec_branch(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    last = "\n".join(ran.out.rstrip("\n").split("\n")[-3:])
    assert "open the pull request from {}".format(SPEC_BRANCH) in last
    assert "mark it ready for review" in last


VERDICTS = "### Verdicts\n\n- S1: Done\n- D1: Done\n"

REPORT = "## Drift report\n\n" + VERDICTS


def recording(driver, command, report):
    def record():
        held = driver.repo.root / (command + "-report.md")
        held.write_text(report, encoding="utf-8", newline="\n")
        publish.main([command, SPEC, held.as_posix()], driver.runner, io.StringIO(),
                     io.StringIO(), lambda seconds: None, driver.repo.work.as_posix())
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
    text = on_remote(driver.repo, FOLDER + "/spec.md")
    assert REPORT + "\n" + NAMES in text
    assert status_on_remote(driver.repo, FOLDER + "/spec.md") == "closed"
    held = driver.repo.work / ".spec-loop" / SPEC / "drift.md"
    assert held.read_text(encoding="utf-8") == VERDICTS
    assert "DRIFT the report is recorded on spec 7" in ran.out
    assert "COUNT the spec holds 2 items, and the drift report gives 2 Verdicts" in ran.out


def test_the_loop_reads_back_the_name_report_recorded_below_the_drift_report(driver):
    given_sessions_that_finish(driver)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    assert on_remote(driver.repo, FOLDER + "/spec.md").endswith(NAMES)
    held = driver.repo.work / ".spec-loop" / SPEC / "names.md"
    assert held.read_text(encoding="utf-8") == RENAMES
    assert "NAMES no rename is owed on spec 7" in ran.out


def test_a_name_check_that_recorded_no_report_stops_and_leaves_the_spec_open(driver):
    sessions = given_sessions_that_finish(driver)
    del sessions.then["spec-names"]

    ran = driver.run()

    assert ran.status == 1
    assert "STOP  the Name check recorded no report on spec 7" in ran.out
    assert status_on_remote(driver.repo, FOLDER + "/spec.md") == "open"


def test_a_drift_check_that_recorded_no_report_stops_and_leaves_the_spec_open(driver):
    sessions = given_sessions_that_finish(driver)
    del sessions.then["spec-drift"]

    ran = driver.run()

    assert ran.status == 1
    assert "STOP  the drift check recorded no report on spec 7" in ran.out
    assert status_on_remote(driver.repo, FOLDER + "/spec.md") == "open"


def test_the_flakes_of_a_run_are_noted_in_the_spec_file_above_its_reports(driver):
    given_sessions_that_finish(driver, runs=2)
    driver.runner.refuse("dotnet test Skillworks.slnx", "a Span test failed", times=1)

    ran = driver.run()

    assert ran.status == 0, said(ran)
    text = on_remote(driver.repo, FOLDER + "/spec.md")
    [kept] = sorted((driver.repo.work / ".spec-loop" / SPEC).glob("flake-ticket-1-suite-*.out"))
    note = text[text.index("## Flakes\n"):text.index(REPORT)]
    assert "- dotnet test Skillworks.slnx, in 7/1 suite: {}\n".format(kept.as_posix()) in note
    assert text.endswith(REPORT + "\n" + NAMES)
    assert status_on_remote(driver.repo, FOLDER + "/spec.md") == "closed"


def test_a_later_note_takes_the_place_of_an_earlier_one_and_leaves_the_reports(driver):
    driver.push({FOLDER + "/spec.md": spec_file(body=COUNTED + "\n" + REPORT + "\n" + NAMES)})
    tracker = files_tracker(driver)

    tracker.record_flakes(SPEC, "## Flakes\n\n- the first run's Flake\n")
    tracker.record_flakes(SPEC, "## Flakes\n\n- the second run's Flake\n")

    text = on_remote(driver.repo, FOLDER + "/spec.md")
    assert text.count("## Flakes") == 1
    assert "the first run's Flake" not in text
    assert text.index("the second run's Flake") < text.index(REPORT)
    assert tracker.drift_report(SPEC) == VERDICTS.strip("\n")
    assert tracker.name_report(SPEC) == RENAMES.strip("\n")


GAP_TICKET = "02-ticket-build-the-gaps-the-drift-check-found"

D1_MISSING = "## Drift report\n\n### Verdicts\n\n- S1: Done\n- D1: Missing. Not there.\n"


# A file of its own, since the ticket landed before it already holds what every build writes.
def given_a_filed_ticket_that_lands(driver, sessions, slug):
    def build():
        (Path(driver.runner.where) / "filed.txt").write_text("built\n", encoding="utf-8",
                                                             newline="\n")

    def finish():
        tree = Path(driver.runner.where)
        held = tree / ticket_path(slug)
        held.write_text(held.read_text(encoding="utf-8").replace("status: open", "status: closed")
                        + "\n## Closing note\n\nBuilt it.\n", encoding="utf-8", newline="\n")
        git(tree, "add", "-A")
        git(tree, "commit", "--quiet", "-m", "Built it\n\nTicket: {}/2".format(SPEC))

    sessions.then["implement {}/2 --stop-after-tests".format(SPEC)] = build
    sessions.then["implement {}/2 --finish".format(SPEC)] = finish


def given_a_gap_round(driver, *reports):
    sessions = given_sessions_that_finish(driver)
    given_a_filed_ticket_that_lands(driver, sessions, GAP_TICKET)
    waiting = list(reports)
    sessions.then["spec-drift"] = lambda: drifting(driver, waiting.pop(0))()
    return sessions


def test_a_gap_is_filed_as_a_ticket_file_under_the_spec_and_a_closed_round_closes_it(driver):
    given_a_gap_round(driver, D1_MISSING, "## Drift report\n\n### Verdicts\n\n- D1: Done\n")

    ran = driver.run()

    assert ran.status == 0, said(ran)
    assert "FILED {}/2 under spec {} builds 1 Gap".format(SPEC, SPEC) in ran.out
    filed = on_remote(driver.repo, ticket_path(GAP_TICKET))
    assert "### D1\n\n> The tracker is files.\n\nVerdict: Missing. Not there.\n" in filed
    assert status_on_remote(driver.repo, ticket_path(GAP_TICKET)) == "closed"
    assert status_on_remote(driver.repo, FOLDER + "/spec.md") == "closed"


def test_a_gap_left_after_the_round_leaves_the_spec_open(driver):
    given_a_gap_round(driver, D1_MISSING,
                      "## Drift report\n\n### Verdicts\n\n- D1: Missing. Not there.\n")

    ran = driver.run()

    assert ran.status == 1
    assert "      Gap: D1 is Missing: Not there.\n" in ran.out
    assert "CLOSE" not in ran.out
    assert status_on_remote(driver.repo, FOLDER + "/spec.md") == "open"


RENAME_TICKET = "02-ticket-make-the-renames-the-name-check-found"

BATCH_MOVED = "## Name report\n\n### Renames\n\n- `Batch`: it now holds a whole spec.\n"


def given_a_rename_round(driver, *reports):
    sessions = given_sessions_that_finish(driver)
    given_a_filed_ticket_that_lands(driver, sessions, RENAME_TICKET)
    waiting = list(reports)
    sessions.then["spec-names"] = lambda: naming(driver, waiting.pop(0))()
    return sessions


def test_a_rename_is_filed_as_a_ticket_file_under_the_spec_and_a_rename_made_closes_it(driver):
    given_a_rename_round(driver, BATCH_MOVED, "## Name report\n\n### Verdicts\n\n- Batch: Done\n")

    ran = driver.run()

    assert ran.status == 0, said(ran)
    assert "FILED {}/2 under spec {} makes 1 rename".format(SPEC, SPEC) in ran.out
    filed = on_remote(driver.repo, ticket_path(RENAME_TICKET))
    assert "### Batch\n\n> `Batch`: it now holds a whole spec.\n" in filed
    assert status_on_remote(driver.repo, ticket_path(RENAME_TICKET)) == "closed"
    assert "NAMES every rename is made on spec 7" in ran.out
    assert status_on_remote(driver.repo, FOLDER + "/spec.md") == "closed"


def test_a_rename_not_made_leaves_the_spec_open(driver):
    given_a_rename_round(driver, BATCH_MOVED,
                         "## Name report\n\n### Verdicts\n\n- Batch: Not done. Still there.\n")

    ran = driver.run()

    assert ran.status == 1
    assert "      Not made: Batch is Not done: Still there.\n" in ran.out
    assert "CLOSE" not in ran.out
    assert status_on_remote(driver.repo, FOLDER + "/spec.md") == "open"


def test_a_resolver_reads_how_a_landed_ticket_was_closed_from_its_closing_note(driver):
    given_sessions_that_finish(driver)
    ran = driver.run()

    read = Files(RecordingRunner(), driver.repo.work, "main", SPEC).closing_note(REFERENCE)

    assert ran.status == 0, said(ran)
    assert read == NOTE


# --- filing a ticket under a spec --------------------------------------------

GAPS = "## What to build\n\nS2: Missing.\n"


def files_tracker(driver, target="main"):
    return Files(RecordingRunner(), driver.repo.work, target, SPEC, lambda seconds: None)


def test_a_filed_ticket_is_pushed_next_in_number_open_and_unclaimed(driver):
    driver.push(two_free_tickets())

    number = files_tracker(driver).file_ticket(SPEC, "TICKET: Build the Gaps", GAPS)

    assert number == "3"
    assert on_remote(driver.repo, ticket_path("03-ticket-build-the-gaps")) == (
        "---\nstatus: open\nblocked-by: []\nclaimed-by: \n---\n\n"
        "# TICKET: Build the Gaps\n\n" + GAPS)


def test_a_filed_ticket_is_listed_among_the_specs_open_tickets(driver):
    driver.push(two_free_tickets())
    tracker = files_tracker(driver)

    number = tracker.file_ticket(SPEC, "TICKET: Build the Gaps", GAPS)

    assert tracker.open_tickets(SPEC) == ["1", "2", number]
    assert tracker.title(number) == "TICKET: Build the Gaps"
    assert tracker.open_blockers(number) == 0


def test_a_filed_ticket_that_loses_a_race_for_its_number_reads_again(driver):
    driver.push(two_free_tickets())
    tracker = Files(Racing(), driver.repo.work, "main", SPEC, lambda seconds: None)
    tracker.runner.before_push = lambda: driver.push(
        {ticket_path("03-rival"): ticket_file("TICKET: Rival")})

    number = tracker.file_ticket(SPEC, "TICKET: Build the Gaps", GAPS)

    assert number == "4"
    assert tracker.title("3") == "TICKET: Rival"
    assert tracker.title("4") == "TICKET: Build the Gaps"


def test_in_spec_mode_a_filed_ticket_reaches_the_branch_the_spec_names(driver):
    driver.push({
        FOLDER + "/spec.md": spec_file(branch=SPEC_BRANCH),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    }, branch=SPEC_BRANCH)

    number = files_tracker(driver, target=None).file_ticket(SPEC, "TICKET: Build the Gaps", GAPS)

    assert number == "2"
    assert "# TICKET: Build the Gaps" in on_remote(
        driver.repo, ticket_path("02-ticket-build-the-gaps"), SPEC_BRANCH)


def test_a_ticket_filed_under_a_spec_with_no_folder_stops_and_says_so(driver):
    driver.push({"elsewhere.txt": "nothing about the spec\n"})

    with pytest.raises(Stop) as stopped:
        files_tracker(driver).file_ticket(SPEC, "TICKET: Build the Gaps", GAPS)

    assert stopped.value.status == REFUSED
    assert "Spec 7 has no folder on origin/main" in stopped.value.said


def test_a_spec_whose_run_stopped_is_left_open_on_the_remote(driver):
    given_sessions_that_finish(driver, closes=False)

    ran = driver.run()

    assert ran.status == 1
    assert status_on_remote(driver.repo, FOLDER + "/spec.md") == "open"


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
    driver.push(two_free_tickets())

    ran = driver.dry_run()

    assert ran.status == 0, said(ran)
    assert "DRY   spec 7: " in ran.out
    assert not speaks_github(log_of(driver)), log_of(driver)


def test_a_spec_still_without_tickets_after_the_tickets_step_stops_in_the_files_trackers_words(driver):
    driver.push({FOLDER + "/spec.md": spec_file()})

    ran = driver.run()

    assert ran.status == 1
    assert "STOP  spec 7 still has no tickets" in said(ran)
    assert not speaks_github(said(ran)), said(ran)


def test_a_spec_in_another_shape_is_turned_down_before_its_first_ticket_is_claimed(driver):
    driver.push({
        FOLDER + "/spec.md": spec_file(body="## User Stories\n\n1. One.\n3. Three.\n"),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    })

    ran = driver.run()

    assert ran.status == 1
    assert "## User Stories skips 2: it goes from 1 to 3" in said(ran)
    assert "the spec has no ## Implementation Decisions heading" in said(ran)
    assert "claimed-by: \n" in on_remote(driver.repo, ticket_path("01-read-loop-json"))


def test_a_spec_that_cannot_be_read_is_refused_naming_no_github_repo(driver):
    driver.push({"elsewhere.txt": "nothing about the spec\n"})

    ran = driver.dry_run()

    assert ran.status == 1
    assert "ABORT cannot read spec 7" in said(ran)
    assert not speaks_github(said(ran)), said(ran)
