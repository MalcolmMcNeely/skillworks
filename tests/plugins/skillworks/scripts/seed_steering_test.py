import io
import json
import re

import seed_steering
from conftest import PLUGIN, Ran, git, launch
from suite import Suite

SETUP = PLUGIN / "skills" / "skillworks-setup"

WHERE = {
    "comments.md": ".claude/rules/comments.md",
    "determinism.md": ".claude/rules/determinism.md",
    "file-placement.md": ".claude/rules/file-placement.md",
    "words.md": ".claude/rules/words.md",
    "issue-tracker.md": "docs/agents/issue-tracker.md",
    "domain.md": "docs/agents/domain.md",
    "placement-checks.md": "docs/agents/placement-checks.md",
    "smell-baseline.md": "docs/agents/smell-baseline.md",
    "arrangement-baseline.md": "docs/agents/arrangement-baseline.md",
    "suite.json": "docs/agents/suite.json",
}

WORKING_FOLDERS = [".spec-loop/", ".handoff/", ".claude/worktrees/"]


def run_seed(runner, where):
    out, err = io.StringIO(), io.StringIO()
    status = seed_steering.main([where.as_posix()], runner, out, err)
    return Ran(status, out.getvalue(), err.getvalue())


def settings_block(path):
    text = path.read_text(encoding="utf-8")
    blocks = re.findall(r"```yaml\n(.*?)```", text, re.DOTALL)
    assert len(blocks) == 1, path
    return blocks[0].splitlines()


def seeded(name):
    return (SETUP / "seeds" / name).read_text(encoding="utf-8")


def test_an_empty_repo_gets_every_seed(repo, runner):
    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    for seed, place in WHERE.items():
        assert (repo.work / place).read_text(encoding="utf-8") == seeded(seed), place
        assert "wrote {}\n".format(place) in ran.out


def test_the_seeds_folder_holds_the_listed_seeds_and_nothing_else():
    assert sorted(path.name for path in (SETUP / "seeds").iterdir()) == sorted(WHERE)


def test_the_rules_arrive_with_their_settings_empty(repo, runner):
    run_seed(runner, repo.work)
    rules = repo.work / ".claude" / "rules"

    placement = settings_block(rules / "file-placement.md")
    assert "slices: []" in placement
    assert "concerns: []" in placement
    assert "test-roots: {}" in placement
    assert "max-types-per-folder: 10" in placement
    assert "banned-words: {}" in settings_block(rules / "words.md")
    determinism = settings_block(rules / "determinism.md")
    assert "contexts: []" in determinism
    assert "clock: TimeProvider" in determinism
    assert "doc-comments: false" in settings_block(rules / "comments.md")


def test_a_seed_already_there_is_kept_and_its_difference_shown(repo, runner):
    edited = repo.work / "docs" / "agents" / "issue-tracker.md"
    edited.parent.mkdir(parents=True)
    edited.write_text("# Our own tracker notes\n", encoding="utf-8", newline="\n")

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert edited.read_text(encoding="utf-8") == "# Our own tracker notes\n"
    assert "kept docs/agents/issue-tracker.md, which differs from the seed:\n" in ran.out
    assert "-# Our own tracker notes\n" in ran.out
    assert "+# Issue tracker: GitHub\n" in ran.out
    assert "wrote docs/agents/issue-tracker.md" not in ran.out


def test_a_seed_already_there_unchanged_says_so_and_shows_nothing(repo, runner):
    run_seed(runner, repo.work)

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert "kept docs/agents/suite.json, the same as the seed\n" in ran.out
    assert "differs" not in ran.out


def test_the_issue_tracker_seed_holds_the_two_conventions():
    tracker = seeded("issue-tracker.md")

    assert "### Two conventions the loop leans on" in tracker
    assert "`Ticket: #<n>`" in tracker
    assert "gh issue close <n> --comment" in tracker


def test_the_starting_suite_is_valid_and_left_empty_is_not_ready(repo, runner):
    run_seed(runner, repo.work)

    parsed = json.loads((repo.work / "docs" / "agents" / "suite.json").read_text(encoding="utf-8"))
    ran = Suite(runner, repo.work).run()

    assert parsed == {"runs": 1, "checks": []}
    assert not ran.passed
    assert not ran.ready


def test_the_working_folders_are_ignored_once(repo, runner):
    (repo.work / ".gitignore").write_text(".handoff/\n", encoding="utf-8", newline="\n")

    run_seed(runner, repo.work)
    ran = run_seed(runner, repo.work)

    lines = (repo.work / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ran.status == 0, ran.err
    for folder in WORKING_FOLDERS:
        assert lines.count(folder) == 1, folder
    assert lines[0] == ".handoff/"


def test_the_allowlist_names_the_short_commands_and_no_tool_of_a_suite():
    allowed = json.loads((SETUP / "settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]
    commands = sorted(path.name for path in (PLUGIN / "bin").iterdir())

    assert len(commands) == 5
    for command in commands:
        assert "Bash({}:*)".format(command) in allowed
    assert "Bash(git commit:*)" in allowed
    assert "Bash(git push:*)" in allowed
    assert "Bash(gh issue:*)" in allowed
    assert "Bash(gh api:*)" in allowed
    for entry in allowed:
        tool = entry[len("Bash("):].split(" ")[0].split(":")[0]
        assert tool in ["gh", "git"] + commands, entry


def test_setup_writes_no_output_style(repo, runner):
    settings = json.loads((SETUP / "settings.json").read_text(encoding="utf-8"))

    run_seed(runner, repo.work)

    assert "outputStyle" not in settings
    assert not (repo.work / ".claude" / "output-styles").exists()
    assert not list(SETUP.rglob("*output-style*"))
    assert "outputStyle" not in (SETUP / "SKILL.md").read_text(encoding="utf-8")


# Each is a name only this repository uses, so finding one means a seed was copied, not written.
THIS_REPO = ["Skillworks.", "slnx", "Studio", "Dashboard", "Loki", "Aspire", "dotnet", "npm",
             "dependency-cruiser", "ADR 00", "../adr/", "tests/plugins"]


def test_the_seeds_carry_no_fact_about_this_repo():
    names = sorted(WHERE)
    assert len(names) == 10
    for name in names:
        text = seeded(name)
        for fact in THIS_REPO:
            assert fact not in text, "{} names {}".format(name, fact)


def test_the_seed_command_seeds_the_top_of_the_repository(repo):
    below = repo.work / "src" / "deep"
    below.mkdir(parents=True)

    ran = launch("seed-steering", where=below)

    assert ran.status == 0, ran.err
    assert (repo.work / "docs" / "agents" / "suite.json").is_file()
    assert not (below / "docs").exists()
    assert git(repo.work, "status", "--porcelain", "--", "docs").strip()
