import io
import json

import pytest

from conftest import ROOT
from stop import REFUSED, Stop
from steering.target_branch import (LOOP_FILE, in_spec_mode, main, target_branch, target_branch_for,
                                    tracker_for, tracker_setting)
from tracker.github import GitHub


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


def test_in_spec_mode_no_spec_stops_and_says_one_is_needed(tmp_path):
    write_loop(tmp_path, {"target-branch": "spec"})

    with pytest.raises(Stop) as stopped:
        target_branch(tmp_path)

    assert stopped.value.status == REFUSED
    assert "no spec was given" in stopped.value.said


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

SPEC_MODE_ON_GITHUB = {"tracker": "github", "target-branch": "spec"}


def test_by_hand_in_spec_mode_the_spec_is_asked_of_the_tracker_for_its_branch(tmp_path, runner):
    write_loop(tmp_path, SPEC_MODE_ON_GITHUB)
    runner.stub("gh", says=SPEC_BODY)

    assert target_branch_for(runner, tmp_path, "282") == "spec/target-branch"


def test_by_hand_a_branch_name_asks_the_tracker_nothing(tmp_path, runner):
    write_loop(tmp_path, {"target-branch": "master"})

    assert target_branch_for(runner, tmp_path, "282") == "master"
    assert target_branch_for(runner, tmp_path, None) == "master"
    assert not runner.started("gh")


def test_by_hand_a_tracker_that_will_not_answer_stops_and_names_the_spec(tmp_path, runner):
    write_loop(tmp_path, SPEC_MODE_ON_GITHUB)
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


def test_by_hand_in_spec_mode_the_spec_is_asked_of_the_tracker_it_is_handed(tmp_path, runner):
    write_loop(tmp_path, {"target-branch": "spec"})
    runner.stub("gh", says=SPEC_BODY)

    assert target_branch_for(runner, tmp_path, "282", GitHub(runner, tmp_path)) == "spec/target-branch"


def test_this_repo_lands_on_main():
    assert target_branch(ROOT) == "main"


# --- the Tracker ------------------------------------------------------------

def test_github_is_a_tracker(tmp_path, runner):
    write_loop(tmp_path, {"tracker": "github", "target-branch": "main"})

    assert tracker_setting(tmp_path) == "github"
    assert isinstance(tracker_for(runner, tmp_path), GitHub)


def test_a_loop_file_with_no_tracker_stops_and_names_the_setting(tmp_path, runner):
    write_loop(tmp_path, {"target-branch": "main"})

    with pytest.raises(Stop) as stopped:
        tracker_for(runner, tmp_path)

    assert stopped.value.status == REFUSED
    assert "names no tracker" in stopped.value.said
    assert '"tracker": "github"' in stopped.value.said


def test_a_tracker_the_loop_does_not_know_stops_and_names_the_ones_it_does(tmp_path, runner):
    write_loop(tmp_path, {"tracker": "jira", "target-branch": "main"})

    with pytest.raises(Stop) as stopped:
        tracker_for(runner, tmp_path)

    assert stopped.value.status == REFUSED
    assert 'the tracker "jira"' in stopped.value.said
    assert "It can be: github, files." in stopped.value.said


def test_a_missing_loop_file_stops_the_question_of_the_tracker_too(tmp_path, runner):
    with pytest.raises(Stop) as stopped:
        tracker_for(runner, tmp_path)

    assert "seed-steering" in stopped.value.said


def test_the_command_prints_the_tracker_when_asked_and_the_target_branch_otherwise(tmp_path):
    write_loop(tmp_path, {"tracker": "files", "target-branch": "master"})
    out, err = io.StringIO(), io.StringIO()

    assert main([str(tmp_path), "tracker"], out, err) == 0
    assert main([str(tmp_path)], out, err) == 0

    assert out.getvalue() == "files\nmaster\n"
    assert err.getvalue() == ""


def test_the_command_asked_for_a_missing_tracker_prints_why_it_stopped(tmp_path):
    write_loop(tmp_path, {"target-branch": "master"})
    out, err = io.StringIO(), io.StringIO()

    assert main([str(tmp_path), "tracker"], out, err) == REFUSED

    assert out.getvalue() == ""
    assert "names no tracker" in err.getvalue()


def test_this_repo_tracks_on_github():
    assert tracker_setting(ROOT) == "github"
