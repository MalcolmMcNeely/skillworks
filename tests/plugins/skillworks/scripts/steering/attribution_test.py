import io
import json

from conftest import PLUGIN, Ran, launch
from runner import Subprocess
from steering import attribution

SEEDED = PLUGIN / "skills" / "skillworks-setup" / "settings.json"


def settings_file(repo):
    return repo.work / ".claude" / "settings.json"


def team_settings(repo, text=None):
    path = settings_file(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text or SEEDED.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    return json.loads(path.read_text(encoding="utf-8"))


def run_attribution(where, *args):
    out, err = io.StringIO(), io.StringIO()
    status = attribution.main([where.as_posix(), *args], Subprocess(), out, err)
    return Ran(status, out.getvalue(), err.getvalue())


def settings_now(repo):
    return json.loads(settings_file(repo).read_text(encoding="utf-8"))


def test_hide_writes_empty_strings_for_commits_and_pull_requests_and_leaves_every_other_key(repo):
    before = team_settings(repo)

    ran = run_attribution(repo.work, "hide")

    after = settings_now(repo)
    assert ran.status == 0, ran.err
    assert after["attribution"] == {"commit": "", "pr": ""}
    assert {key: value for key, value in after.items() if key != "attribution"} == before
    assert "wrote" in ran.out and ".claude/settings.json" in ran.out


def test_show_writes_no_attribution_and_leaves_the_file_as_it_was(repo):
    team_settings(repo)
    before = settings_file(repo).read_bytes()

    ran = run_attribution(repo.work, "show")

    assert ran.status == 0, ran.err
    assert settings_file(repo).read_bytes() == before
    assert "attribution" not in settings_now(repo)
    assert "Claude Code's own default" in ran.out


def test_an_attribution_block_already_there_is_kept_whatever_the_answer(repo):
    for held in [{"commit": "", "pr": ""}, {"commit": "Made with care", "pr": ""}]:
        team_settings(repo, json.dumps({"autoMemoryEnabled": False, "attribution": held}, indent=2) + "\n")
        before = settings_file(repo).read_bytes()
        for answer in ["hide", "show"]:
            ran = run_attribution(repo.work, answer)

            assert ran.status == 0, ran.err
            assert settings_file(repo).read_bytes() == before
            assert "kept the attribution block in .claude/settings.json" in ran.out


def test_hide_with_no_settings_file_writes_one_that_holds_the_block(repo):
    ran = run_attribution(repo.work, "hide")

    assert ran.status == 0, ran.err
    assert settings_now(repo) == {"attribution": {"commit": "", "pr": ""}}


def test_no_answer_writes_false_or_touches_the_local_settings(repo):
    for text in [None, "{}\n", '{"attribution": {"commit": ""}}\n']:
        for answer in ["hide", "show"]:
            team_settings(repo, text)

            run_attribution(repo.work, answer)

            assert settings_now(repo).get("attribution") is not False
            assert "false" not in json.dumps(settings_now(repo).get("attribution", {}))
            assert not (repo.work / ".claude" / "settings.local.json").exists()


def test_an_answer_other_than_hide_or_show_is_a_misuse(repo):
    team_settings(repo)
    before = settings_file(repo).read_bytes()

    ran = run_attribution(repo.work, "false")

    assert ran.status == 64
    assert "hide|show" in ran.err
    assert settings_file(repo).read_bytes() == before


def test_a_settings_file_that_is_not_json_is_refused_and_left_alone(repo):
    settings_file(repo).parent.mkdir(parents=True)
    settings_file(repo).write_text('{"autoMemoryEnabled": false,', encoding="utf-8", newline="\n")

    ran = run_attribution(repo.work, "hide")

    assert ran.status == 1
    assert "FAIL  .claude/settings.json is not JSON" in ran.err
    assert settings_file(repo).read_text(encoding="utf-8") == '{"autoMemoryEnabled": false,'


def test_the_command_writes_the_settings_at_the_top_of_the_repository(repo):
    team_settings(repo)
    below = repo.work / "src" / "deep"
    below.mkdir(parents=True)

    ran = launch("set-attribution", "hide", where=below)

    assert ran.status == 0, ran.err
    assert settings_now(repo)["attribution"] == {"commit": "", "pr": ""}
    assert not (below / ".claude").exists()
