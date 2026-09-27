# Git, node and uv stay real, so the settings file and loop.json are really read. One case takes node off PATH.

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import BASH, SCRIPTS, Ran, Repo, git, launch, run

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
  "api repos/owner/repo/branches/"*"/protection --jq "*)
    branch="${2#repos/owner/repo/branches/}"; branch="${branch%/protection}"
    cat "$here/$branch-protection"; exit "$(cat "$here/$branch-protection-status")" ;;
  "api repos/owner/repo/rules/branches/"*" --jq .[].type") cat "$here/${2#repos/owner/repo/rules/branches/}-rules" ;;
  "api repos/owner/repo/branches/"*" --jq .name")
    branch="${2#repos/owner/repo/branches/}"
    grep -qxF -- "$branch" "$here/branches" || { echo "gh: Branch not found (HTTP 404)" >&2; exit 1; }
    echo "$branch" ;;
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
        for name, text in (("gh", GH), ("claude", CLAUDE)):
            stand_in = self.stand_ins / name
            stand_in.write_text(text, encoding="utf-8", newline="\n")
            stand_in.chmod(0o755)
        self.plugins = []
        self.target("main")
        self.answer("default-branch", "main")
        self.answer("branches", "main")
        self.answer("may-push", "true")
        self.answer("main-rules", "")
        self.protect("gh: Branch not protected (HTTP 404)", status=1)
        self.install("skillworks", forces=True)

    def answer(self, name, text):
        (self.stand_ins / name).write_text(text + "\n" if text else "", encoding="utf-8", newline="\n")

    def target(self, branch, tracker="github"):
        loop = self.repo / "docs" / "agents" / "loop.json"
        loop.parent.mkdir(parents=True, exist_ok=True)
        loop.write_text(json.dumps({"tracker": tracker, "target-branch": branch}, indent=2) + "\n",
                        encoding="utf-8", newline="\n")

    # A bare repo on disk answers for the url, so a remote no test can reach is still really read.
    def serve(self, url, *branches):
        bare = self.root / "remote.git"
        run(["git", "init", "--quiet", "--bare", "--initial-branch=" + branches[0], bare.as_posix()])
        for name, value in Repo.SETTINGS:
            git(self.repo, "config", name, value)
        git(self.repo, "commit", "--quiet", "--allow-empty", "-m", "Base")
        git(self.repo, "config", f"url.{bare.as_posix()}.insteadOf", url)
        git(self.repo, "remote", "set-url", "origin", url)
        for branch in branches:
            git(self.repo, "push", "--quiet", "origin", f"HEAD:refs/heads/{branch}")

    def protect(self, *lines, status=0, branch="main"):
        self.answer(f"{branch}-protection", "\n".join(lines))
        self.answer(f"{branch}-protection-status", str(status))

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


# A folder the program shares with preflight's tools, such as /usr/bin, is mirrored without it, since dropping it loses the tools.
TOOLS = ("git", "uv", "awk", "sort", "head", "grep", "paste", "sed", "basename")


def without(program, path, spare):
    folders = []
    for folder in path.split(os.pathsep):
        if not shutil.which(program, path=folder):
            folders.append(folder)
        elif any(shutil.which(tool, path=folder) for tool in TOOLS):
            mirror = spare / f"{program}-path-{len(folders)}"
            mirror.mkdir()
            for entry in Path(folder).iterdir():
                if entry.stem != program:
                    (mirror / entry.name).symlink_to(entry)
            folders.append(str(mirror))
    return os.pathsep.join(folders)


def with_stand_ins(work, node=True, gh=True):
    env = dict(os.environ)
    path = env["PATH"]
    if not node:
        path = without("node", path, work.root)
    if not gh:
        (work.stand_ins / "gh").unlink(missing_ok=True)
        path = without("gh", path, work.root)
    env["PATH"] = str(work.stand_ins) + os.pathsep + path
    return env


