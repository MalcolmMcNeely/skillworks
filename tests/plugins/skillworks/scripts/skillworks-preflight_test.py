# Git and node stay real, so the settings file is really read. One case takes node off PATH.

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import BASH, SCRIPTS, Ran, git, launch, run

PREFLIGHT = SCRIPTS / "skillworks-preflight.sh"

WARNING = "autoMemoryEnabled is not false in .claude/settings.json"

# Every call preflight makes is answered, and any other one fails, so a new call cannot pass on a guess.
# Varied answers sit in files beside the stand-ins, so one stand-in serves every case.
GH = """#!/usr/bin/env bash
here="$(dirname "$0")"
case "$*" in
  "auth status") exit 0 ;;
  "api user --jq .login") echo me ;;
  "repo view --json nameWithOwner --jq .nameWithOwner") echo owner/repo ;;
  "--version") echo "gh version 2.94.0 (2026-01-01)" ;;
  "api repos/owner/repo --jq .has_issues") echo true ;;
  "api repos/owner/repo --jq .default_branch") cat "$here/default-branch" ;;
  "api repos/owner/repo --jq .permissions.push") cat "$here/may-push" ;;
  "api repos/owner/repo/rules/branches/main --jq .[].type") cat "$here/main-rules" ;;
  "api repos/owner/repo/branches/main/protection --jq "*) cat "$here/main-protection"; exit "$(cat "$here/main-protection-status")" ;;
  "label list --limit 200 --json name --jq .[].name") echo ready-for-agent ;;
  *) echo "unplanned gh call: $*" >&2; exit 97 ;;
esac
"""

CLAUDE = """#!/usr/bin/env bash
case "$*" in
  "--version") echo "2.1.242 (Claude Code)" ;;
  "plugin list --json") cat "$(dirname "$0")/plugins.json" ;;
  *) echo "unplanned claude call: $*" >&2; exit 97 ;;
esac
"""

UV = """#!/usr/bin/env bash
echo "unplanned uv call: $*" >&2
exit 97
"""

FORCED = "---\nname: {name}\nforce-for-plugin: true\n---\n\nTalk like a pirate.\n"
PLAIN = "---\nname: {name}\n---\n\nPlain.\n"


