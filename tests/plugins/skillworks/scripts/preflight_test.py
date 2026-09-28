# Git stays real, so loop.json, CLAUDE.md and a bare remote are really read.

import io
import json
import os
import shutil

import pytest

from conftest import Ran, Repo, git, launch, run
from preflight import main

WARNING = "autoMemoryEnabled is not false in .claude/settings.json"
STYLE_WARNING = "also forces an output style"
COLD_CACHE = "Each ticket will pay a cold prompt cache."

FORCED = "---\nname: {name}\nforce-for-plugin: true\n---\n\nTalk like a pirate.\n"

LABEL_CREATE = "label create ready-for-agent --color 0e8a16 --description Fully specified. An agent can take it."


def protection(*held, users=(), teams=()):
    body = {"enforce_admins": {"enabled": "enforced" in held}, "lock_branch": {"enabled": "lock_branch" in held}}
    if "pull_request" in held:
        body["required_pull_request_reviews"] = {"required_approving_review_count": 1}
    if "required_status_checks" in held:
        body["required_status_checks"] = {"strict": True, "contexts": []}
    if "restrictions" in held:
        body["restrictions"] = {"users": [{"login": user} for user in users],
                                "teams": [{"slug": team} for team in teams]}
    return json.dumps(body)


NOT_PROTECTED = (1, "gh: Branch not protected (HTTP 404)")


