#
# The fetch that looks again, read against a throwaway repository.

import io

from conftest import git
from fetch_origin import fetch_origin

# What git says to the loop that lost the race for the ref.
REFUSED = "error: cannot lock ref 'refs/remotes/origin/main': is at 1b1e78e but expected 972ef6b"

UNREACHABLE = "fatal: could not read from remote repository"

# Enough of the command to tell it from a temporary path that holds the word fetch.
FETCH = "fetch --quiet origin"


def run_fetch(repo, runner):
    err = io.StringIO()
    worked = fetch_origin(runner, repo.work.as_posix(), err)
    return worked, err.getvalue()


def fetch_tries(runner):
    return len(runner.built(FETCH))


def head(where, name):
    return git(where, "rev-parse", name).strip()


def test_a_fetch_that_works_is_asked_once(repo, runner):
    repo.advance_origin("one")

    worked, _ = run_fetch(repo, runner)

    assert worked
    assert fetch_tries(runner) == 1


def test_a_fetch_that_works_says_nothing(repo, runner):
    worked, said = run_fetch(repo, runner)

    assert worked
    assert said == ""


def test_a_refused_ref_is_looked_at_again(repo, runner):
    repo.advance_origin("two")
    runner.refuse(FETCH, REFUSED, times=2)

    worked, _ = run_fetch(repo, runner)

    assert worked
    assert fetch_tries(runner) == 3


def test_a_refused_ref_still_brings_the_commit_down(repo, runner):
    repo.advance_origin("three")
    # Read off the remote, so the two sides of the comparison cannot move together.
    pushed = head(repo.origin, "main")
    runner.refuse(FETCH, REFUSED, times=1)

    worked, _ = run_fetch(repo, runner)

    assert worked
    assert head(repo.work, "origin/main") == pushed


def test_a_ref_that_never_frees_up_stops(repo, runner):
    runner.refuse(FETCH, REFUSED)

    worked, said = run_fetch(repo, runner)

    assert not worked
    assert fetch_tries(runner) == 5
    # A caller is told the reason git gave, and never a summary of it.
    assert said == REFUSED + "\n"


def test_an_origin_that_cannot_be_reached_is_asked_once(repo, runner):
    runner.refuse(FETCH, UNREACHABLE)

    worked, said = run_fetch(repo, runner)

    assert not worked
    assert fetch_tries(runner) == 1
    assert said == UNREACHABLE + "\n"