class Work:
    def __init__(self, root):
        self.root = root
        self.repo = root / "work"
        self.stand_ins = root / "stand-ins"
        run(["git", "init", "--quiet", "--initial-branch=main", self.repo.as_posix()])
        git(self.repo, "remote", "add", "origin", "https://github.com/owner/repo.git")
        # Git can spell a temporary folder differently from the way pytest handed it out.
        self.top = git(self.repo, "rev-parse", "--show-toplevel").strip()
        self.stand_ins.mkdir()
        for name, text in (("gh", GH), ("claude", CLAUDE), ("uv", UV)):
            stand_in = self.stand_ins / name
            stand_in.write_text(text, encoding="utf-8", newline="\n")
            stand_in.chmod(0o755)
        self.plugins = []
        self.answer("default-branch", "main")
        self.answer("may-push", "true")
        self.answer("main-rules", "")
        self.protect("gh: Branch not protected (HTTP 404)", status=1)
        self.install("skillworks", forces=True)

    def answer(self, name, text):
        (self.stand_ins / name).write_text(text + "\n" if text else "", encoding="utf-8", newline="\n")

    def protect(self, *lines, status=0):
        self.answer("main-protection", "\n".join(lines))
        self.answer("main-protection-status", str(status))

    def install(self, name, forces=False, enabled=True, scope="user", project=None, styles=None):
        home = self.root / "plugins" / f"{name}-{len(self.plugins)}"
        (home / ".claude-plugin").mkdir(parents=True)
        manifest = {"name": name}
        folder = home / "output-styles"
        if styles is not None:
            manifest["outputStyles"] = styles
            folder = home / styles.strip("./")
        (home / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
        folder.mkdir(parents=True)
        style = (FORCED if forces else PLAIN).format(name=name)
        (folder / f"{name}.md").write_text(style, encoding="utf-8", newline="\n")
        entry = {"id": f"{name}@market", "scope": scope, "enabled": enabled, "installPath": str(home)}
        if project is not None:
            entry["projectPath"] = project
        self.plugins.append(entry)
        (self.stand_ins / "plugins.json").write_text(json.dumps(self.plugins), encoding="utf-8")


@pytest.fixture
def work(tmp_path):
    return Work(tmp_path)


def settings(work, text):
    (work.repo / ".claude").mkdir(exist_ok=True)
    (work.repo / ".claude" / "settings.json").write_text(text, encoding="utf-8", newline="\n")


# Node can share /usr/bin with the tools preflight calls, so that folder is mirrored, not dropped.
# Where node has a folder of its own, as on Windows, the folder is dropped and no mirror is made.
TOOLS = ("git", "awk", "sort", "head", "grep", "paste")


def without_node(path, spare):
    folders = []
    for folder in path.split(os.pathsep):
        if not shutil.which("node", path=folder):
            folders.append(folder)
        elif any(shutil.which(tool, path=folder) for tool in TOOLS):
            mirror = spare / f"path-{len(folders)}"
            mirror.mkdir()
            for entry in Path(folder).iterdir():
                if entry.stem != "node":
                    (mirror / entry.name).symlink_to(entry)
            folders.append(str(mirror))
    return os.pathsep.join(folders)


def with_stand_ins(work, node=True):
    env = dict(os.environ)
    path = env["PATH"] if node else without_node(env["PATH"], work.stand_ins.parent)
    env["PATH"] = str(work.stand_ins) + os.pathsep + path
    return env


def preflight(work, *args, node=True):
    done = subprocess.run(
        [BASH, PREFLIGHT.as_posix(), *args],
        cwd=work.repo, env=with_stand_ins(work, node), capture_output=True, encoding="utf-8",
        errors="replace")
    return Ran(done.returncode, done.stdout, done.stderr)


def said(ran):
    return ran.out + ran.err


def test_settings_that_turn_auto_memory_off_draw_no_warning(work):
    settings(work, '{"permissions": {"allow": []}, "autoMemoryEnabled": false}')

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert WARNING not in said(ran)
    assert "auto-memory off" in ran.out


def test_settings_without_the_key_warn_naming_the_key_and_the_file(work):
    settings(work, '{"permissions": {"allow": []}}')

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert WARNING in ran.out


def test_settings_that_turn_auto_memory_on_warn(work):
    settings(work, '{"autoMemoryEnabled": true}')

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert WARNING in ran.out


def test_no_settings_file_warns(work):
    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert WARNING in ran.out


def test_a_settings_file_that_is_not_json_warns_and_does_not_crash(work):
    settings(work, '{"autoMemoryEnabled": false,')

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert WARNING in ran.out


def test_a_machine_without_node_warns_that_the_setting_could_not_be_checked(work):
    settings(work, '{"autoMemoryEnabled": false}')

    ran = preflight(work, node=False)

    assert ran.status == 0, said(ran)
    assert "could not check autoMemoryEnabled" in ran.out
    assert "node is not on PATH" in ran.out
    assert WARNING not in said(ran)


def test_check_only_prints_the_same_warning(work):
    settings(work, '{"autoMemoryEnabled": true}')

    ran = preflight(work, "--check-only")

    assert ran.status == 0, said(ran)
    assert WARNING in ran.out
    assert "no labels were written" in ran.out


def test_the_warning_comes_after_the_label_work(work):
    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert ran.out.index("label ready-for-agent") < ran.out.index(WARNING)


def test_the_preflight_command_reads_the_settings_at_the_top_of_the_repository(work):
    settings(work, '{"autoMemoryEnabled": false}')
    below = work.repo / "src" / "deep"
    below.mkdir(parents=True)

    ran = launch("skillworks-preflight", where=below, env=with_stand_ins(work))

    assert ran.status == 0, said(ran)
    assert "auto-memory off" in ran.out
    assert WARNING not in said(ran)


def test_the_preflight_command_names_itself_in_its_usage(work):
    ran = launch("skillworks-preflight", "--no-such-flag", where=work.repo, env=with_stand_ins(work))

    assert ran.status == 64
    assert ran.err == "usage: skillworks-preflight [--check-only]\n"


STYLE_WARNING = "also forces an output style"


def test_no_other_plugin_forcing_a_style_draws_no_warning(work):
    work.install("quiet")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert STYLE_WARNING not in said(ran)
    assert "no other plugin forces an output style" in ran.out


def test_a_second_enabled_plugin_that_forces_a_style_warns_and_passes(work):
    work.install("pirate", forces=True)

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "warn  pirate@market " + STYLE_WARNING in ran.out


def test_a_forced_style_in_the_folder_the_manifest_names_warns(work):
    work.install("pirate", forces=True, styles="./voices")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "pirate@market " + STYLE_WARNING in ran.out


def test_a_disabled_plugin_that_forces_a_style_draws_no_warning(work):
    work.install("pirate", forces=True, enabled=False)

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert STYLE_WARNING not in said(ran)


def test_a_plugin_enabled_for_another_project_draws_no_warning(work):
    work.install("pirate", forces=True, scope="project", project=str(work.root / "elsewhere"))

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert STYLE_WARNING not in said(ran)


def test_a_plugin_enabled_for_this_project_that_forces_a_style_warns(work):
    work.install("pirate", forces=True, scope="project", project=work.top)

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "pirate@market " + STYLE_WARNING in ran.out


def test_a_machine_without_node_warns_that_forced_styles_could_not_be_checked(work):
    work.install("pirate", forces=True)

    ran = preflight(work, node=False)

    assert ran.status == 0, said(ran)
    assert "could not check which plugins force an output style" in ran.out
    assert STYLE_WARNING not in said(ran)


def test_a_default_branch_other_than_main_fails_naming_the_branch(work):
    work.answer("default-branch", "trunk")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  the default branch of owner/repo is trunk, not main." in ran.err
    assert "label ready-for-agent" not in ran.out


def test_a_repo_that_refuses_this_login_a_push_fails(work):
    work.answer("may-push", "false")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  me may not push to owner/repo, so the loop cannot land a ticket on main." in ran.err


def test_a_rule_that_refuses_a_push_to_main_fails_naming_the_rule(work):
    work.answer("main-rules", "deletion\npull_request")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  a rule on main in owner/repo refuses a direct push (pull_request)" in ran.err


def test_a_rule_that_lets_a_push_through_passes(work):
    work.answer("main-rules", "deletion\nnon_fast_forward")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "may push to main" in ran.out


@pytest.mark.parametrize("protection", ["pull_request", "required_status_checks", "lock_branch"])
def test_classic_protection_that_refuses_a_push_to_main_fails_naming_the_protection(work, protection):
    work.protect("enforced", protection)

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert f"FAIL  classic branch protection on main in owner/repo refuses a direct push ({protection})" in ran.err
    assert "label ready-for-agent" not in ran.out


def test_classic_protection_that_lets_admins_through_passes(work):
    work.protect("pull_request", "restrictions")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "me may push to main" in ran.out


def test_classic_protection_that_restricts_pushes_to_others_fails(work):
    work.protect("enforced", "restrictions", "user someone")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  classic branch protection on main in owner/repo restricts who may push, and me is not one of them." in ran.err


def test_classic_protection_that_restricts_pushes_to_this_login_passes(work):
    work.protect("enforced", "restrictions", "user someone", "user me")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "me may push to main" in ran.out


def test_classic_protection_that_restricts_pushes_to_a_team_warns_and_passes(work):
    work.protect("enforced", "restrictions", "team builders")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "warn  classic branch protection on main in owner/repo lets teams push (builders)" in ran.out


def test_classic_protection_that_cannot_be_read_warns_and_passes(work):
    work.protect("gh: Must have admin rights to Repository. (HTTP 403)", status=1)

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "warn  could not read the classic branch protection on main in owner/repo" in ran.out
    assert "may push to main" not in ran.out
    assert "label ready-for-agent" in ran.out
