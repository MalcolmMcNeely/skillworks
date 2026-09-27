import io
import json

from conftest import PLUGIN, Ran, launch
from runner import Subprocess
from steering import allowlist

SEEDED = PLUGIN / "skills" / "skillworks-setup" / "settings.json"


def settings_file(repo):
    return repo.work / ".claude" / "settings.json"


def team_settings(repo, text=None):
    path = settings_file(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text or SEEDED.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    return json.loads(path.read_text(encoding="utf-8"))


def run_allowlist(where, *entries):
    out, err = io.StringIO(), io.StringIO()
    status = allowlist.main([where.as_posix(), *entries], Subprocess(), out, err)
    return Ran(status, out.getvalue(), err.getvalue())


def settings_now(repo):
    return json.loads(settings_file(repo).read_text(encoding="utf-8"))


def test_an_entry_is_added_to_the_allowlist_and_no_entry_or_key_is_removed(repo):
    before = team_settings(repo)

    ran = run_allowlist(repo.work, "Bash(dotnet test:*)")

    after = settings_now(repo)
    assert ran.status == 0, ran.err
    assert after["permissions"]["allow"] == before["permissions"]["allow"] + ["Bash(dotnet test:*)"]
    assert {key: value for key, value in after.items() if key != "permissions"} == {
        key: value for key, value in before.items() if key != "permissions"}
    assert "added Bash(dotnet test:*) to permissions.allow in .claude/settings.json" in ran.out


def test_an_entry_already_there_is_not_added_twice_and_the_file_is_left_as_it_was(repo):
    team_settings(repo)
    before = settings_file(repo).read_bytes()

    ran = run_allowlist(repo.work, "Bash(git push:*)")

    assert ran.status == 0, ran.err
    assert settings_file(repo).read_bytes() == before
    assert "Bash(git push:*) is already in permissions.allow" in ran.out


def test_several_entries_are_added_in_the_order_given_each_once(repo):
    before = team_settings(repo)

    run_allowlist(repo.work, "Bash(npm run lint:*)", "Bash(git push:*)", "Bash(npm ci:*)", "Bash(npm ci:*)")

    assert settings_now(repo)["permissions"]["allow"] == before["permissions"]["allow"] + [
        "Bash(npm run lint:*)", "Bash(npm ci:*)"]


def test_an_entry_is_added_after_the_last_one_and_the_rest_of_the_file_is_kept_byte_for_byte(repo):
    settings_file(repo).parent.mkdir(parents=True)
    settings_file(repo).write_bytes(
        b'{\r\n\t"note": "caf\xc3\xa9",\r\n\t"permissions": {\r\n\t\t"allow": [\r\n\t\t\t"Bash(git status)"\r\n'
        b'\t\t],\r\n\t\t"deny": ["Bash(rm:*)"]\r\n\t}\r\n}')

    run_allowlist(repo.work, "Bash(go test:*)")

    assert settings_file(repo).read_bytes() == (
        b'{\r\n\t"note": "caf\xc3\xa9",\r\n\t"permissions": {\r\n\t\t"allow": [\r\n\t\t\t"Bash(git status)",\r\n'
        b'\t\t\t"Bash(go test:*)"\r\n\t\t],\r\n\t\t"deny": ["Bash(rm:*)"]\r\n\t}\r\n}')


def test_an_entry_is_added_on_the_same_line_of_an_allowlist_on_one_line(repo):
    team_settings(repo, '{"permissions": {"allow": ["Bash(git status)"]}}\n')

    run_allowlist(repo.work, "Bash(go test:*)")

    assert settings_file(repo).read_text(encoding="utf-8") == (
        '{"permissions": {"allow": ["Bash(git status)","Bash(go test:*)"]}}\n')


def test_a_file_with_no_allowlist_gains_one_and_keeps_every_other_key(repo):
    for text in ['{\n  "autoMemoryEnabled": false\n}\n',
                 '{\n  "permissions": {\n    "deny": []\n  }\n}\n',
                 '{\n  "permissions": {\n    "allow": []\n  }\n}\n']:
        before = team_settings(repo, text)

        ran = run_allowlist(repo.work, "Bash(dotnet test:*)")

        after = settings_now(repo)
        assert ran.status == 0, ran.err
        assert after["permissions"]["allow"] == ["Bash(dotnet test:*)"]
        assert {key: value for key, value in after["permissions"].items() if key != "allow"} == {
            key: value for key, value in before.get("permissions", {}).items() if key != "allow"}
        assert {key: value for key, value in after.items() if key != "permissions"} == {
            key: value for key, value in before.items() if key != "permissions"}


def test_with_no_settings_file_the_command_writes_one_that_holds_the_allowlist(repo):
    ran = run_allowlist(repo.work, "Bash(dotnet test:*)")

    assert ran.status == 0, ran.err
    assert settings_now(repo) == {"permissions": {"allow": ["Bash(dotnet test:*)"]}}


def test_no_entry_is_a_misuse(repo):
    team_settings(repo)
    before = settings_file(repo).read_bytes()

    ran = run_allowlist(repo.work)

    assert ran.status == 64
    assert "usage: allow-commands" in ran.err
    assert settings_file(repo).read_bytes() == before


def test_a_settings_file_that_is_not_json_is_refused_and_left_alone(repo):
    settings_file(repo).parent.mkdir(parents=True)
    settings_file(repo).write_text('{"permissions": {', encoding="utf-8", newline="\n")

    ran = run_allowlist(repo.work, "Bash(go test:*)")

    assert ran.status == 1
    assert "FAIL  .claude/settings.json is not JSON" in ran.err
    assert settings_file(repo).read_text(encoding="utf-8") == '{"permissions": {'


def test_an_allowlist_that_is_not_a_list_is_refused_and_left_alone(repo):
    for text in ['[]\n', '{"permissions": []}\n', '{"permissions": {"allow": "Bash(git status)"}}\n']:
        team_settings(repo, text)

        ran = run_allowlist(repo.work, "Bash(go test:*)")

        assert ran.status == 1, text
        assert ran.err.startswith("FAIL  ") and "Nothing was written." in ran.err
        assert settings_file(repo).read_text(encoding="utf-8") == text


def test_the_command_writes_the_settings_at_the_top_of_the_repository(repo):
    team_settings(repo)
    below = repo.work / "src" / "deep"
    below.mkdir(parents=True)

    ran = launch("allow-commands", "Bash(dotnet test:*)", where=below)

    assert ran.status == 0, ran.err
    assert "Bash(dotnet test:*)" in settings_now(repo)["permissions"]["allow"]
    assert not (below / ".claude").exists()
