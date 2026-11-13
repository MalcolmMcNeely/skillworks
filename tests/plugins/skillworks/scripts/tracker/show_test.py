# Driven through main against a stand-in for gh, so each case checks what a Session reads.

import contextlib
import io
import json

import pytest

from conftest import Ran, Repo, launch
from files_test import write_loop
from steering.target_branch import LOOP_FILE
from tracker import show


class Issues:
    def __init__(self, runner):
        self.runner = runner
        self.held = {}
        runner.stub("gh", does=self.answer)

    def answer(self):
        called = self.runner.calls[-1][1:]
        if called[:2] == ["repo", "view"]:
            return Ran(0, "owner/repo\n", "")
        if called[:2] == ["api", "user"]:
            return Ran(0, "me\n", "")
        if called[:2] == ["issue", "view"]:
            if called[2] not in self.held:
                return Ran(1, "", "GraphQL: Could not resolve to an issue with the number of {}.\n".format(
                    called[2]))
            title, body, comments = self.held[called[2]]
            return Ran(0, json.dumps({"title": title, "body": body, "comments": [
                {"author": {"login": login}, "body": said} for login, said in comments]}), "")
        return None


def on_github(repo):
    path = repo.work / LOOP_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tracker": "github", "target-branch": "main"}), encoding="utf-8")


@pytest.fixture
def repo(tmp_path):
    made = Repo(tmp_path / "repo")
    on_github(made)
    return made


@pytest.fixture
def issues(runner):
    return Issues(runner)


def shown(repo, runner, *argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.chdir(repo.work):
        status = show.main(list(argv), runner, out, err)
    return Ran(status, out.getvalue(), err.getvalue())


def test_a_ticket_is_printed_with_its_title_its_body_and_each_comment(repo, runner, issues):
    issues.held["642"] = ("TICKET: Read and close", "## What to build\n\nTwo commands.\n",
                          [("ana", "Started."), ("bo", "Done.\n")])

    ran = shown(repo, runner, "642")

    assert (ran.status, ran.out) == (0, "# TICKET: Read and close\n\n"
                                        "## What to build\n\nTwo commands.\n\n"
                                        "## Comment by ana\n\nStarted.\n\n"
                                        "## Comment by bo\n\nDone.\n"), ran.err


def test_a_spec_is_printed_the_same_way_as_a_ticket(repo, runner, issues):
    issues.held["639"] = ("SPEC: Many specs at once", "## Problem Statement\n\nOne at a time.\n", [])

    ran = shown(repo, runner, "639")

    assert (ran.status, ran.out) == (0, "# SPEC: Many specs at once\n\n"
                                        "## Problem Statement\n\nOne at a time.\n"), ran.err


def test_an_issue_github_will_not_give_is_refused_with_what_gh_said(repo, runner, issues):
    ran = shown(repo, runner, "9999")

    assert (ran.status, ran.out) == (1, "")
    assert "Could not resolve to an issue with the number of 9999." in ran.err


def test_a_number_that_is_not_a_number_is_told_the_usage(repo, runner, issues):
    ran = shown(repo, runner, "#642")

    assert ran.status == 64
    assert "usage: tracker-show <spec-or-ticket>" in ran.err


def test_the_command_runs_from_the_plugins_bin_folder_and_turns_down_the_files_tracker(repo):
    write_loop(repo.work, "main")

    ran = launch("tracker-show", "642", where=repo.work)

    assert ran.status == 1, ran.out + ran.err
    assert "tracker-show serves the GitHub Tracker alone so far" in ran.err
