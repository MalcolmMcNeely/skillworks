# Driven through main against a stand-in for gh, so each case checks what reached the issue.

import contextlib
import io

import pytest

from conftest import Ran, Repo, launch
from files_test import write_loop
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


def test_the_command_runs_from_the_plugins_bin_folder_and_turns_down_the_files_tracker(repo):
    write_loop(repo.work, "main")

    ran = launch("tracker-close", "642", note_file(repo), where=repo.work)

    assert ran.status == 1, ran.out + ran.err
    assert "tracker-close serves the GitHub Tracker alone so far" in ran.err
