import contextlib
import io
import json
from pathlib import Path

import pytest

from branches import spec_branch
from clock.held_clock import HeldClock
from conftest import Ran, Repo, git, launch
from runner import Subprocess
from sidecar.sidecar import Sidecar
from steering.target_branch import LOOP_FILE

NAME = "feature/PROJ-12/many-specs"


def write_loop(top, tracker):
    path = Path(top) / LOOP_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tracker": tracker, "target-branch": "pr"}), encoding="utf-8")


class Work:
    def __init__(self, repo, runner):
        self.repo = repo
        self.runner = runner

    def run(self, *argv, where=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.chdir(where or self.repo.work):
            status = spec_branch.main(list(argv), self.runner, out, err)
        return Ran(status, out.getvalue(), err.getvalue())

    def on_origin(self):
        said = git(self.repo.origin, "for-each-ref", "--format=%(refname:strip=2)", "refs/heads/")
        return sorted(said.split())

    def tip_on_origin(self, branch):
        return git(self.repo.origin, "rev-parse", branch).strip()

    def checkout_branch(self):
        return git(self.repo.work, "branch", "--show-current").strip()

    def grill(self, name):
        return self.repo.work / ".spec-loop" / "grill" / name


@pytest.fixture
def work(tmp_path, runner):
    repo = Repo(tmp_path)
    write_loop(repo.work, "files")
    return Work(repo, runner)


def said(ran):
    return ran.out + ran.err


def open_spec_in_the_sidecar(repo, branch, status="open"):
    text = "---\nstatus: {}\nbranch: {}\n---\n\n# SPEC: Many specs\n".format(status, branch)
    spec = ".specs/0007-many-specs/spec.md"

    def write(folder):
        (folder / spec).parent.mkdir(parents=True)
        (folder / spec).write_text(text, encoding="utf-8", newline="\n")
    Sidecar.of(Subprocess(), repo.work, HeldClock()).write("Tracker state", write)


class Issues:
    def __init__(self, runner):
        self.runner = runner
        self.specs = []
        runner.stub("gh", does=self.answer)

    def answer(self):
        called = self.runner.calls[-1][1:]
        if called[:2] == ["repo", "view"]:
            return Ran(0, "owner/repo\n", "")
        if called[:2] == ["api", "user"]:
            return Ran(0, "me\n", "")
        if called[:1] == ["api"] and any("labels=ready-for-agent" in arg for arg in called):
            return Ran(0, "".join(json.dumps([number, body]) + "\n" for number, body in self.specs), "")
        return None


@pytest.fixture
def on_github(work, runner):
    write_loop(work.repo.work, "github")
    return Issues(runner)


def test_a_free_name_is_made_on_origin_at_the_default_branchs_tip(work):
    ran = work.run(NAME)

    assert (ran.status, work.tip_on_origin(NAME)) == (0, work.tip_on_origin("main")), said(ran)


def test_a_free_name_opens_the_grill_worktree_on_the_new_branch(work):
    ran = work.run(NAME)

    opened = git(work.grill(NAME), "branch", "--show-current").strip()
    assert (ran.status, opened, ran.out) == (0, NAME, work.grill(NAME).as_posix() + "\n"), said(ran)


def test_the_grill_worktree_pushes_to_the_new_branch_on_origin(work):
    work.run(NAME)

    upstream = git(work.grill(NAME), "rev-parse", "--abbrev-ref", "@{upstream}").strip()
    assert upstream == "origin/" + NAME


def test_the_main_checkout_stays_on_the_default_branch(work):
    work.run(NAME)

    assert work.checkout_branch() == "main"


def test_from_another_worktree_the_grill_worktree_opens_under_the_main_checkout(work):
    other = work.repo.root / "elsewhere"
    git(work.repo.work, "worktree", "add", "--quiet", "--detach", other.as_posix())

    ran = work.run(NAME, where=other)

    assert (ran.status, work.grill(NAME).is_dir()) == (0, True), said(ran)


def test_the_tip_is_origins_even_when_the_checkout_is_behind_it(work):
    work.repo.advance_origin("ahead")

    work.run(NAME)

    assert work.tip_on_origin(NAME) == work.tip_on_origin("main")


def test_the_default_branch_is_refused_and_nothing_is_pushed(work):
    ran = work.run("main")

    assert (ran.status, "main is the default branch" in ran.err, work.on_origin()) == (1, True, ["main"]), said(ran)


def test_a_name_already_on_origin_is_refused_and_nothing_is_pushed(work):
    git(work.repo.work, "push", "--quiet", "origin", "main:" + NAME)
    before = work.tip_on_origin(NAME)
    work.repo.advance_origin("ahead")

    ran = work.run(NAME)

    assert (ran.status, "already on origin" in ran.err, work.tip_on_origin(NAME)) == (1, True, before), said(ran)


def test_a_name_an_open_spec_in_the_sidecar_names_is_refused_and_nothing_is_pushed(work):
    open_spec_in_the_sidecar(work.repo, NAME)

    ran = work.run(NAME)

    assert (ran.status, "spec 7" in ran.err, work.on_origin()) == (1, True, ["main"]), said(ran)


def test_a_name_only_a_closed_spec_in_the_sidecar_names_is_made(work):
    open_spec_in_the_sidecar(work.repo, NAME, status="closed")

    ran = work.run(NAME)

    assert (ran.status, NAME in work.on_origin()) == (0, True), said(ran)


def test_a_name_an_open_spec_issue_names_is_refused_and_nothing_is_pushed(work, on_github):
    on_github.specs.append((639, "<!-- skillworks-spec sha256:00 -->\n\n## Branch\n\n`{}`\n".format(NAME)))

    ran = work.run(NAME)

    assert (ran.status, "spec #639" in ran.err, work.on_origin()) == (1, True, ["main"]), said(ran)


def test_with_the_github_tracker_a_name_no_open_spec_names_is_made(work, on_github):
    on_github.specs.append((639, "<!-- skillworks-spec sha256:00 -->\n\n## Branch\n\n`other`\n"))
    on_github.specs.append((640, "## Problem Statement\n\nNo branch here.\n"))

    ran = work.run(NAME)

    assert (ran.status, NAME in work.on_origin()) == (0, True), said(ran)


def test_a_name_git_would_not_take_is_refused_and_nothing_is_pushed(work):
    ran = work.run("two..dots")

    assert (ran.status, work.on_origin()) == (1, ["main"]), said(ran)


def test_a_local_branch_of_the_name_is_refused_and_nothing_is_pushed(work):
    git(work.repo.work, "branch", NAME)

    ran = work.run(NAME)

    assert (ran.status, "already a branch" in ran.err, work.on_origin()) == (1, True, ["main"]), said(ran)


def test_a_refusal_says_that_nothing_was_pushed(work):
    ran = work.run("main")

    assert "Nothing was pushed." in ran.err, said(ran)


def test_no_name_is_refused_with_the_usage(work):
    ran = work.run()

    assert (ran.status, ran.err) == (64, "usage: spec-branch <name>\n"), said(ran)


def test_the_command_runs_from_the_plugins_bin_folder(work):
    ran = launch("spec-branch", NAME, where=work.repo.work)

    assert (ran.status, NAME in work.on_origin()) == (0, True), said(ran)