def preflight(work, *args, node=True, gh=True):
    done = subprocess.run(
        [BASH, PREFLIGHT.as_posix(), *args],
        cwd=work.repo, env=with_stand_ins(work, node, gh), capture_output=True, encoding="utf-8",
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


def test_a_missing_loop_file_fails_naming_the_command_that_writes_it(work):
    (work.repo / "docs" / "agents" / "loop.json").unlink()

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  docs/agents/loop.json is missing. Run seed-steering to write it." in ran.err
    assert "label ready-for-agent" not in ran.out


def test_a_loop_file_with_no_target_branch_fails(work):
    (work.repo / "docs" / "agents" / "loop.json").write_text('{"tracker": "github"}\n', encoding="utf-8")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  docs/agents/loop.json names no target-branch." in ran.err


def test_a_loop_file_with_no_tracker_fails(work):
    (work.repo / "docs" / "agents" / "loop.json").write_text('{"target-branch": "main"}\n', encoding="utf-8")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  docs/agents/loop.json names no tracker." in ran.err


def test_a_target_branch_split_across_lines_passes(work):
    (work.repo / "docs" / "agents" / "loop.json").write_text(
        '{\n  "tracker": "github",\n  "target-branch":\n    "main"\n}\n', encoding="utf-8", newline="\n")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch main" in ran.out


# A reader that matched text rather than JSON would take the last key it saw, which is develop.
def test_a_target_branch_nested_in_another_setting_is_not_the_target_branch(work):
    (work.repo / "docs" / "agents" / "loop.json").write_text(
        json.dumps({"tracker": "github", "target-branch": "main", "was": {"target-branch": "develop"}}),
        encoding="utf-8")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch main" in ran.out


def test_a_target_branch_named_master_that_is_on_the_remote_passes(work):
    work.target("master")
    work.answer("default-branch", "master")
    work.answer("branches", "master")
    work.answer("master-rules", "")
    work.protect("gh: Branch not protected (HTTP 404)", status=1, branch="master")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch master" in ran.out
    assert "me may push to master" in ran.out


def test_a_target_branch_missing_on_the_remote_fails_naming_it(work):
    work.target("master")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  the Target branch master in docs/agents/loop.json is not on owner/repo." in ran.err
    assert "label ready-for-agent" not in ran.out


def test_a_target_branch_other_than_the_default_branch_passes(work):
    work.answer("default-branch", "develop")
    work.answer("branches", "develop\nmain")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch main" in ran.out


def test_in_spec_mode_a_protected_default_branch_passes(work):
    work.target("spec")
    work.answer("main-rules", "pull_request\nrequired_status_checks")
    work.protect("enforced", "pull_request", "required_status_checks")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch spec, each reviewed into main" in ran.out
    assert "label ready-for-agent" in ran.out


def test_in_spec_mode_a_default_branch_missing_on_the_remote_fails(work):
    work.target("spec")
    work.answer("branches", "")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  the default branch main is not on owner/repo" in ran.err


def test_in_spec_mode_a_repo_that_refuses_this_login_a_push_fails(work):
    work.target("spec")
    work.answer("may-push", "false")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  me may not push to owner/repo, so the loop cannot land a ticket on a spec's branch." in ran.err


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


RULES = ("comments.md", "determinism.md", "file-placement.md", "words.md")


def rules(work, *names):
    folder = work.repo / "docs" / "agents" / "rules"
    folder.mkdir(parents=True)
    for name in names:
        (folder / name).write_text("# A rule\n", encoding="utf-8", newline="\n")


def claude_md(work, *lines):
    (work.repo / "CLAUDE.md").write_text("# Repo\n\n" + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def test_a_claude_md_that_imports_every_rule_passes(work):
    rules(work, *RULES)
    claude_md(work, *(f"@docs/agents/rules/{name}" for name in RULES))

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    CLAUDE.md imports every rule in docs/agents/rules" in ran.out


def test_a_rule_with_no_import_fails_naming_the_rule_and_the_line_to_add(work):
    rules(work, *RULES)
    claude_md(work, *(f"@docs/agents/rules/{name}" for name in RULES if name != "determinism.md"))

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert ("FAIL  docs/agents/rules/determinism.md has no import in CLAUDE.md, so it does not load into a session. "
            "Add this line to CLAUDE.md: @docs/agents/rules/determinism.md") in ran.err
    assert "label ready-for-agent" not in ran.out


def test_an_import_inside_other_text_does_not_count(work):
    rules(work, "words.md")
    claude_md(work, "See @docs/agents/rules/words.md.old for history.")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "docs/agents/rules/words.md has no import in CLAUDE.md" in ran.err


def test_rules_with_no_claude_md_fail(work):
    rules(work, "words.md")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "Add this line to CLAUDE.md: @docs/agents/rules/words.md" in ran.err


def test_a_repo_with_no_rules_folder_passes(work):
    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "import" not in said(ran)


GITLAB = "https://gitlab.example.com/team/repo.git"


def test_with_the_files_tracker_a_gitlab_remote_passes_without_gh(work):
    work.target("main", tracker="files")
    work.serve(GITLAB, "main")

    ran = preflight(work, gh=False)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch main" in ran.out
    assert "label ready-for-agent" not in ran.out


def test_with_the_files_tracker_a_bare_remote_on_a_shared_drive_passes(work):
    work.target("main", tracker="files")
    work.serve((work.root / "shared" / "repo.git").as_posix(), "main")

    ran = preflight(work, gh=False)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch main" in ran.out


def test_with_the_files_tracker_a_target_branch_missing_on_the_remote_fails_naming_it(work):
    work.target("master", tracker="files")
    work.serve(GITLAB, "main")

    ran = preflight(work, gh=False)

    assert ran.status == 1, said(ran)
    assert "FAIL  the Target branch master in docs/agents/loop.json is not on origin." in ran.err


def test_with_the_files_tracker_in_spec_mode_the_default_branch_of_the_remote_passes(work):
    work.target("spec", tracker="files")
    work.serve(GITLAB, "main")

    ran = preflight(work, gh=False)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch spec, each reviewed into main" in ran.out


def test_with_the_files_tracker_in_spec_mode_a_remote_with_no_default_branch_fails(work):
    work.target("spec", tracker="files")
    work.serve(GITLAB, "main")
    git(work.root / "remote.git", "symbolic-ref", "HEAD", "refs/heads/gone")

    ran = preflight(work, gh=False)

    assert ran.status == 1, said(ran)
    assert "FAIL  origin names no default branch" in ran.err


def test_with_the_files_tracker_check_only_passes_without_gh(work):
    work.target("main", tracker="files")
    work.serve(GITLAB, "main")

    ran = preflight(work, "--check-only", gh=False)

    assert ran.status == 0, said(ran)
    assert "label" not in ran.out


@pytest.mark.parametrize("tracker", ["github", "files"])
def test_a_repo_with_no_remote_fails_with_the_commands_that_add_a_bare_one(work, tracker):
    work.target("main", tracker=tracker)
    git(work.repo, "remote", "remove", "origin")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  no 'origin' remote." in ran.err
    assert "git init --bare" in ran.err
    assert "git remote add origin" in ran.err
    assert "git push origin main" in ran.err
