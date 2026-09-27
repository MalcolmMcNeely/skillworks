# Driven through the dry run, so each case checks which ticket starts, not how it was found.

import contextlib
import io
import json
from pathlib import Path

import pytest

import spec_loop
from conftest import Ran, RecordingRunner, Repo, git
from spec_loop_test import Sessions, given_a_suite_that_passes
from steering.target_branch import LOOP_FILE
from tracker.files import Files

SPEC = "7"
FOLDER = ".specs/0007-local-tracker"
SPEC_BRANCH = "spec/local-tracker"

ME = "test@example.invalid"
RIVAL = "rival@example.invalid"

NO_TICKET = "DRY   no ticket is startable"


def next_is(ticket):
    return "DRY   the next ticket is #{}\n".format(ticket)


def spec_file(status="open", branch=None):
    lines = ["---", "status: " + status]
    if branch is not None:
        lines.append("branch: " + branch)
    return "\n".join(lines + ["---", "", "# SPEC: A local tracker", ""])


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
    assert "#1 [closed] Read loop.json" in ran.out
    assert "#2 [open] Close in the worktree" in ran.out


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

    assert "START #1" in ran.out, said(ran)
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

    assert "START #2" in ran.out, said(ran)
    assert "START #1" not in ran.out
    assert claimed_on_remote(driver.repo, "01-read-loop-json") == RIVAL
    assert claimed_on_remote(driver.repo, "02-close-in-worktree") == ME


def test_two_loops_racing_for_one_ticket_build_different_tickets(driver):
    driver.push(two_free_tickets())
    rival = driver.rival()
    rivalled = []
    # The rival runs whole the moment this loop first pushes, so this loop's claim is the one that loses.
    driver.runner.before_push = lambda: rivalled.append(rival.run())

    ran = driver.run()

    assert "START #1" in rivalled[0].out, said(rivalled[0])
    assert len([call for call in driver.runner.calls if "push" in call]) == 2
    assert "START #2" in ran.out, said(ran)
    assert "START #1" not in ran.out
    assert claimed_on_remote(driver.repo, "01-read-loop-json") == RIVAL
    assert claimed_on_remote(driver.repo, "02-close-in-worktree") == ME


def test_in_spec_mode_a_claim_reaches_the_branch_the_spec_names(driver):
    write_loop(driver.repo.work, "spec")
    driver.push({
        FOLDER + "/spec.md": spec_file(branch=SPEC_BRANCH),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    }, branch=SPEC_BRANCH)

    ran = driver.run()

    assert "START #1" in ran.out, said(ran)
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


def given_sessions_that_finish(driver, **finish):
    given_a_suite_that_passes(driver)
    sessions = Sessions(driver.repo, driver.runner)
    sessions.then[FINISH] = finishing(driver.runner, **finish)
    driver.push({
        FOLDER + "/spec.md": spec_file(),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    })
    return sessions


def on_remote(repo, path, branch="main"):
    return git(repo.origin, "show", "{}:{}".format(branch, path))


def status_on_remote(repo, path):
    return next(line[len("status:"):].strip() for line in on_remote(repo, path).split("\n")
                if line.startswith("status:"))


def asked_of_claude(driver):
    return [call[2] for call in driver.runner.started("claude")]


def test_a_landed_tickets_commit_holds_its_code_its_close_and_its_closing_note(driver):
    given_sessions_that_finish(driver)

    ran = driver.run()

    assert "DONE  #1" in ran.out, said(ran)
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
    assert ran.out.index("DRIFT") < ran.out.index("CLOSE spec #7") < ran.out.index("END   spec #7")


def test_a_resolver_reads_how_a_landed_ticket_was_closed_from_its_closing_note(driver):
    given_sessions_that_finish(driver)
    ran = driver.run()

    read = Files(RecordingRunner(), driver.repo.work, "main", SPEC).closing_note(REFERENCE)

    assert ran.status == 0, said(ran)
    assert read == NOTE


def test_a_spec_whose_run_stopped_is_left_open_on_the_remote(driver):
    given_sessions_that_finish(driver, closes=False)

    ran = driver.run()

    assert ran.status == 1
    assert status_on_remote(driver.repo, FOLDER + "/spec.md") == "open"
