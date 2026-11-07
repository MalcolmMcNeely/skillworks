import json

import pytest

from conftest import ROOT
from steering.export import export_on
from steering.target_branch import LOOP_FILE, settings
from stop import REFUSED, Stop


def given_loop(top, held):
    path = top / LOOP_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(held), encoding="utf-8", newline="\n")


@pytest.mark.parametrize("answer", [True, False])
def test_the_answer_in_the_loop_file_is_read(tmp_path, answer):
    given_loop(tmp_path, {"tracker": "github", "target-branch": "spec", "export": answer})

    assert export_on(tmp_path) is answer


def test_a_loop_file_with_no_answer_reads_as_off(tmp_path):
    given_loop(tmp_path, {"tracker": "github", "target-branch": "main"})

    assert export_on(tmp_path) is False


def test_export_with_a_named_target_branch_stops_and_says_it_needs_spec(tmp_path):
    given_loop(tmp_path, {"tracker": "github", "target-branch": "main", "export": True})

    with pytest.raises(Stop) as stopped:
        export_on(tmp_path)

    assert stopped.value.status == REFUSED
    assert 'export works only with "target-branch": "spec"' in stopped.value.said


@pytest.mark.parametrize("answer", ["true", "yes", 1, None])
def test_an_answer_that_is_neither_true_nor_false_stops_and_names_both(tmp_path, answer):
    given_loop(tmp_path, {"tracker": "github", "target-branch": "spec", "export": answer})

    with pytest.raises(Stop) as stopped:
        export_on(tmp_path)

    assert "It can be true or false." in stopped.value.said


def test_a_missing_loop_file_stops_and_names_the_command_that_writes_it(tmp_path):
    with pytest.raises(Stop) as stopped:
        export_on(tmp_path)

    assert "seed-steering" in stopped.value.said


def test_this_repo_names_export_and_leaves_it_off():
    assert settings(ROOT)["export"] is False
