# Driven through main against a stand-in for gh, so each case checks what reached the issue.

import contextlib
import io

import pytest

from clock.held_clock import HeldClock
from conftest import Ran, Repo, launch
from files_test import FOLDER, spec_file, ticket_file, ticket_path, write_files, write_loop
from runner import Subprocess
from sidecar.sidecar import Sidecar, sidecar_of
from show_test import on_github
from tracker import close

NOTE = "Built both commands.\n\nshow_test.py and close_test.py prove them.\n"


class Issues:
    def __init__(self, runner):
        self.runner = runner
        self.states = {}
        self.notes = {}
        self.fails = False
        runner.stub("gh", does=self.answer)

    def answer(self):
        called = self.runner.calls[-1][1:]
        if called[:2] == ["repo", "view"]:
            return Ran(0, "owner/repo\n", "")
        if called[:2] == ["api", "user"]:
            return Ran(0, "me\n", "")
        if called[0] == "api" and called[-2:] == ["--jq", ".state"]:
            return Ran(0, self.states[called[1].rsplit("/", 1)[-1]] + "\n", "")
        if called[:2] == ["issue", "close"]:
            if self.fails:
                return Ran(1, "", "HTTP 502: Bad Gateway\n")
            ticket = called[2]
            self.states[ticket] = "closed"
            self.notes[ticket] = (called[called.index("--comment") + 1],
                                  called[called.index("--reason") + 1])
            return Ran(0, "", "")
        return None


@pytest.fixture
def repo(tmp_path):
    made = Repo(tmp_path / "repo")
    on_github(made)
    return made


@pytest.fixture
def issues(runner):
    made = Issues(runner)
    made.states["642"] = "open"
    return made


def closed(repo, runner, *argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.chdir(repo.work):
        status = close.main(list(argv), runner, out, err)
    return Ran(status, out.getvalue(), err.getvalue())


def note_file(repo, text=NOTE):
    path = repo.work / "closing-note.md"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path.name


def test_a_ticket_is_closed_as_completed_with_the_note_as_its_comment(repo, runner, issues):
    ran = closed(repo, runner, "642", note_file(repo))

    assert (ran.status, issues.notes) == (0, {"642": (NOTE, "completed")}), ran.err


def test_a_rerun_on_a_closed_ticket_changes_nothing_and_says_so(repo, runner, issues):
    closed(repo, runner, "642", note_file(repo))

    ran = closed(repo, runner, "642", note_file(repo, "A second note.\n"))

    assert (ran.status, issues.notes["642"][0]) == (0, NOTE), ran.err
    assert "Ticket #642 is already closed, so nothing changed." in ran.err


def test_a_close_github_turns_down_leaves_the_ticket_open_and_says_to_run_again(repo, runner, issues):
    issues.fails = True

    ran = closed(repo, runner, "642", note_file(repo))

    assert (ran.status, issues.states["642"]) == (1, "open")
    assert "HTTP 502: Bad Gateway" in ran.err and "again" in ran.err


def test_a_note_file_that_cannot_be_read_closes_nothing(repo, runner, issues):
    ran = closed(repo, runner, "642", "missing.md")

    assert (ran.status, issues.states["642"]) == (1, "open")
    assert "missing.md could not be read" in ran.err


def test_a_call_with_no_note_file_is_told_the_usage(repo, runner, issues):
    ran = closed(repo, runner, "642")

    assert ran.status == 64
    assert "usage: tracker-close <ticket> <note-file>" in ran.err


@pytest.fixture
def in_files(repo):
    write_loop(repo.work, "main")
    Sidecar.of(Subprocess(), repo.work, HeldClock()).write("Tracker state", lambda folder: write_files(
        folder, {FOLDER + "/spec.md": spec_file(),
                 ticket_path("01-read-loop-json"): ticket_file("TICKET: Read loop.json")}))
    return repo


def in_sidecar(repo):
    return (sidecar_of(Subprocess(), repo.work) / ticket_path("01-read-loop-json")).read_text(
        encoding="utf-8")


def test_with_the_files_tracker_a_ticket_is_closed_in_the_sidecar_with_its_closing_note(
        in_files, runner):
    ran = closed(in_files, runner, "7/1", note_file(in_files))

    assert (ran.status, ran.out) == (0, "Closed 7/1.\n"), ran.err
    assert in_sidecar(in_files).startswith("---\nstatus: closed\n")
    assert in_sidecar(in_files).endswith("## Closing note\n\n" + NOTE)


def test_with_the_files_tracker_a_rerun_on_a_closed_ticket_changes_nothing_and_says_so(
        in_files, runner):
    closed(in_files, runner, "7/1", note_file(in_files))

    ran = closed(in_files, runner, "7/1", note_file(in_files, "A second note.\n"))

    assert (ran.status, in_sidecar(in_files).endswith(NOTE)) == (0, True), ran.err
    assert "Ticket 7/1 is already closed, so nothing changed." in ran.err


def test_with_the_files_tracker_a_spec_alone_closes_nothing(in_files, runner):
    ran = closed(in_files, runner, "7", note_file(in_files))

    assert ran.status == 1
    assert "such as 7/2" in ran.err
    assert in_sidecar(in_files).startswith("---\nstatus: open\n")


def test_the_command_runs_from_the_plugins_bin_folder_with_the_files_tracker(in_files):
    ran = launch("tracker-close", "7/1", note_file(in_files), where=in_files.work)

    assert (ran.status, ran.out) == (0, "Closed 7/1.\n"), ran.err
