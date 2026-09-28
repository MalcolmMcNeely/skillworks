import io
import json
import sys

import pytest

from configuration.checks import main

WARNING = "autoMemoryEnabled is not false in .claude/settings.json"
MEMORY_WARNING = ("warn  " + WARNING + ", so each session loads memory files only this machine holds. "
                  "Add \"autoMemoryEnabled\": false to that file.\n")
STYLE_WARNING = ("also forces an output style. When two plugins force one the first loaded wins, so the "
                 "loop's reports may not come in the skillworks style.")
COULD_NOT = "warn  could not check which plugins force an output style"

FORCED = "---\nname: {name}\nforce-for-plugin: true\n---\n\nTalk like a pirate.\n"
PLAIN = "---\nname: {name}\n---\n\nPlain.\n"


class Machine:
    def __init__(self, root, runner):
        self.root = root
        self.top = root / "work"
        self.top.mkdir()
        self.runner = runner
        self.plugins = []
        self.install("skillworks", forces=True)

    def settings(self, text):
        (self.top / ".claude").mkdir(exist_ok=True)
        (self.top / ".claude" / "settings.json").write_text(text, encoding="utf-8", newline="\n")

    def install(self, name, forces=False, enabled=True, project=None, styles=None, manifest=True):
        home = self.root / "plugins" / "{}-{}".format(name, len(self.plugins))
        (home / ".claude-plugin").mkdir(parents=True)
        folder = home / "output-styles"
        if manifest:
            held = {"name": name}
            if styles is not None:
                held["outputStyles"] = styles
                named = styles if isinstance(styles, list) else [styles]
                folder = home / named[0].strip("./")
            (home / ".claude-plugin" / "plugin.json").write_text(json.dumps(held), encoding="utf-8")
        folder.mkdir(parents=True, exist_ok=True)
        style = (FORCED if forces else PLAIN).format(name=name)
        (folder / "{}.md".format(name)).write_text(style, encoding="utf-8", newline="\n")
        entry = {"id": name + "@market", "enabled": enabled, "installPath": str(home)}
        if project is not None:
            entry["projectPath"] = str(project)
        self.plugins.append(entry)
        self.runner.stub("claude", says=json.dumps(self.plugins))
        return home

    def check(self):
        out = io.StringIO()
        status = main([str(self.top)], self.runner, out)
        assert status == 0
        return out.getvalue()


@pytest.fixture
def machine(tmp_path, runner):
    return Machine(tmp_path, runner)


def test_settings_that_turn_auto_memory_off_draw_no_warning(machine):
    machine.settings('{"permissions": {"allow": []}, "autoMemoryEnabled": false}')

    said = machine.check()

    assert "ok    auto-memory off\n" in said
    assert WARNING not in said


@pytest.mark.parametrize("text", [
    '{"permissions": {"allow": []}}',
    '{"autoMemoryEnabled": true}',
    '{"autoMemoryEnabled": 0}',
    '[false]',
    '{"autoMemoryEnabled": false,',
])
def test_settings_that_do_not_turn_auto_memory_off_warn_naming_the_key_and_the_file(machine, text):
    machine.settings(text)

    said = machine.check()

    assert MEMORY_WARNING in said
    assert "auto-memory off" not in said


def test_no_settings_file_warns(machine):
    assert MEMORY_WARNING in machine.check()


def test_a_settings_file_that_is_not_utf8_counts_as_not_false(machine):
    (machine.top / ".claude").mkdir()
    (machine.top / ".claude" / "settings.json").write_bytes(b'{"autoMemoryEnabled": false, "x": "\xff"}')

    assert MEMORY_WARNING in machine.check()


def test_the_plugins_are_read_from_claude(machine):
    machine.check()

    assert machine.runner.calls == [["claude", "plugin", "list", "--json"]]


def test_no_other_plugin_forcing_a_style_draws_no_warning(machine):
    machine.install("quiet")

    said = machine.check()

    assert "ok    no other plugin forces an output style\n" in said
    assert STYLE_WARNING not in said


def test_skillworks_forcing_its_own_style_draws_no_warning(machine):
    said = machine.check()

    assert STYLE_WARNING not in said


def test_a_second_enabled_plugin_that_forces_a_style_warns(machine):
    machine.install("pirate", forces=True)

    said = machine.check()

    assert "warn  pirate@market " + STYLE_WARNING + "\n" in said
    assert "no other plugin forces" not in said


