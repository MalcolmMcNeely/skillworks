# Driven through the dry run, so each case checks which ticket starts, not how it was found.

import io
import json
from pathlib import Path

import pytest

import spec_loop
from conftest import Ran, Repo, git
from steering.target_branch import LOOP_FILE

SPEC = "7"
FOLDER = ".specs/0007-local-tracker"
SPEC_BRANCH = "spec/local-tracker"

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


class Driver:
    def __init__(self, repo, runner):
        self.repo = repo
        self.runner = runner

    def dry_run(self):
        out, err = io.StringIO(), io.StringIO()
        status = spec_loop.main([SPEC, "--dry-run"], self.runner, out, err, lambda seconds: None)
        return Ran(status, out.getvalue(), err.getvalue())

    # Pushed from a clone of its own, so the main checkout never holds what the remote does.
    def push(self, files, branch="main"):
        other = self.repo.other_checkout()
        if branch != "main":
            git(other, "checkout", "--quiet", "-B", branch)
        commit_files(other, files, "Tracker state")
        git(other, "push", "--quiet", "origin", branch)


@pytest.fixture
def driver(tmp_path, runner, monkeypatch):
    repo = Repo(tmp_path)
    monkeypatch.chdir(repo.work)
    monkeypatch.delenv("SPEC_LOOP_PERMISSION_MODE", raising=False)
    write_loop(repo.work, "main")
    # Enough of a claude for the preflight to find one, and none of a session.
    runner.stub("claude")
    return Driver(repo, runner)


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


def test_in_spec_mode_a_spec_that_names_no_branch_stops_the_dry_run(driver):
    write_loop(driver.repo.work, "spec")
    driver.push({
        FOLDER + "/spec.md": spec_file(),
        ticket_path("01-read-loop-json"): ticket_file("Read loop.json"),
    }, branch=SPEC_BRANCH)

    ran = driver.dry_run()

    assert ran.status == 1
    assert "branch in its spec.md frontmatter" in said(ran)
