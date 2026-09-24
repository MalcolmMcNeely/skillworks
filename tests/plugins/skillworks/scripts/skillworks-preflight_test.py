# Git and node stay real, so the settings file is really read. One case takes node off PATH.

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import BASH, SCRIPTS, Ran, git, launch, run

PREFLIGHT = SCRIPTS / "skillworks-preflight.sh"

WARNING = "autoMemoryEnabled is not false in .claude/settings.json"

# Every call preflight makes is answered, and any other one fails, so a new call cannot pass on a guess.
GH = """#!/usr/bin/env bash
case "$*" in
  "auth status") exit 0 ;;
  "api user --jq .login") echo me ;;
  "repo view --json nameWithOwner --jq .nameWithOwner") echo owner/repo ;;
  "--version") echo "gh version 2.94.0 (2026-01-01)" ;;
  "api repos/owner/repo --jq .has_issues") echo true ;;
  "label list --limit 200 --json name --jq .[].name") echo ready-for-agent ;;
  *) echo "unplanned gh call: $*" >&2; exit 97 ;;
esac
"""

CLAUDE = """#!/usr/bin/env bash
case "$*" in
  "--version") echo "2.1.242 (Claude Code)" ;;
  *) echo "unplanned claude call: $*" >&2; exit 97 ;;
esac
"""

UV = """#!/usr/bin/env bash
echo "unplanned uv call: $*" >&2
exit 97
"""


class Work:
    def __init__(self, root):
        self.repo = root / "work"
        self.stand_ins = root / "stand-ins"
        run(["git", "init", "--quiet", "--initial-branch=main", self.repo.as_posix()])
        git(self.repo, "remote", "add", "origin", "https://github.com/owner/repo.git")
        self.stand_ins.mkdir()
        for name, text in (("gh", GH), ("claude", CLAUDE), ("uv", UV)):
            stand_in = self.stand_ins / name
            stand_in.write_text(text, encoding="utf-8", newline="\n")
            stand_in.chmod(0o755)


@pytest.fixture
def work(tmp_path):
    return Work(tmp_path)


def settings(work, text):
    (work.repo / ".claude").mkdir(exist_ok=True)
    (work.repo / ".claude" / "settings.json").write_text(text, encoding="utf-8", newline="\n")


# Node can share /usr/bin with the tools preflight calls, so that folder is mirrored, not dropped.
# Where node has a folder of its own, as on Windows, the folder is dropped and no mirror is made.
TOOLS = ("git", "awk", "sort", "head", "grep")


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
