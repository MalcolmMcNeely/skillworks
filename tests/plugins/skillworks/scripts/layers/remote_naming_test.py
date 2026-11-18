import contextlib
import io
import json
import os

import pytest

from conftest import Ran, RemoteSteering, Repo, git, launch, sidecar_steering
from layers import remote_naming
from runner import Subprocess
from steering import steering_file


class Setup:
    def __init__(self, repo, remote, home):
        self.repo = repo
        self.remote = remote
        self.home = home

    @property
    def origin(self):
        return self.repo.origin.as_posix()

    @property
    def user_file(self):
        return self.home / ".skillworks" / "remote-steering.json"

    def holds(self, settings):
        self.remote.name_in(self.home, settings)

    def held(self):
        return json.loads(self.user_file.read_text(encoding="utf-8"))

    def answer(self, *argv, where=None):
        out, err = io.StringIO(), io.StringIO()
        status = remote_naming.main([(where or self.repo.work).as_posix(), *argv], Subprocess(), out, err,
                                    home=self.home)
        return Ran(status, out.getvalue(), err.getvalue())


@pytest.fixture
def setup(tmp_path):
    return Setup(Repo(tmp_path), RemoteSteering(tmp_path), tmp_path / "home")


def test_with_no_user_file_a_yes_with_a_url_writes_the_url_and_the_repos_origin(setup):
    ran = setup.answer("yes", setup.remote.url)

    assert (ran.status, setup.held()) == (0, {"url": setup.remote.url, "repos": [setup.origin]}), ran.err


OTHER_REPO = "https://example.invalid/another-client.git"


def test_with_a_url_already_set_a_yes_with_no_url_adds_the_origin_beside_the_repos_listed(setup):
    setup.holds({"url": setup.remote.url, "repos": [OTHER_REPO]})

    ran = setup.answer("yes")

    assert (ran.status, setup.held()) == (0, {"url": setup.remote.url, "repos": [OTHER_REPO, setup.origin]}), ran.err


def test_a_yes_for_a_repo_already_on_the_list_leaves_the_user_file_as_it_was(setup):
    setup.holds({"url": setup.remote.url, "repos": [setup.origin, OTHER_REPO]})
    before = setup.user_file.read_bytes()

    ran = setup.answer("yes")

    assert (ran.status, setup.user_file.read_bytes()) == (0, before), ran.err


@pytest.mark.parametrize("settings", [None, {"url": "file:///somewhere/method.git", "repos": [OTHER_REPO]}])
def test_a_no_leaves_the_user_file_as_it_was(setup, settings):
    if settings is not None:
        setup.holds(settings)
    before = setup.user_file.read_bytes() if settings is not None else None

    ran = setup.answer("no")

    after = setup.user_file.read_bytes() if setup.user_file.exists() else None
    assert (ran.status, after) == (0, before), ran.err


def test_a_yes_with_no_url_set_and_none_given_asks_for_the_url_and_writes_nothing(setup):
    ran = setup.answer("yes")

    assert (ran.status, ran.out.startswith("asks the URL"), setup.user_file.exists()) == (0, True, False), ran.err


def test_a_yes_with_a_url_other_than_the_one_set_is_refused_and_writes_nothing(setup):
    setup.holds({"url": setup.remote.url, "repos": [OTHER_REPO]})
    before = setup.user_file.read_bytes()

    ran = setup.answer("yes", "file:///somewhere/else.git")

    assert (ran.status, setup.user_file.read_bytes(), setup.remote.url in ran.err) == (1, before, True), ran.err


def test_a_yes_in_a_repo_with_no_origin_is_refused_and_writes_nothing(setup):
    git(setup.repo.work, "remote", "remove", "origin")

    ran = setup.answer("yes", setup.remote.url)

    assert (ran.status, ran.err.startswith("FAIL  this repo has no origin"), setup.user_file.exists()) == (
        1, True, False), ran.err


def test_a_yes_over_a_user_file_that_is_not_json_is_refused_and_leaves_it_as_it_was(setup):
    setup.user_file.parent.mkdir(parents=True)
    setup.user_file.write_text("{not json", encoding="utf-8")

    ran = setup.answer("yes", setup.remote.url)

    assert (ran.status, setup.user_file.read_text(encoding="utf-8")) == (1, "{not json"), ran.err


def every_file(root):
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


@pytest.mark.parametrize("answers", [[["yes", "URL"]], [["no"]], [["yes", "URL"], ["yes"]], [["yes"]]])
def test_after_any_answer_the_repo_and_the_sidecar_hold_no_file_url_or_commit_of_the_remote(setup, answers):
    sidecar = sidecar_steering(setup.repo)
    before = (every_file(setup.repo.work), every_file(sidecar))

    for answer in answers:
        setup.answer(*[setup.remote.url if part == "URL" else part for part in answer])

    assert (every_file(setup.repo.work), every_file(sidecar)) == before


METHOD = "docs/skillworks/method.md"


def test_after_a_yes_steering_file_in_that_repo_reads_the_remote(setup):
    setup.remote.push(METHOD, "# Method\n\nThe remote's way of working.\n")
    setup.answer("yes", setup.remote.url)
    out, err = io.StringIO(), io.StringIO()

    with contextlib.chdir(setup.repo.work):
        status = steering_file.main([METHOD], Subprocess(), out, err, home=setup.home)

    assert (status, out.getvalue()) == (0, "# Method\n\nThe remote's way of working.\n"), err.getvalue()


def test_the_command_writes_the_user_file_in_the_home_it_runs_under(setup):
    env = dict(os.environ, HOME=str(setup.home), USERPROFILE=str(setup.home))

    ran = launch("set-remote-steering", "yes", setup.remote.url, where=setup.repo.work, env=env)

    assert (ran.status, setup.held()) == (0, {"url": setup.remote.url, "repos": [setup.origin]}), ran.err
