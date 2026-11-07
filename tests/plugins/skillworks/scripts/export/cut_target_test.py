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


def test_the_target_branch_is_cut_from_the_moved_steering_branch_pushed_and_checked_out(work):
    work.commit("feature.txt", "the team's newest work", "The team's newest work")
    work.start_export_branch()

    ran = work.run()

    assert ran.status == 0, said(ran)
    assert (work.on_origin(TARGET), work.head(), git(work.repo.work, "branch", "--show-current").strip()) == (
        work.on_origin(STEERING),) * 2 + (TARGET,)


def test_a_steering_branch_whose_rebase_conflicts_is_left_as_it_was_and_each_conflicting_file_is_named(work):
    before = work.on_origin(STEERING)
    work.commit(LOOP, '{"export": false}', "The team's own loop file")
    work.commit("notes.txt", "the team's notes", "The team's notes")
    work.start_export_branch()

    ran = work.run()

    assert (ran.status, LOOP in ran.err, work.on_origin(STEERING), work.head(STEERING),
            work.has_on_origin(TARGET), git(work.repo.work, "branch", "--show-current").strip()) == (
        1, True, before, before, False, EXPORT), said(ran)


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


def test_the_command_cuts_the_target_branch_from_the_branch_the_caller_is_on(work):
    work.start_export_branch()

    ran = launch("cut-target-branch", where=work.repo.work)

    assert (ran.status, work.on_origin(TARGET)) == (0, work.on_origin(STEERING)), said(ran)
