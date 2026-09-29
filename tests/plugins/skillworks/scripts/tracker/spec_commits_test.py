# Driven through main against a real origin, so each case checks the commits a check would be handed.

import contextlib
import io
import json
import re

import pytest

from conftest import Ran, Repo, git, launch
from files_test import commit_files, spec_file, ticket_file, write_loop
from steering.target_branch import LOOP_FILE
from tracker import spec_commits

FOLDER = ".specs/0007-local-tracker"


class History:
    def __init__(self, repo, runner):
        self.repo = repo
        self.runner = runner
        self.other = repo.other_checkout()

    # Pushed from a clone of its own, so only the fetch the command makes can find it.
    def commit(self, subject, trailers=(), files=None):
        name = re.sub(r"[^a-z]+", "-", subject.lower()).strip("-") + ".txt"
        message = subject + ("\n\n" + "\n".join(trailers) if trailers else "")
        commit_files(self.other, files or {name: subject + "\n"}, message)
        branch = git(self.other, "branch", "--show-current").strip()
        git(self.other, "push", "--quiet", "origin", branch)
        return git(self.other, "rev-parse", "HEAD").strip()

    def move_to(self, branch):
        held = git(self.other, "branch", "--list", branch).strip()
        git(self.other, "checkout", "--quiet", *([branch] if held else ["-b", branch]))

    def run(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.chdir(self.repo.work):
            status = spec_commits.main(list(argv), self.runner, out, err, lambda seconds: None)
        return Ran(status, out.getvalue(), err.getvalue())


def printed(ran):
    return re.findall(r"^commit ([0-9a-f]{40})$", ran.out, re.MULTILINE)


def said(ran):
    return ran.out + ran.err


def on_files(repo, target="main"):
    write_loop(repo.work, target)


@pytest.fixture
def history(tmp_path, runner):
    repo = Repo(tmp_path)
    on_files(repo)
    return History(repo, runner)


def four_tickets():
    return {FOLDER + "/spec.md": spec_file(),
            FOLDER + "/tickets/01-read.md": ticket_file("TICKET: Read"),
            FOLDER + "/tickets/02-write.md": ticket_file("TICKET: Write"),
            FOLDER + "/tickets/03-gap.md": ticket_file("TICKET: Gap"),
            FOLDER + "/tickets/04-rename.md": ticket_file("TICKET: Rename")}


def test_with_files_the_commits_that_name_the_specs_tickets_are_printed_and_no_other(history):
    base = history.commit("The tickets of spec 7", files=four_tickets())
    read = history.commit("Read", ["Ticket: 7/1"])
    history.commit("A hand fix")
    history.commit("Another spec's work", ["Ticket: 8/1"])
    gap = history.commit("Fill the gap", ["Ticket: 7/3"])
    rename = history.commit("Rename", ["Co-Authored-By: Somebody <a@b.invalid>", "Ticket: 7/4"])

    ran = history.run("7", base)

    assert ran.status == 0, said(ran)
    assert printed(ran) == [read, gap, rename]


def test_commits_at_or_before_the_base_are_left_out(history):
    history.commit("The tickets of spec 7", files=four_tickets())
    history.commit("Read before the loop", ["Ticket: 7/1"])
    base = history.commit("Write at the base", ["Ticket: 7/2"])
    after = history.commit("Read again", ["Ticket: 7/1"])

    ran = history.run("7", base)

    assert printed(ran) == [after]


def test_a_commit_with_several_ticket_trailers_is_printed_when_any_names_the_specs_ticket(history):
    base = history.commit("The tickets of spec 7", files=four_tickets())
    shared = history.commit("Shared fix", ["Ticket: 8/1", "Ticket: 7/2"])

    ran = history.run("7", base)

    assert printed(ran) == [shared]


def test_each_commit_is_printed_oldest_first_with_its_trailer_and_its_patch(history):
    base = history.commit("The tickets of spec 7", files=four_tickets())
    history.commit("Read", ["Ticket: 7/1"], {"read.txt": "the first line\n"})
    history.commit("Write", ["Ticket: 7/2"], {"write.txt": "the second line\n"})

    ran = history.run("7", base)

    assert re.search(r"Read\n\s+Ticket: 7/1\n\s+diff --git a/read.txt b/read.txt\n.*"
                     r"\+the first line\n.*"
                     r"Write\n\s+Ticket: 7/2\n\s+diff --git a/write.txt b/write.txt\n.*"
                     r"\+the second line\n", ran.out, re.DOTALL), ran.out


def test_the_checkout_and_the_tracker_are_left_as_they_were(history):
    base = history.commit("The tickets of spec 7", files=four_tickets())
    history.commit("Read", ["Ticket: 7/1"])
    work = history.repo.work
    (work / "staged.txt").write_text("staged\n", encoding="utf-8")
    git(work, "add", "staged.txt")
    def state():
        return (git(work, "rev-parse", "HEAD"), git(work, "status", "--porcelain"),
                git(history.repo.origin, "for-each-ref"))
    before = state()

    ran = history.run("7", base)

    assert ran.status == 0, said(ran)
    assert state() == before


def test_in_spec_mode_the_specs_own_branch_is_read(history):
    on_files(history.repo, "spec")
    history.move_to("spec/local-tracker")
    base = history.commit("The tickets of spec 7",
                          files={**four_tickets(), FOLDER + "/spec.md": spec_file(branch="spec/local-tracker")})
    read = history.commit("Read", ["Ticket: 7/1"])

    ran = history.run("7", base)

    assert ran.status == 0, said(ran)
    assert printed(ran) == [read]


def test_a_base_that_is_no_commit_is_turned_down(history):
    history.commit("The tickets of spec 7", files=four_tickets())

    ran = history.run("7", "not-a-commit")

    assert ran.status == 1
    assert "not-a-commit is not a commit" in ran.err


class SubIssues:
    def __init__(self, runner, spec, tickets, branch=""):
        self.runner = runner
        self.spec = spec
        self.tickets = tickets
        self.branch = branch
        self.unanswered = []
        runner.stub("gh", does=self.answer)

    # Only the reads are answered, so a write shows up here and fails the command too.
    def answer(self):
        called = self.runner.calls[-1][1:]
        if called[:2] == ["auth", "status"]:
            return Ran(0, "", "")
        if called[:2] == ["repo", "view"]:
            return Ran(0, "owner/repo\n", "")
        if called[:2] == ["api", "user"]:
            return Ran(0, "me\n", "")
        if called[:2] == ["api", "--paginate"] and called[2] == \
                "repos/owner/repo/issues/{}/sub_issues".format(self.spec):
            return Ran(0, "".join(ticket + "\n" for ticket in self.tickets), "")
        if called[1:] == ["repos/owner/repo/issues/{}".format(self.spec), "--jq", ".body"]:
            return Ran(0, "## Branch\n\n{}\n\n## Problem Statement\n".format(self.branch), "")
        self.unanswered.append(" ".join(called))
        return Ran(1, "", "no answer\n")


def on_github(repo, target="main"):
    path = repo.work / LOOP_FILE
    path.write_text(json.dumps({"tracker": "github", "target-branch": target}), encoding="utf-8")


def test_with_github_the_commits_that_name_the_specs_sub_issues_are_printed_and_no_other(history):
    on_github(history.repo)
    SubIssues(history.runner, "468", ["469", "470", "471"])
    base = history.commit("Spec 468 starts")
    read = history.commit("Read", ["Ticket: #469"])
    history.commit("A hand fix")
    history.commit("Another spec's work", ["Ticket: #480"])
    gap = history.commit("Fill the gap", ["Ticket: #471"])

    ran = history.run("468", base)

    assert ran.status == 0, said(ran)
    assert printed(ran) == [read, gap]


def test_with_github_nothing_but_reads_reaches_gh(history):
    on_github(history.repo)
    issues = SubIssues(history.runner, "468", ["469"])
    base = history.commit("Spec 468 starts")
    history.commit("Read", ["Ticket: #469"])

    history.run("468", base)

    assert issues.unanswered == []


def test_with_github_in_spec_mode_the_branch_the_spec_names_is_read(history):
    on_github(history.repo, "spec")
    SubIssues(history.runner, "468", ["469"], branch="spec/pull-request")
    base = history.commit("Spec 468 starts")
    history.move_to("spec/pull-request")
    read = history.commit("Read", ["Ticket: #469"])
    history.move_to("main")
    history.commit("On main", ["Ticket: #469"])

    ran = history.run("468", base)

    assert ran.status == 0, said(ran)
    assert printed(ran) == [read]


def test_the_command_runs_from_the_plugins_bin_folder(history):
    base = history.commit("The tickets of spec 7", files=four_tickets())
    read = history.commit("Read", ["Ticket: 7/1"])

    ran = launch("spec-commits", "7", base, where=history.repo.work)

    assert ran.status == 0, said(ran)
    assert printed(ran) == [read]