class Work:
    def __init__(self, root, runner):
        self.root = root
        self.runner = runner
        self.repo = root / "work"
        run(["git", "init", "--quiet", "--initial-branch=main", self.repo.as_posix()])
        git(self.repo, "remote", "add", "origin", "https://github.com/owner/repo.git")
        self.plugins = []
        self.claude_version = "2.1.242"
        self.default_branch = "main"
        self.branches = {"main"}
        self.may_push = True
        self.labels = ["ready-for-agent"]
        self.rules = {}
        self.protections = {}
        self.target("main")
        self.install("skillworks")
        runner.stub("gh", does=self.gh)
        runner.stub("claude", does=self.claude)

    def target(self, branch, tracker="github"):
        loop = self.repo / "docs" / "agents" / "loop.json"
        loop.parent.mkdir(parents=True, exist_ok=True)
        loop.write_text(json.dumps({"tracker": tracker, "target-branch": branch}, indent=2) + "\n",
                        encoding="utf-8", newline="\n")

    def loop_file(self, text):
        (self.repo / "docs" / "agents" / "loop.json").write_text(text, encoding="utf-8", newline="\n")

    # Every call the preflight makes is answered, and any other one fails, so a new call cannot pass on a guess.
    def gh(self):
        line = " ".join(self.runner.calls[-1][1:])
        branches = "api repos/owner/repo/branches/"
        if line == "auth status":
            return Ran(0, "", "")
        if line == "api user --jq .login":
            return Ran(0, "me\n", "")
        if line == "repo view --json nameWithOwner --jq .nameWithOwner":
            return Ran(0, "owner/repo\n", "")
        if line == "api repos/owner/repo":
            return Ran(0, json.dumps({"has_issues": True, "default_branch": self.default_branch,
                                      "permissions": {"push": self.may_push}}), "")
        if line.startswith("api repos/owner/repo/rules/branches/"):
            branch = line.removeprefix("api repos/owner/repo/rules/branches/")
            return Ran(0, json.dumps([{"type": kind} for kind in self.rules.get(branch, [])]), "")
        if line.startswith(branches) and line.endswith("/protection"):
            status, said = self.protections.get(line.removeprefix(branches).removesuffix("/protection"),
                                                NOT_PROTECTED)
            return Ran(0, said, "") if status == 0 else Ran(status, "", said + "\n")
        if line.startswith(branches) and line.endswith(" --jq .name"):
            branch = line.removeprefix(branches).removesuffix(" --jq .name")
            if branch in self.branches:
                return Ran(0, branch + "\n", "")
            return Ran(1, "", "gh: Branch not found (HTTP 404)\n")
        if line == "label list --limit 200 --json name --jq .[].name":
            return Ran(0, "".join(label + "\n" for label in self.labels), "")
        if line == LABEL_CREATE:
            return Ran(0, "", "")
        return Ran(97, "", "unplanned gh call: " + line + "\n")

    def claude(self):
        line = " ".join(self.runner.calls[-1][1:])
        if line == "--version":
            return Ran(0, self.claude_version + " (Claude Code)\n", "")
        if line == "plugin list --json":
            return Ran(0, json.dumps(self.plugins), "")
        return Ran(97, "", "unplanned claude call: " + line + "\n")

    def protect(self, *held, users=(), teams=()):
        self.protections["main"] = (0, protection(*held, users=users, teams=teams))

    def cannot_read_protection(self, said):
        self.protections["main"] = (1, said)

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

    def install(self, name):
        home = self.root / "plugins" / f"{name}-{len(self.plugins)}"
        (home / ".claude-plugin").mkdir(parents=True)
        (home / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": name}), encoding="utf-8")
        folder = home / "output-styles"
        folder.mkdir(parents=True)
        (folder / f"{name}.md").write_text(FORCED.format(name=name), encoding="utf-8", newline="\n")
        self.plugins.append({"id": f"{name}@market", "scope": "user", "enabled": True, "installPath": str(home)})

    def settings(self, text):
        (self.repo / ".claude").mkdir(exist_ok=True)
        (self.repo / ".claude" / "settings.json").write_text(text, encoding="utf-8", newline="\n")


@pytest.fixture
def work(tmp_path, runner):
    return Work(tmp_path, runner)


def preflight(work, *args, where=None):
    out, err = io.StringIO(), io.StringIO()
    status = main(list(args), work.runner, out, err, where=str(where or work.repo))
    return Ran(status, out.getvalue(), err.getvalue())


def said(ran):
    return ran.out + ran.err


def test_settings_that_turn_auto_memory_off_draw_no_warning(work):
    work.settings('{"permissions": {"allow": []}, "autoMemoryEnabled": false}')

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert WARNING not in said(ran)
    assert "auto-memory off" in ran.out


def test_settings_without_the_key_warn_naming_the_key_and_the_file(work):
    work.settings('{"permissions": {"allow": []}}')

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert WARNING in ran.out


def test_settings_that_turn_auto_memory_on_warn(work):
    work.settings('{"autoMemoryEnabled": true}')

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert WARNING in ran.out


def test_no_settings_file_warns(work):
    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert WARNING in ran.out


def test_a_settings_file_that_is_not_json_warns_and_does_not_crash(work):
    work.settings('{"autoMemoryEnabled": false,')

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert WARNING in ran.out


def test_a_machine_without_node_still_checks_the_setting_and_the_output_styles(work):
    work.settings('{"autoMemoryEnabled": true}')
    work.install("pirate")
    work.runner.hide("node")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert WARNING in ran.out
    assert "warn  pirate@market " + STYLE_WARNING in ran.out
    assert "node" not in said(ran)
    assert work.runner.started("node") == []


def test_check_only_prints_the_same_warning_and_writes_no_label(work):
    work.settings('{"autoMemoryEnabled": true}')
    work.labels = []

    ran = preflight(work, "--check-only")

    assert ran.status == 0, said(ran)
    assert WARNING in ran.out
    assert "no labels were written" in ran.out
    assert work.runner.built("label") == []
    assert "Ready." not in ran.out


def test_a_missing_label_is_created(work):
    work.labels = []

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    label ready-for-agent created" in ran.out
    assert len(work.runner.built(LABEL_CREATE)) == 1


def test_a_label_that_is_there_is_left_alone(work):
    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    label ready-for-agent (already there, left alone)" in ran.out
    assert work.runner.built("label create") == []
    assert ran.out.endswith("\nReady. Next: the rest of /skillworks:skillworks-setup.\n")


def test_the_warning_comes_after_the_label_work(work):
    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert ran.out.index("label ready-for-agent") < ran.out.index(WARNING)


def test_the_preflight_reads_the_settings_at_the_top_of_the_repository(work):
    work.settings('{"autoMemoryEnabled": false}')
    below = work.repo / "src" / "deep"
    below.mkdir(parents=True)

    ran = preflight(work, where=below)

    assert ran.status == 0, said(ran)
    assert "auto-memory off" in ran.out
    assert WARNING not in said(ran)


def test_an_unknown_argument_prints_the_usage_and_starts_nothing(work):
    ran = preflight(work, "--no-such-flag")

    assert ran.status == 64
    assert ran.err == "usage: skillworks-preflight [--check-only]\n"
    assert work.runner.calls == []


@pytest.mark.parametrize("program, reason", [
    ("git", "FAIL  git is not installed\n"),
    ("claude", "FAIL  claude is not on PATH. The loop shells out to it.\n"),
])
def test_a_missing_program_fails_naming_it(work, program, reason):
    work.runner.hide(program)

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert ran.err == reason
    assert work.runner.calls == []


def test_a_folder_outside_a_repository_fails(work):
    outside = work.root / "outside"
    outside.mkdir()

    ran = preflight(work, where=outside)

    assert ran.status == 1, said(ran)
    assert ran.err == "FAIL  not inside a git repository\n"


def test_a_claude_older_than_2_1_242_warns_of_a_cold_prompt_cache(work):
    work.claude_version = "2.1.241"

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "warn  claude 2.1.241 predates 2.1.242" in ran.out
    assert COLD_CACHE in ran.out


def test_a_claude_of_2_1_1000_is_newer_than_2_1_242(work):
    work.claude_version = "2.1.1000"

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    claude 2.1.1000" in ran.out
    assert COLD_CACHE not in said(ran)


def test_the_gh_version_is_never_asked(work):
    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert work.runner.built("--version") == [["claude", "--version"]]


def test_a_missing_loop_file_fails_naming_the_command_that_writes_it(work):
    (work.repo / "docs" / "agents" / "loop.json").unlink()

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  docs/agents/loop.json is missing. Run seed-steering to write it." in ran.err
    assert "label ready-for-agent" not in ran.out


def test_a_loop_file_with_no_target_branch_fails(work):
    work.loop_file('{"tracker": "github"}\n')

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  docs/agents/loop.json names no target-branch." in ran.err


def test_a_loop_file_with_no_tracker_fails(work):
    work.loop_file('{"target-branch": "main"}\n')

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  docs/agents/loop.json names no tracker." in ran.err


def test_a_target_branch_split_across_lines_passes(work):
    work.loop_file('{\n  "tracker": "github",\n  "target-branch":\n    "main"\n}\n')

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch main" in ran.out


# A reader that matched text rather than JSON would take the last key it saw, which is develop.
def test_a_target_branch_nested_in_another_setting_is_not_the_target_branch(work):
    work.loop_file(json.dumps({"tracker": "github", "target-branch": "main", "was": {"target-branch": "develop"}}))

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch main" in ran.out


def test_a_target_branch_named_master_that_is_on_the_remote_passes(work):
    work.target("master")
    work.default_branch = "master"
    work.branches = {"master"}

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
    work.default_branch = "develop"
    work.branches = {"develop", "main"}

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch main" in ran.out


def test_in_spec_mode_a_protected_default_branch_passes(work):
    work.target("spec")
    work.rules["main"] = ["pull_request", "required_status_checks"]
    work.protect("enforced", "pull_request", "required_status_checks")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch spec, each reviewed into main" in ran.out
    assert "label ready-for-agent" in ran.out


def test_in_spec_mode_a_default_branch_missing_on_the_remote_fails(work):
    work.target("spec")
    work.branches = set()

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  the default branch main is not on owner/repo" in ran.err


def test_in_spec_mode_a_repo_that_refuses_this_login_a_push_fails(work):
    work.target("spec")
    work.may_push = False

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  me may not push to owner/repo, so the loop cannot land a ticket on a spec's branch." in ran.err


def test_a_repo_that_refuses_this_login_a_push_fails(work):
    work.may_push = False

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  me may not push to owner/repo, so the loop cannot land a ticket on main." in ran.err


def test_a_rule_that_refuses_a_push_to_main_fails_naming_the_rule(work):
    work.rules["main"] = ["deletion", "pull_request"]

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  a rule on main in owner/repo refuses a direct push (pull_request)" in ran.err


def test_a_rule_that_lets_a_push_through_passes(work):
    work.rules["main"] = ["deletion", "non_fast_forward"]

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "may push to main" in ran.out


@pytest.mark.parametrize("held", ["pull_request", "required_status_checks", "lock_branch"])
def test_classic_protection_that_refuses_a_push_to_main_fails_naming_the_protection(work, held):
    work.protect("enforced", held)

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert f"FAIL  classic branch protection on main in owner/repo refuses a direct push ({held})" in ran.err
    assert "label ready-for-agent" not in ran.out


def test_classic_protection_that_lets_admins_through_passes(work):
    work.protect("pull_request", "restrictions")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "me may push to main" in ran.out


def test_classic_protection_that_restricts_pushes_to_others_fails(work):
    work.protect("enforced", "restrictions", users=["someone"])

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  classic branch protection on main in owner/repo restricts who may push, and me is not one of them." in ran.err


def test_classic_protection_that_restricts_pushes_to_this_login_passes(work):
    work.protect("enforced", "restrictions", users=["someone", "me"])

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "me may push to main" in ran.out


def test_classic_protection_that_restricts_pushes_to_a_team_warns_and_passes(work):
    work.protect("enforced", "restrictions", teams=["builders"])

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "warn  classic branch protection on main in owner/repo lets teams push (builders)" in ran.out


def test_classic_protection_that_cannot_be_read_warns_and_passes(work):
    work.cannot_read_protection("gh: Must have admin rights to Repository. (HTTP 403)")

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
    work.runner.hide("gh")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch main" in ran.out
    assert "label ready-for-agent" not in ran.out
    assert work.runner.started("gh") == []


def test_with_the_files_tracker_a_bare_remote_on_a_shared_drive_passes(work):
    work.target("main", tracker="files")
    work.serve((work.root / "shared" / "repo.git").as_posix(), "main")
    work.runner.hide("gh")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch main" in ran.out


def test_with_the_files_tracker_a_target_branch_missing_on_the_remote_fails_naming_it(work):
    work.target("master", tracker="files")
    work.serve(GITLAB, "main")
    work.runner.hide("gh")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  the Target branch master in docs/agents/loop.json is not on origin." in ran.err


def test_with_the_files_tracker_in_spec_mode_the_default_branch_of_the_remote_passes(work):
    work.target("spec", tracker="files")
    work.serve(GITLAB, "main")
    work.runner.hide("gh")

    ran = preflight(work)

    assert ran.status == 0, said(ran)
    assert "ok    target-branch spec, each reviewed into main" in ran.out


def test_with_the_files_tracker_in_spec_mode_a_remote_with_no_default_branch_fails(work):
    work.target("spec", tracker="files")
    work.serve(GITLAB, "main")
    git(work.root / "remote.git", "symbolic-ref", "HEAD", "refs/heads/gone")
    work.runner.hide("gh")

    ran = preflight(work)

    assert ran.status == 1, said(ran)
    assert "FAIL  origin names no default branch" in ran.err


def test_with_the_files_tracker_check_only_passes_without_gh(work):
    work.target("main", tracker="files")
    work.serve(GITLAB, "main")
    work.runner.hide("gh")

    ran = preflight(work, "--check-only")

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


def test_the_preflight_command_fails_with_the_install_link_when_uv_is_missing(tmp_path):
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join(folder for folder in env["PATH"].split(os.pathsep)
                                  if not shutil.which("uv", path=folder))

    ran = launch("skillworks-preflight", where=tmp_path, env=env)

    assert ran.status == 1, said(ran)
    assert ran.err == ("FAIL  uv is not on PATH. The loop's scripts are Python and run under it. "
                       "https://docs.astral.sh/uv\n")


def test_the_preflight_command_names_itself_in_its_usage(tmp_path):
    ran = launch("skillworks-preflight", "--no-such-flag", where=tmp_path)

    assert ran.status == 64, said(ran)
    assert ran.err == "usage: skillworks-preflight [--check-only]\n"