def test_each_plugin_that_forces_a_style_is_named(machine):
    machine.install("pirate", forces=True)
    machine.install("robot", forces=True)

    said = machine.check()

    assert "warn  pirate@market " + STYLE_WARNING in said
    assert "warn  robot@market " + STYLE_WARNING in said


def test_a_disabled_plugin_that_forces_a_style_draws_no_warning(machine):
    machine.install("pirate", forces=True, enabled=False)

    assert STYLE_WARNING not in machine.check()


def test_a_plugin_enabled_for_another_project_draws_no_warning(machine):
    machine.install("pirate", forces=True, project=machine.root / "elsewhere")

    assert STYLE_WARNING not in machine.check()


def test_a_plugin_enabled_for_this_project_that_forces_a_style_warns(machine):
    machine.install("pirate", forces=True, project=machine.top)

    assert "pirate@market " + STYLE_WARNING in machine.check()


def test_on_windows_a_project_path_in_other_letter_case_is_this_project(machine, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    machine.install("pirate", forces=True, project=str(machine.top).upper())

    assert "pirate@market " + STYLE_WARNING in machine.check()


def test_elsewhere_a_project_path_in_other_letter_case_is_another_project(machine, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    machine.install("pirate", forces=True, project=str(machine.top).upper())

    assert STYLE_WARNING not in machine.check()


def test_a_forced_style_in_the_folder_the_manifest_names_warns(machine):
    machine.install("pirate", forces=True, styles="./voices")

    assert "pirate@market " + STYLE_WARNING in machine.check()


def test_a_forced_style_in_a_folder_from_a_list_the_manifest_names_warns(machine):
    machine.install("pirate", forces=True, styles=["./voices", "./more"])

    assert "pirate@market " + STYLE_WARNING in machine.check()


def test_a_forced_style_file_the_manifest_names_warns(machine):
    home = machine.install("pirate")
    (home / ".claude-plugin" / "plugin.json").write_text('{"outputStyles": "./talk.md"}', encoding="utf-8")
    (home / "talk.md").write_text(FORCED.format(name="talk"), encoding="utf-8", newline="\n")

    assert "pirate@market " + STYLE_WARNING in machine.check()


def test_a_plugin_with_no_manifest_still_has_its_output_styles_folder_read(machine):
    machine.install("pirate", forces=True, manifest=False)

    assert "pirate@market " + STYLE_WARNING in machine.check()


def test_a_force_outside_the_front_matter_does_not_count(machine):
    home = machine.install("pirate")
    (home / "output-styles" / "late.md").write_text(
        "---\nname: late\n---\n\nforce-for-plugin: true\n", encoding="utf-8", newline="\n")

    assert STYLE_WARNING not in machine.check()


def test_a_force_set_to_false_does_not_count(machine):
    home = machine.install("pirate")
    (home / "output-styles" / "off.md").write_text(
        "---\nname: off\nforce-for-plugin: false\n---\n", encoding="utf-8", newline="\n")

    assert STYLE_WARNING not in machine.check()


def test_front_matter_with_windows_line_ends_counts(machine):
    home = machine.install("pirate")
    (home / "output-styles" / "crlf.md").write_bytes(b"---\r\nname: crlf\r\nforce-for-plugin: true\r\n---\r\n")

    assert "pirate@market " + STYLE_WARNING in machine.check()


def test_a_file_that_is_not_markdown_does_not_count(machine):
    home = machine.install("pirate")
    (home / "output-styles" / "notes.txt").write_text(FORCED.format(name="notes"), encoding="utf-8")

    assert STYLE_WARNING not in machine.check()


@pytest.mark.parametrize("says", ["", "not json", '{"id": "pirate@market"}', '[{"enabled": true}]'])
def test_plugin_output_that_cannot_be_read_warns_that_the_styles_could_not_be_checked(machine, says):
    machine.runner.stub("claude", says=says)

    said = machine.check()

    assert (COULD_NOT + ", because claude plugin list --json gave nothing the preflight could read.\n") in said
    assert "no other plugin forces" not in said


def test_a_claude_that_fails_to_list_its_plugins_warns_that_the_styles_could_not_be_checked(machine):
    machine.runner.stub("claude", status=1)

    assert COULD_NOT in machine.check()


def test_auto_memory_is_checked_before_the_output_styles(machine):
    machine.install("pirate", forces=True)

    said = machine.check()

    assert said.index(WARNING) < said.index(STYLE_WARNING)
