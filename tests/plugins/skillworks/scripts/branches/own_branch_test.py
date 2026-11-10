import contextlib
import io

import pytest

from branches import own_branch
from conftest import Ran, Repo, git, launch

DEVELOPERS = "feature/PROJ-12/slug"
WHAT_TO_DO = "Make a branch of your own, switch to it, and start again"


class Work:
    def __init__(self, repo, runner):
        self.repo = repo
        self.runner = runner

    def switch(self, *args):
        git(self.repo.work, "switch", "--quiet", *args)

    def run(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.chdir(self.repo.work):
            status = own_branch.main(list(argv), self.runner, out, err)
        return Ran(status, out.getvalue(), err.getvalue())


@pytest.fixture
def work(tmp_path, runner):
    return Work(Repo(tmp_path), runner)


def said(ran):
    return ran.out + ran.err


def test_a_developers_branch_passes_and_is_named(work):
    work.switch("-c", DEVELOPERS)

    ran = work.run()

    assert (ran.status, ran.out) == (0, DEVELOPERS + "\n"), said(ran)


def test_the_default_branch_is_refused_with_what_to_do(work):
    ran = work.run()

    assert (ran.status, "main is the default branch" in ran.err, WHAT_TO_DO in ran.err) == (1, True, True), said(ran)


def test_a_branch_under_the_loops_own_prefix_is_refused_with_what_to_do(work):
    work.switch("-c", "skillworks/spec/feature")

    ran = work.run()

    assert (ran.status, "belongs to the loop" in ran.err, WHAT_TO_DO in ran.err) == (1, True, True), said(ran)


def test_no_branch_is_refused_with_what_to_do(work):
    work.switch("--detach")

    ran = work.run()

    assert (ran.status, "on no branch" in ran.err, WHAT_TO_DO in ran.err) == (1, True, True), said(ran)


def test_a_refusal_says_that_nothing_was_written(work):
    ran = work.run()

    assert "Nothing was written." in ran.err, said(ran)


def test_the_default_branch_is_found_with_no_gh_call(work, runner):
    work.run()

    assert runner.started("gh") == []


def test_an_argument_is_refused_with_the_usage(work):
    work.switch("-c", DEVELOPERS)

    ran = work.run("main")

    assert (ran.status, ran.err) == (64, "usage: own-branch\n"), said(ran)


def test_the_command_names_the_branch_the_caller_is_on(work):
    work.switch("-c", DEVELOPERS)

    ran = launch("own-branch", where=work.repo.work)

    assert (ran.status, ran.out) == (0, DEVELOPERS + "\n"), said(ran)
