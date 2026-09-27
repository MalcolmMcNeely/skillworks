import json

import pytest

from conftest import ROOT
from stop import REFUSED, Stop
from steering.target_branch import LOOP_FILE, in_spec_mode, target_branch, target_branch_for


def write_loop(top, settings):
    path = top / LOOP_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8", newline="\n")


def test_a_branch_name_is_the_target_branch(tmp_path):
    write_loop(tmp_path, {"target-branch": "master"})

    assert target_branch(tmp_path) == "master"


def test_a_missing_loop_file_stops_and_names_the_command_that_writes_it(tmp_path):
    with pytest.raises(Stop) as stopped:
        target_branch(tmp_path)

    assert stopped.value.status == REFUSED
    assert "docs/agents/loop.json" in stopped.value.said
    assert "seed-steering" in stopped.value.said


def test_a_loop_file_with_no_target_branch_stops_and_names_the_setting(tmp_path):
    write_loop(tmp_path, {})

    with pytest.raises(Stop) as stopped:
        target_branch(tmp_path)

    assert stopped.value.status == REFUSED
    assert "target-branch" in stopped.value.said


def test_in_spec_mode_the_target_branch_is_the_branch_the_spec_names(tmp_path):
    write_loop(tmp_path, {"target-branch": "spec"})
    spec = "## Problem Statement\r\n\r\nWords.\r\n\r\n## Branch\r\n\r\n`spec/target-branch`\r\n\r\n## Solution\r\n"

    assert target_branch(tmp_path, spec) == "spec/target-branch"


def test_in_spec_mode_a_spec_that_names_no_branch_stops_and_says_so(tmp_path):
    write_loop(tmp_path, {"target-branch": "spec"})

    with pytest.raises(Stop) as stopped:
        target_branch(tmp_path, "## Problem Statement\n\nWords.\n")

    assert stopped.value.status == REFUSED
    assert "## Branch" in stopped.value.said
    assert "to-spec" in stopped.value.said


def test_in_spec_mode_no_spec_stops_and_says_one_is_needed(tmp_path):
    write_loop(tmp_path, {"target-branch": "spec"})

    with pytest.raises(Stop) as stopped:
        target_branch(tmp_path)

    assert stopped.value.status == REFUSED
    assert "no spec was given" in stopped.value.said


def test_a_branch_name_ignores_the_branch_a_spec_names(tmp_path):
    write_loop(tmp_path, {"target-branch": "master"})

    assert target_branch(tmp_path, "## Branch\n\n`spec/other`\n") == "master"


def test_spec_mode_is_told_apart_from_a_branch_name(tmp_path):
    write_loop(tmp_path, {"target-branch": "spec"})
    assert in_spec_mode(tmp_path)

    write_loop(tmp_path, {"target-branch": "master"})
    assert not in_spec_mode(tmp_path)


def test_a_missing_loop_file_stops_the_question_of_spec_mode_too(tmp_path):
    with pytest.raises(Stop) as stopped:
        in_spec_mode(tmp_path)

    assert "seed-steering" in stopped.value.said


SPEC_BODY = "## Problem Statement\n\nWords.\n\n## Branch\n\n`spec/target-branch`\n"


def test_by_hand_in_spec_mode_the_spec_is_asked_of_the_tracker_for_its_branch(tmp_path, runner):
    write_loop(tmp_path, {"target-branch": "spec"})
    runner.stub("gh", says=SPEC_BODY)

    assert target_branch_for(runner, tmp_path, "282") == "spec/target-branch"


def test_by_hand_a_branch_name_asks_the_tracker_nothing(tmp_path, runner):
    write_loop(tmp_path, {"target-branch": "master"})

    assert target_branch_for(runner, tmp_path, "282") == "master"
    assert target_branch_for(runner, tmp_path, None) == "master"
    assert not runner.started("gh")


def test_by_hand_a_tracker_that_will_not_answer_stops_and_names_the_spec(tmp_path, runner):
    write_loop(tmp_path, {"target-branch": "spec"})
    runner.stub("gh", status=1)

    with pytest.raises(Stop) as stopped:
        target_branch_for(runner, tmp_path, "282")

    assert stopped.value.status == REFUSED
    assert "#282" in stopped.value.said


def test_by_hand_in_spec_mode_no_spec_stops_before_the_tracker_is_asked(tmp_path, runner):
    write_loop(tmp_path, {"target-branch": "spec"})

    with pytest.raises(Stop) as stopped:
        target_branch_for(runner, tmp_path, None)

    assert "no spec was given" in stopped.value.said
    assert not runner.started("gh")


def test_this_repo_lands_on_main():
    assert target_branch(ROOT) == "main"
