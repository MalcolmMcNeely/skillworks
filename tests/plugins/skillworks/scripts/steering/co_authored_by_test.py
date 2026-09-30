import io
import json

import pytest

from conftest import PLUGIN, Ran, launch, write_loop
from runner import Subprocess
from steering import co_authored_by
from steering.target_branch import LOOP_FILE

SEEDED = PLUGIN / "skills" / "skillworks-setup" / "settings.json"

HIDDEN = {"commit": "", "pr": ""}
SHOWN = {"commit": ""}


@pytest.fixture
def repo(repo):
    write_loop(repo.work, "main")
    return repo


def settings_file(repo):
    return repo.work / ".claude" / "settings.json"


def loop_file(repo):
    return repo.work / LOOP_FILE


def team_settings(repo, text=None):
    path = settings_file(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text or SEEDED.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    return json.loads(path.read_text(encoding="utf-8"))


def run_co_authored_by(where, *args):
    out, err = io.StringIO(), io.StringIO()
    status = co_authored_by.main([where.as_posix(), *args], Subprocess(), out, err)
    return Ran(status, out.getvalue(), err.getvalue())


def settings_now(repo):
    return json.loads(settings_file(repo).read_text(encoding="utf-8"))


def loop_now(repo):
    return json.loads(loop_file(repo).read_text(encoding="utf-8"))


@pytest.mark.parametrize("answer", ["hide", "show"])
def test_the_answer_is_written_to_the_loop_file_beside_every_other_setting(repo, answer):
    ran = launch("set-co-authored-by", answer, where=repo.work)

    assert ran.status == 0, ran.err
    assert loop_now(repo) == {"tracker": "github", "target-branch": "main", "co-authored-by": answer}
    assert "docs/agents/loop.json" in ran.out


def test_the_loop_file_keeps_its_layout_and_only_the_answer_changes(repo):
    loop_file(repo).write_bytes(b'{\r\n    "tracker": "files",\r\n    "co-authored-by": "show",\r\n'
                                b'    "target-branch": "spec"\r\n}\r\n')

    run_co_authored_by(repo.work, "hide")

    assert loop_file(repo).read_bytes() == (b'{\r\n    "tracker": "files",\r\n    "co-authored-by": "hide",\r\n'
                                            b'    "target-branch": "spec"\r\n}\r\n')


def test_hide_writes_empty_strings_for_commits_and_pull_requests_and_leaves_every_other_key(repo):
    before = team_settings(repo)

    ran = run_co_authored_by(repo.work, "hide")

    after = settings_now(repo)
    assert ran.status == 0, ran.err
    assert after["attribution"] == HIDDEN
    assert {key: value for key, value in after.items() if key != "attribution"} == before
    assert "wrote" in ran.out and ".claude/settings.json" in ran.out


def test_show_turns_off_only_the_commit_credit_and_leaves_every_other_key(repo):
    before = team_settings(repo)

    ran = run_co_authored_by(repo.work, "show")

    after = settings_now(repo)
    assert ran.status == 0, ran.err
    assert after["attribution"] == SHOWN
    assert {key: value for key, value in after.items() if key != "attribution"} == before


@pytest.mark.parametrize("first, then, block", [("hide", "show", SHOWN), ("show", "hide", HIDDEN)])
def test_a_second_run_with_the_other_answer_rewrites_the_block_and_the_key(repo, first, then, block):
    team_settings(repo)
    run_co_authored_by(repo.work, first)

    ran = run_co_authored_by(repo.work, then)

    assert ran.status == 0, ran.err
    assert settings_now(repo)["attribution"] == block
    assert loop_now(repo)["co-authored-by"] == then


@pytest.mark.parametrize("answer, block", [("hide", HIDDEN), ("show", SHOWN)])
def test_a_block_edited_by_hand_comes_back_into_step(repo, answer, block):
    team_settings(repo, '{\n  "attribution": {\n    "commit": "Made with care",\n    "pr": "Made with care"\n  },\n'
                        '  "autoMemoryEnabled": false\n}\n')

    run_co_authored_by(repo.work, answer)

    assert settings_now(repo) == {"attribution": block, "autoMemoryEnabled": False}


def test_a_block_rewritten_in_place_keeps_the_files_layout(repo):
    team_settings(repo, '{\n\t"attribution": { "commit": "x" },\n\t"autoMemoryEnabled": false\n}\n')

    run_co_authored_by(repo.work, "hide")

    assert settings_file(repo).read_text(encoding="utf-8") == (
        '{\n\t"attribution": {\n\t\t"commit": "",\n\t\t"pr": ""\n\t},\n\t"autoMemoryEnabled": false\n}\n'
    )


def test_hide_adds_only_the_block_to_a_file_indented_with_tabs(repo):
    team_settings(repo, '{\n\t"permissions": {\n\t\t"allow": ["Bash(git status)"]\n\t}\n}\n')

    run_co_authored_by(repo.work, "hide")

    assert settings_file(repo).read_text(encoding="utf-8") == (
        '{\n\t"permissions": {\n\t\t"allow": ["Bash(git status)"]\n\t},\n'
        '\t"attribution": {\n\t\t"commit": "",\n\t\t"pr": ""\n\t}\n}\n'
    )


def test_hide_adds_only_the_block_to_a_file_indented_with_four_spaces_and_crlf(repo):
    settings_file(repo).parent.mkdir(parents=True)
    settings_file(repo).write_bytes(b'{\r\n    "zeta": 1,\r\n    "alpha": true\r\n}')

    run_co_authored_by(repo.work, "hide")

    assert settings_file(repo).read_bytes() == (
        b'{\r\n    "zeta": 1,\r\n    "alpha": true,\r\n'
        b'    "attribution": {\r\n        "commit": "",\r\n        "pr": ""\r\n    }\r\n}'
    )


def test_hide_leaves_non_ascii_text_as_the_team_wrote_it(repo):
    team_settings(repo, '{\n  "note": "café ✓"\n}\n')

    run_co_authored_by(repo.work, "hide")

    assert settings_file(repo).read_text(encoding="utf-8") == (
        '{\n  "note": "café ✓",\n  "attribution": {\n    "commit": "",\n    "pr": ""\n  }\n}\n'
    )


def test_show_adds_the_block_on_the_same_line_of_a_file_on_one_line(repo):
    team_settings(repo, '{"autoMemoryEnabled":false}')

    run_co_authored_by(repo.work, "show")

    assert settings_file(repo).read_text(encoding="utf-8") == '{"autoMemoryEnabled":false,"attribution":{"commit":""}}'


def test_hide_writes_the_plain_form_to_an_empty_object(repo):
    team_settings(repo, "{ }\n")

    run_co_authored_by(repo.work, "hide")

    assert settings_file(repo).read_text(encoding="utf-8") == (
        '{\n  "attribution": {\n    "commit": "",\n    "pr": ""\n  }\n}\n'
    )


def test_show_with_no_settings_file_writes_one_that_holds_the_block(repo):
    ran = run_co_authored_by(repo.work, "show")

    assert ran.status == 0, ran.err
    assert settings_file(repo).read_text(encoding="utf-8") == '{\n  "attribution": {\n    "commit": ""\n  }\n}\n'


def test_no_answer_writes_false_or_touches_the_local_settings(repo):
    for text in [None, "{}\n", '{"attribution": {"commit": "x"}}\n', '{"attribution": false}\n']:
        for answer in ["hide", "show"]:
            team_settings(repo, text)

            run_co_authored_by(repo.work, answer)

            assert "false" not in json.dumps(settings_now(repo)["attribution"])
            assert not (repo.work / ".claude" / "settings.local.json").exists()


def test_an_answer_other_than_hide_or_show_is_a_misuse_and_writes_nothing(repo):
    team_settings(repo)
    before = settings_file(repo).read_bytes(), loop_file(repo).read_bytes()

    ran = run_co_authored_by(repo.work, "false")

    assert ran.status == 64
    assert "set-co-authored-by hide|show" in ran.err
    assert (settings_file(repo).read_bytes(), loop_file(repo).read_bytes()) == before


def test_a_settings_file_that_is_not_json_is_refused_and_nothing_is_written(repo):
    settings_file(repo).parent.mkdir(parents=True)
    settings_file(repo).write_text('{"autoMemoryEnabled": false,', encoding="utf-8", newline="\n")
    before = loop_file(repo).read_bytes()

    ran = run_co_authored_by(repo.work, "hide")

    assert ran.status == 1
    assert "FAIL  .claude/settings.json is not JSON" in ran.err
    assert settings_file(repo).read_text(encoding="utf-8") == '{"autoMemoryEnabled": false,'
    assert loop_file(repo).read_bytes() == before


def test_a_settings_file_that_holds_no_json_object_is_refused_and_left_alone(repo):
    for text in ['[{"autoMemoryEnabled": false}]\n', "[]\n", '"attribution"\n']:
        team_settings(repo, text)

        ran = run_co_authored_by(repo.work, "hide")

        assert ran.status == 1
        assert "FAIL  .claude/settings.json does not hold a JSON object" in ran.err
        assert settings_file(repo).read_text(encoding="utf-8") == text


def test_a_missing_loop_file_is_refused_with_the_command_that_writes_it_and_nothing_is_written(repo):
    loop_file(repo).unlink()

    ran = run_co_authored_by(repo.work, "hide")

    assert ran.status == 1
    assert "seed-steering" in ran.err
    assert not settings_file(repo).exists()


def test_a_loop_file_that_is_not_json_is_refused_and_nothing_is_written(repo):
    loop_file(repo).write_text('{"tracker": ', encoding="utf-8", newline="\n")

    ran = run_co_authored_by(repo.work, "hide")

    assert ran.status == 1
    assert "FAIL  docs/agents/loop.json is not JSON" in ran.err
    assert not settings_file(repo).exists()


def test_the_command_writes_both_files_at_the_top_of_the_repository(repo):
    team_settings(repo)
    below = repo.work / "src" / "deep"
    below.mkdir(parents=True)

    ran = launch("set-co-authored-by", "hide", where=below)

    assert ran.status == 0, ran.err
    assert settings_now(repo)["attribution"] == HIDDEN
    assert loop_now(repo)["co-authored-by"] == "hide"
    assert not (below / ".claude").exists() and not (below / "docs").exists()


def test_the_old_command_is_gone():
    assert not (PLUGIN / "bin" / "set-attribution").exists()
