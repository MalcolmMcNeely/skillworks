import io

import pytest

from conftest import Ran, Repo, launch
from runner import Subprocess
from steering import show_steering

STEP_LIST = (
    "Name a step to see the Steering it reads: show-steering <step>\n"
    "\n"
    "The Grill\n"
    "  grill         Interviews you about the design, and writes the glossary and the ADRs as they settle.\n"
    "  gate          Sums up the design and waits for your yes.\n"
    "  write-spec    Writes the spec from the settled design and publishes it to the Tracker.\n"
    "\n"
    "The spec loop\n"
    "  tickets       Breaks the spec into tickets, each with the tickets that block it.\n"
    "  build         Builds one ticket test first, and leaves the change uncommitted.\n"
    "  standards     Reviews the change against the rules and the review file for standards.\n"
    "  spec          Reviews the change against what the ticket and its spec asked for.\n"
    "  architecture  Reviews where the change sits, and runs the placement checks.\n"
    "  fix           Fixes what the three reviews found, or a Suite that went red.\n"
    "  sweep         Cuts the comments the comments rule does not keep.\n"
    "  suite         Runs every check in the Suite file, with no Session.\n"
    "  finish        Commits the ticket and closes it with its Closing note.\n"
    "\n"
    "The step map: https://github.com/MalcolmMcNeely/skillworks/blob/main/docs/usage/the-loop/step-map.md\n"
)


@pytest.fixture
def repo(tmp_path):
    return Repo(tmp_path)


def show(*argv, where):
    out, err = io.StringIO(), io.StringIO()
    status = show_steering.main(list(argv), Subprocess(), out, err, str(where))
    return Ran(status, out.getvalue(), err.getvalue())


def test_with_no_step_named_the_steps_of_the_dev_loop_are_listed_by_stage(repo):
    ran = show(where=repo.work)

    assert (ran.status, ran.out) == (0, STEP_LIST), ran.err


def test_a_name_that_is_not_a_step_is_turned_down_with_the_step_list(repo):
    ran = show("biuld", where=repo.work)

    assert (ran.status != 0, ran.out) == (True, "biuld is not a step.\n\n" + STEP_LIST), ran.err


def test_a_step_named_from_a_folder_below_the_repo_root_is_found(repo):
    below = repo.work / "src" / "deep"
    below.mkdir(parents=True)

    ran = show("build", where=below)

    assert (ran.status, ran.out) == (0, STEP_LIST), ran.err


def test_a_folder_outside_a_git_repository_is_turned_down(tmp_path):
    outside = tmp_path / "loose"
    outside.mkdir()

    ran = show(where=outside)

    assert (ran.status != 0, ran.err) == (True, "FAIL  {} is not in a git repository.\n".format(outside))


def test_the_command_prints_the_step_list_to_the_caller(repo):
    ran = launch("show-steering", where=repo.work)

    assert (ran.status, ran.out) == (0, STEP_LIST), ran.err
