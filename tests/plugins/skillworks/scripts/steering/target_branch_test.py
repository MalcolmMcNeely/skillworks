import json

import pytest

from conftest import ROOT
from stop import REFUSED, Stop
from steering.target_branch import LOOP_FILE, target_branch


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


def test_this_repo_lands_on_main():
    assert target_branch(ROOT) == "main"
