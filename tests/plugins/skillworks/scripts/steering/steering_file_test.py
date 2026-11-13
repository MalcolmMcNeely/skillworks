# Driven against a bare origin that holds a skillworks/steering branch, so a read that reached for it would show.

import contextlib
import io

import pytest

from conftest import Ran, Repo, git, launch
from runner import Subprocess
from steering import steering_file

OLD_STEERING_BRANCH = "skillworks/steering"
SURFACES = "docs/skillworks/surfaces.md"
RULES = "docs/skillworks/rules/"


class Work:
    def __init__(self, repo):
        self.repo = repo

    def on_old_steering_branch(self, *files):
        git(self.repo.work, "switch", "--quiet", "-c", OLD_STEERING_BRANCH)
        for name, text in zip(files[::2], files[1::2]):
            (self.repo.work / name).parent.mkdir(parents=True, exist_ok=True)
            self.repo.write_commit(self.repo.work, name, text, "Steering")
        git(self.repo.work, "push", "--quiet", "-u", "origin", OLD_STEERING_BRANCH)
        git(self.repo.work, "switch", "--quiet", "main")

    def on_disk(self, name, text):
        path = self.repo.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def in_sidecar(self, name, text):
        path = self.repo.work.parent / "work-skillworks" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def nested_worktree(self):
        tree = self.repo.work / ".spec-loop" / "nested" / "job"
        git(self.repo.work, "worktree", "add", "--quiet", "-b", "job", tree.as_posix())
        return tree

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


def test_a_file_missing_on_disk_is_missing_even_when_an_old_steering_branch_holds_it(work):
    work.on_old_steering_branch(SURFACES, "# Surfaces\n\nThe Steering copy.")

    ran = work.run(SURFACES)

    assert (ran.status != 0, ran.out, ran.err) == (True, "", "FAIL  {} is missing.\n".format(SURFACES))


def test_a_file_on_disk_is_printed_from_disk_when_an_old_steering_branch_holds_it_too(work):
    work.on_old_steering_branch(SURFACES, "# Surfaces\n\nThe Steering copy.")
    work.on_disk(SURFACES, "# Surfaces\n\nThe disk copy.\n")

    ran = work.run(SURFACES)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe disk copy.\n"), ran.err


def test_a_folder_on_disk_prints_the_path_of_each_file_in_it(work):
    work.on_disk(RULES + "words.md", "# Words")
    work.on_disk(RULES + "comments.md", "# Comments")

    ran = work.run(RULES)

    assert (ran.status, ran.out) == (0, RULES + "comments.md\n" + RULES + "words.md\n"), ran.err


def test_a_folder_missing_on_disk_is_missing_even_when_an_old_steering_branch_holds_it(work):
    work.on_old_steering_branch(RULES + "words.md", "# Words")

    ran = work.run(RULES)

    assert (ran.status != 0, ran.out, ran.err) == (True, "", "FAIL  {} is missing.\n".format(RULES))


def test_a_path_is_read_from_the_repo_root_whatever_folder_the_caller_is_in(work):
    work.on_disk(SURFACES, "# Surfaces\n\nThe disk copy.\n")
    (work.repo.work / "src").mkdir()

    ran = work.run(SURFACES, where=work.repo.work / "src")

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe disk copy.\n"), ran.err


LOOP = "docs/skillworks/loop.json"


def test_with_loop_json_in_the_sidecar_the_sidecars_copy_is_printed_from_the_main_checkout(work):
    work.on_disk(LOOP, '{"target-branch": "main"}\n')
    work.in_sidecar(LOOP, '{"target-branch": "pr"}\n')

    ran = work.run(LOOP)

    assert (ran.status, ran.out) == (0, '{"target-branch": "pr"}\n'), ran.err


def test_with_loop_json_in_the_sidecar_the_sidecars_copy_is_printed_from_a_worktree(work):
    tree = work.nested_worktree()
    work.in_sidecar(LOOP, '{"target-branch": "pr"}\n')

    ran = work.run(LOOP, where=tree)

    assert (ran.status, ran.out) == (0, '{"target-branch": "pr"}\n'), ran.err


def test_with_loop_json_in_the_sidecar_a_steering_file_is_read_from_the_sidecar_and_not_the_repo(work):
    work.on_disk(SURFACES, "# Surfaces\n\nThe repo copy.\n")
    work.in_sidecar(LOOP, '{"target-branch": "pr"}\n')
    work.in_sidecar(SURFACES, "# Surfaces\n\nThe Sidecar copy.\n")

    ran = work.run(SURFACES)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe Sidecar copy.\n"), ran.err


def test_a_sidecar_with_no_loop_json_leaves_every_read_on_the_repo(work):
    work.on_disk(SURFACES, "# Surfaces\n\nThe repo copy.\n")
    work.in_sidecar(SURFACES, "# Surfaces\n\nThe Sidecar copy.\n")

    ran = work.run(SURFACES)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe repo copy.\n"), ran.err


def test_the_command_prints_the_sidecars_copy_to_the_caller_from_a_worktree(work):
    tree = work.nested_worktree()
    work.in_sidecar(LOOP, '{"target-branch": "pr"}\n')

    ran = launch("steering-file", LOOP, where=tree)

    assert (ran.status, ran.out) == (0, '{"target-branch": "pr"}\n'), ran.err


def test_the_command_prints_the_disk_copy_to_the_caller(work):
    work.on_disk(SURFACES, "# Surfaces\n\nThe disk copy.\n")

    ran = launch("steering-file", SURFACES, where=work.repo.work)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe disk copy.\n"), ran.err
