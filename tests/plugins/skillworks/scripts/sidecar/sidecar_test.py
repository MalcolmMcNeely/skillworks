import threading

import pytest

from clock.held_clock import HeldClock
from conftest import git
from runner import Subprocess
from sidecar.locator import sidecar_of
from sidecar.sidecar import WAIT_SECONDS, Sidecar


@pytest.fixture
def nested(repo):
    tree = repo.work / ".spec-loop" / "nested" / "job"
    git(repo.work, "worktree", "add", "--quiet", "-b", "job", tree.as_posix())
    return tree


def named(repo):
    return repo.work.parent / "work-skillworks"


def log(sidecar):
    return git(sidecar, "log", "--format=%s").splitlines()


def write_file(name, text):
    def change(folder):
        (folder / name).write_text(text, encoding="utf-8", newline="\n")
    return change


def test_the_locator_names_one_folder_beside_the_main_checkout_from_it_and_from_a_nested_worktree(
        repo, nested):
    assert {sidecar_of(Subprocess(), where) for where in (repo.work, nested)} == {named(repo)}


def test_the_first_write_makes_the_sidecar_a_git_repo_with_no_remote(repo, nested):
    Sidecar.of(Subprocess(), nested, HeldClock()).write("First", write_file("one.md", "one"))

    assert (git(named(repo), "rev-parse", "--is-inside-work-tree").strip(),
            git(named(repo), "remote")) == ("true", "")


def test_each_write_is_one_commit_in_the_sidecars_history(repo):
    sidecar = Sidecar.of(Subprocess(), repo.work, HeldClock())

    sidecar.write("First", write_file("one.md", "one"))
    sidecar.write("Second", write_file("two.md", "two"))

    assert log(named(repo)) == ["Second", "First"]


def test_two_writers_at_once_both_commit_one_after_the_other(repo, nested):
    clock = HeldClock()
    first, second = (Sidecar.of(Subprocess(), where, clock) for where in (repo.work, nested))
    holds, let_go = threading.Event(), threading.Event()

    def held_open(folder):
        write_file("one.md", "one")(folder)
        holds.set()
        let_go.wait()

    first_writer = threading.Thread(target=first.write, args=("First", held_open))
    second_writer = threading.Thread(target=second.write, args=("Second", write_file("two.md", "two")))
    first_writer.start()
    holds.wait()
    second_writer.start()
    clock.repeating.wait()
    let_go.set()
    first_writer.join()
    clock.move(WAIT_SECONDS)
    second_writer.join()

    assert (log(named(repo)), sorted(path.name for path in named(repo).glob("*.md"))) == (
        ["Second", "First"], ["one.md", "two.md"])
