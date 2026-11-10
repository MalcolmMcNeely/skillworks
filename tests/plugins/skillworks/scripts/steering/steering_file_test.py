# Driven against a bare origin, so the Steering branch is read from the local origin/skillworks/steering a fetch left.

import contextlib
import io

import pytest

from conftest import Ran, Repo, git, launch
from runner import Subprocess
from steering import steering_file

STEERING = "skillworks/steering"
SURFACES = "docs/agents/surfaces.md"


class Work:
    def __init__(self, repo):
        self.repo = repo

    def on_steering(self, name, text):
        git(self.repo.work, "switch", "--quiet", "-c", STEERING)
        (self.repo.work / name).parent.mkdir(parents=True, exist_ok=True)
        self.repo.write_commit(self.repo.work, name, text, "Steering")
        git(self.repo.work, "push", "--quiet", "-u", "origin", STEERING)
        git(self.repo.work, "switch", "--quiet", "main")

    def on_disk(self, name, text):
        path = self.repo.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def run(self, *argv, where=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.chdir(where or self.repo.work):
            status = steering_file.main(list(argv), Subprocess(), out, err)
        return Ran(status, out.getvalue(), err.getvalue())


@pytest.fixture
def work(tmp_path):
    return Work(Repo(tmp_path))


def test_a_file_on_disk_is_printed_as_it_is_on_disk(work):
    work.on_disk(SURFACES, "# Surfaces\n\nThe disk copy.\n")

    ran = work.run(SURFACES)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe disk copy.\n"), ran.err


def test_a_file_missing_on_disk_is_printed_from_the_steering_branch(work):
    work.on_steering(SURFACES, "# Surfaces\n\nThe Steering copy.")

    ran = work.run(SURFACES)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe Steering copy.\n"), ran.err


def test_a_file_on_disk_and_on_the_steering_branch_is_printed_from_disk(work):
    work.on_steering(SURFACES, "# Surfaces\n\nThe Steering copy.")
    work.on_disk(SURFACES, "# Surfaces\n\nThe disk copy.\n")

    ran = work.run(SURFACES)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe disk copy.\n"), ran.err


def test_a_file_in_neither_place_prints_nothing_and_fails_with_one_line(work):
    work.on_steering("docs/agents/loop.json", "{}")

    ran = work.run(SURFACES)

    assert (ran.status != 0, ran.out, len(ran.err.splitlines())) == (True, "", 1), ran.err


def test_a_steering_change_on_origin_is_not_read_until_a_fetch_brings_it(work):
    work.on_steering(SURFACES, "# Surfaces\n\nThe Steering copy.")
    other = work.repo.other_checkout()
    git(other, "switch", "--quiet", STEERING)
    work.repo.write_commit(other, SURFACES, "A change made on another machine.", "Another machine")
    git(other, "push", "--quiet", "origin", STEERING)

    ran = work.run(SURFACES)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe Steering copy.\n"), ran.err


def test_a_path_is_read_from_the_repo_root_whatever_folder_the_caller_is_in(work):
    work.on_steering(SURFACES, "# Surfaces\n\nThe Steering copy.")
    (work.repo.work / "src").mkdir()

    ran = work.run(SURFACES, where=work.repo.work / "src")

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe Steering copy.\n"), ran.err


def test_the_command_prints_the_steering_copy_to_the_caller(work):
    work.on_steering(SURFACES, "# Surfaces\n\nThe Steering copy.")

    ran = launch("steering-file", SURFACES, where=work.repo.work)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe Steering copy.\n"), ran.err
