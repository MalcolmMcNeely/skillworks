import json

import pytest

from steering.session_trailer import session_trailer
from steering.target_branch import LOOP_FILE


def given_loop(top, settings):
    path = top / LOOP_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings), encoding="utf-8", newline="\n")


@pytest.mark.parametrize("answer", ["hide", "show"])
def test_the_answer_in_the_loop_file_is_read(tmp_path, answer):
    given_loop(tmp_path, {"tracker": "github", "target-branch": "main", "session-trailer": answer})

    assert session_trailer(tmp_path) == answer


def test_a_loop_file_with_no_answer_reads_as_show(tmp_path):
    given_loop(tmp_path, {"tracker": "github", "target-branch": "main"})

    assert session_trailer(tmp_path) == "show"


@pytest.mark.parametrize("answer", ["false", "", None, True])
def test_an_answer_other_than_hide_reads_as_show(tmp_path, answer):
    given_loop(tmp_path, {"tracker": "github", "target-branch": "main", "session-trailer": answer})

    assert session_trailer(tmp_path) == "show"


def test_a_missing_loop_file_reads_as_show(tmp_path):
    assert session_trailer(tmp_path) == "show"


@pytest.mark.parametrize("text", ['{"session-trailer": ', '["hide"]'])
def test_a_loop_file_that_holds_no_json_object_reads_as_show(tmp_path, text):
    (tmp_path / "docs" / "skillworks").mkdir(parents=True)
    (tmp_path / LOOP_FILE).write_text(text, encoding="utf-8", newline="\n")

    assert session_trailer(tmp_path) == "show"
