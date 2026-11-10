# Driven through main against a bare origin, so each case reads the branches as the loop later does.

import contextlib
import io
import subprocess

import pytest

from conftest import Ran, Repo, git, launch
from export import cut_target

STEERING = "skillworks/steering"
EXPORT = "feature/PROJ-12/slug"
TARGET = "skillworks/spec/" + EXPORT
LOOP = "docs/agents/loop.json"


class Work:
    def __init__(self, repo, runner):
        self.repo = repo
        self.runner = runner

    def commit(self, name, text, message):
        (self.repo.work / name).parent.mkdir(parents=True, exist_ok=True)
        self.repo.write_commit(self.repo.work, name, text, message)
        return self.head()

    def head(self, ref="HEAD"):
        return git(self.repo.work, "rev-parse", ref).strip()

    def on_origin(self, branch):
        return git(self.repo.origin, "rev-parse", "refs/heads/" + branch).strip()

    def has_on_origin(self, branch):
        return subprocess.run(["git", "-C", self.repo.origin.as_posix(), "rev-parse", "--verify", "--quiet",
                               "refs/heads/" + branch], capture_output=True).returncode == 0

    def make_steering(self):
        git(self.repo.work, "switch", "--quiet", "-c", STEERING)
        self.commit(LOOP, '{"export": true}', "Steering")
        git(self.repo.work, "push", "--quiet", "origin", STEERING)
        git(self.repo.work, "switch", "--quiet", "main")

    def start_export_branch(self):
        git(self.repo.work, "switch", "--quiet", "-c", EXPORT)
        return self.head()

    def run(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.chdir(self.repo.work):
            status = cut_target.main(list(argv), self.runner, out, err)
        return Ran(status, out.getvalue(), err.getvalue())


@pytest.fixture
def work(tmp_path, runner):
    made = Work(Repo(tmp_path), runner)
    made.make_steering()
    return made


def said(ran):
    return ran.out + ran.err


def test_a_steering_branch_behind_the_export_branch_is_moved_onto_its_commit_and_pushed(work):
    work.commit("feature.txt", "the team's newest work", "The team's newest work")
    tip = work.start_export_branch()

    ran = work.run()

    assert ran.status == 0, said(ran)
    moved = work.on_origin(STEERING)
    assert (git(work.repo.origin, "rev-parse", moved + "^").strip(),
            git(work.repo.origin, "log", "-1", "--format=%s", moved).strip()) == (tip, "Steering")


def test_the_target_branch_on_origin_starts_at_the_moved_steering_branch(work):
    work.commit("feature.txt", "the team's newest work", "The team's newest work")
    work.start_export_branch()

    ran = work.run()

    assert ran.status == 0, said(ran)
    assert work.on_origin(TARGET) == work.on_origin(STEERING)


def test_the_session_is_left_on_the_target_branch(work):
    work.commit("feature.txt", "the team's newest work", "The team's newest work")
    work.start_export_branch()

    ran = work.run()

    assert ran.status == 0, said(ran)
    assert git(work.repo.work, "branch", "--show-current").strip() == TARGET


def given_a_steering_rebase_that_conflicts(work):
    before = work.on_origin(STEERING)
    work.commit(LOOP, '{"export": false}', "The team's own loop file")
    work.commit("notes.txt", "the team's notes", "The team's notes")
    work.start_export_branch()
    return before


def test_a_conflicting_steering_rebase_leaves_the_steering_branch_as_it_was(work):
    before = given_a_steering_rebase_that_conflicts(work)

    ran = work.run()

    assert (work.on_origin(STEERING), work.head(STEERING)) == (before, before), said(ran)


def test_a_conflicting_steering_rebase_cuts_no_target_branch(work):
    given_a_steering_rebase_that_conflicts(work)

    ran = work.run()

    assert (work.has_on_origin(TARGET), git(work.repo.work, "branch", "--show-current").strip()) == (
        False, EXPORT), said(ran)


def test_a_conflicting_steering_rebase_names_each_conflicting_file(work):
    given_a_steering_rebase_that_conflicts(work)

    ran = work.run()

    assert (ran.status, LOOP in ran.err) == (1, True), said(ran)


def test_the_uncommitted_file_the_grill_just_settled_comes_along_onto_the_target_branch(work):
    work.start_export_branch()
    (work.repo.work / "CONTEXT.md").write_text("# Words\n", encoding="utf-8")

    ran = work.run()

    assert ran.status == 0, said(ran)
    assert (git(work.repo.work, "branch", "--show-current").strip(),
            git(work.repo.work, "status", "--porcelain").strip()) == (TARGET, "?? CONTEXT.md")


def test_a_branch_under_the_plugins_own_prefix_is_refused_as_an_export_branch(work):
    git(work.repo.work, "switch", "--quiet", "-c", "skillworks/spec/feature")

    ran = work.run()

    assert (ran.status, "skillworks/" in ran.err) == (1, True), said(ran)


def test_the_default_branch_is_refused_with_what_to_do(work):
    ran = work.run()

    assert (ran.status, "Make a branch of your own, switch to it, and start again" in ran.err) == (1, True), said(ran)


def test_the_default_branch_cuts_and_pushes_nothing(work):
    before = work.on_origin(STEERING)

    ran = work.run()

    assert (work.on_origin(STEERING), work.has_on_origin("skillworks/spec/main"),
            git(work.repo.work, "branch", "--show-current").strip()) == (before, False, "main"), said(ran)


def test_the_default_branch_is_the_one_origin_head_names(work):
    git(work.repo.work, "switch", "--quiet", "-c", "trunk")
    git(work.repo.work, "push", "--quiet", "origin", "trunk")
    git(work.repo.work, "remote", "set-head", "origin", "trunk")

    ran = work.run()

    assert (ran.status, "trunk is the default branch" in ran.err) == (1, True), said(ran)


def test_an_origin_that_names_no_default_branch_is_refused_with_how_to_name_it(work):
    work.start_export_branch()
    git(work.repo.origin, "symbolic-ref", "HEAD", "refs/heads/gone")

    ran = work.run()

    assert (ran.status, "git remote set-head origin --auto" in ran.err) == (1, True), said(ran)


def test_the_default_branch_is_found_with_no_gh_call(work, runner):
    work.run()

    assert runner.started("gh") == []


def test_no_branch_is_refused_with_what_to_do(work):
    git(work.repo.work, "switch", "--quiet", "--detach")

    ran = work.run()

    assert (ran.status, "Make a branch of your own, switch to it, and start again" in ran.err) == (1, True), said(ran)


def test_a_branch_under_the_plugins_own_prefix_is_refused_with_what_to_do(work):
    git(work.repo.work, "switch", "--quiet", "-c", "skillworks/spec/feature")

    ran = work.run()

    assert "Make a branch of your own, switch to it, and start again" in ran.err, said(ran)


def test_the_command_cuts_the_target_branch_from_the_branch_the_caller_is_on(work):
    work.start_export_branch()

    ran = launch("cut-target-branch", where=work.repo.work)

    assert (ran.status, work.on_origin(TARGET)) == (0, work.on_origin(STEERING)), said(ran)
