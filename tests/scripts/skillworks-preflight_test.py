# Git and node stay real, so the settings file is really read.

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import ROOT, Ran, git, run

PREFLIGHT = ROOT / "scripts" / "skillworks-preflight.sh"

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


# On Windows the first bash on PATH can be WSL's, which cannot see this repository.
def git_bash():
    if sys.platform != "win32":
        return shutil.which("bash")
    git_home = Path(run(["git", "--exec-path"]).strip()).parents[2]
    return str(git_home / "bin" / "bash.exe")


BASH = git_bash()


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


def preflight(work, *args):
    env = dict(os.environ)
    env["PATH"] = str(work.stand_ins) + os.pathsep + env["PATH"]
    done = subprocess.run(
        [BASH, PREFLIGHT.as_posix(), *args],
        cwd=work.repo, env=env, capture_output=True, encoding="utf-8", errors="replace")
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
