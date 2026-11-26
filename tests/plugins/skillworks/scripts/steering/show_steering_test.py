import io
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from conftest import PLUGIN, Ran, Repo, launch
from runner import Subprocess
from steering import show_steering

STEP_LIST = (
    "Name a step to see the Steering it reads: show-steering <step>\n"
    "\n"
    "The Grill\n"
    "  grill            Interviews you about the design, and writes the glossary and the ADRs as they settle.\n"
    "  gate             Sums up the design and waits for your yes.\n"
    "  write-spec       Writes the spec from the settled design and publishes it to the Tracker.\n"
    "\n"
    "The spec loop\n"
    "  cut              Breaks the spec into tickets, each with the tickets that block it.\n"
    "  build            Builds one ticket test first, and leaves the change uncommitted.\n"
    "  standards        Reviews the change against the rules and the review file for standards.\n"
    "  spec             Reviews the change against what the ticket and its spec asked for.\n"
    "  architecture     Reviews where the change sits, and runs the placement checks.\n"
    "  fix              Fixes what the three reviews found, or a Suite that went red.\n"
    "  sweep            Cuts the comments the comments rule does not keep.\n"
    "  suite            Runs every check in the Suite file, with no Session.\n"
    "  finish           Commits the ticket and closes it with its Closing note.\n"
    "  deepening-check  Looks for modules the spec left shallow, and files a ticket to deepen each one.\n"
    "  simplify-check   Looks for code the spec made harder than it has to be, and files one ticket to clean it up.\n"
    "  drift-check      Reads the finished work against the spec, and files one ticket for any Gap it finds.\n"
    "\n"
    "The step map: https://github.com/MalcolmMcNeely/skillworks/blob/main/docs/usage/the-loop/step-map.md\n"
)


@pytest.fixture
def repo(tmp_path):
    return Repo(tmp_path)


@pytest.fixture
def home(tmp_path):
    folder = tmp_path / "home"
    folder.mkdir()
    return folder


def write(root, name, text):
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def show(*argv, where, home=None):
    out, err = io.StringIO(), io.StringIO()
    status = show_steering.main(list(argv), Subprocess(), out, err, str(where), home)
    return Ran(status, out.getvalue(), err.getvalue())


def test_with_no_step_named_the_steps_of_the_dev_loop_are_listed_by_stage(repo):
    ran = show(where=repo.work)

    assert (ran.status, ran.out) == (0, STEP_LIST), ran.err


def test_a_name_that_is_not_a_step_is_turned_down_with_the_step_list(repo):
    ran = show("biuld", where=repo.work)

    assert (ran.status != 0, ran.out) == (True, "biuld is not a step.\n\n" + STEP_LIST), ran.err


def test_a_step_named_from_a_folder_below_the_repo_root_is_found(repo, home):
    write(repo.work, "CLAUDE.md", "# Rules\n")
    below = repo.work / "src" / "deep"
    below.mkdir(parents=True)

    ran = show("gate", where=below, home=home)

    assert (ran.status, ran.out) == (0, (
        "The Steering the gate step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "\n"
        "==> [repo] CLAUDE.md <==\n"
        "# Rules\n"
    )), ran.err


def test_a_step_with_only_always_files_lists_the_repo_claude_md_and_its_imports_then_their_text(repo, home):
    write(repo.work, "CLAUDE.md", "# Rules\n\n@docs/a.md\n")
    write(repo.work, "docs/a.md", "# A\n\n## Part\n\nText.\n")

    ran = show("gate", where=repo.work, home=home)

    assert (ran.status, ran.out) == (0, (
        "The Steering the gate step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  always     [repo]     docs/a.md\n"
        "\n"
        "==> [repo] CLAUDE.md <==\n"
        "# Rules\n"
        "\n"
        "@docs/a.md\n"
        "\n"
        "==> [repo] docs/a.md <==\n"
        "# A\n"
        "\n"
        "[repo]\n"
        "## Part\n"
        "\n"
        "Text.\n"
    )), ran.err


def test_a_step_with_on_demand_files_shows_each_file_of_a_folder_path_sorted_by_name(repo, home):
    write(repo.work, "CLAUDE.md", "# Rules\n")
    write(repo.work, "docs/skillworks/issue-tracker.md", "# Tracker\n")
    write(repo.work, "docs/skillworks/rules/words.md", "# Words\n")
    write(repo.work, "docs/skillworks/rules/comments.md", "# Comments\n")
    write(repo.work, "docs/skillworks/domain.md", "# Domain\n")
    write(repo.work, "docs/skillworks/review-standards.md", "# Standards\n")

    ran = show("standards", where=repo.work, home=home)

    assert (ran.status, ran.out) == (0, (
        "The Steering the standards step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  on demand  [repo]     docs/skillworks/issue-tracker.md\n"
        "  on demand  [repo]     docs/skillworks/rules/comments.md\n"
        "  on demand  [repo]     docs/skillworks/rules/words.md\n"
        "  on demand  [repo]     docs/skillworks/domain.md\n"
        "  on demand  [repo]     docs/skillworks/review-standards.md\n"
        "\n"
        "==> [repo] CLAUDE.md <==\n"
        "# Rules\n"
        "\n"
        "==> [repo] docs/skillworks/issue-tracker.md <==\n"
        "# Tracker\n"
        "\n"
        "==> [repo] docs/skillworks/rules/comments.md <==\n"
        "# Comments\n"
        "\n"
        "==> [repo] docs/skillworks/rules/words.md <==\n"
        "# Words\n"
        "\n"
        "==> [repo] docs/skillworks/domain.md <==\n"
        "# Domain\n"
        "\n"
        "==> [repo] docs/skillworks/review-standards.md <==\n"
        "# Standards\n"
    )), ran.err


def test_a_missing_file_is_marked_missing_and_the_rest_still_shows(repo, home):
    write(repo.work, "CLAUDE.md", "# Rules\n\n@docs/gone.md\n")
    write(repo.work, "docs/skillworks/suite.json", "{}\n")

    ran = show("suite", where=repo.work, home=home)

    assert (ran.status, ran.out) == (0, (
        "The Steering the suite step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  always     [repo]     docs/gone.md  missing\n"
        "  on demand  [repo]     docs/skillworks/suite.json\n"
        "\n"
        "==> [repo] CLAUDE.md <==\n"
        "# Rules\n"
        "\n"
        "@docs/gone.md\n"
        "\n"
        "==> [repo] docs/skillworks/suite.json <==\n"
        "{}\n"
    )), ran.err


def test_a_missing_on_demand_file_is_marked_missing_with_exit_code_0(repo, home):
    write(repo.work, "CLAUDE.md", "# Rules\n")

    ran = show("sweep", where=repo.work, home=home)

    assert (ran.status, ran.out) == (0, (
        "The Steering the sweep step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  on demand  [repo]     docs/skillworks/rules/comments.md  missing\n"
        "\n"
        "==> [repo] CLAUDE.md <==\n"
        "# Rules\n"
    )), ran.err


def test_the_deepening_check_shows_its_own_file_the_tracker_and_the_domain_docs_even_when_turned_off(repo, home):
    write(repo.work, "CLAUDE.md", "# Rules\n")
    write(repo.work, "docs/skillworks/deepening-check.md", "# Deepening\n\n```yaml\nlimit: 0\n```\n")
    write(repo.work, "docs/skillworks/issue-tracker.md", "# Tracker\n")
    write(repo.work, "docs/skillworks/domain.md", "# Domain\n")

    ran = show("deepening-check", where=repo.work, home=home)

    assert (ran.status, ran.out) == (0, (
        "The Steering the deepening-check step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  on demand  [repo]     docs/skillworks/deepening-check.md\n"
        "  on demand  [repo]     docs/skillworks/issue-tracker.md\n"
        "  on demand  [repo]     docs/skillworks/domain.md\n"
        "\n"
        "==> [repo] CLAUDE.md <==\n"
        "# Rules\n"
        "\n"
        "==> [repo] docs/skillworks/deepening-check.md <==\n"
        "# Deepening\n"
        "\n"
        "```yaml\n"
        "limit: 0\n"
        "```\n"
        "\n"
        "==> [repo] docs/skillworks/issue-tracker.md <==\n"
        "# Tracker\n"
        "\n"
        "==> [repo] docs/skillworks/domain.md <==\n"
        "# Domain\n"
    )), ran.err


def test_the_simplify_check_shows_its_own_file_and_the_tracker_even_when_turned_off(repo, home):
    write(repo.work, "CLAUDE.md", "# Rules\n")
    write(repo.work, "docs/skillworks/simplify-check.md", "# Simplify\n\n```yaml\nenabled: false\n```\n")
    write(repo.work, "docs/skillworks/issue-tracker.md", "# Tracker\n")

    ran = show("simplify-check", where=repo.work, home=home)

    assert (ran.status, ran.out) == (0, (
        "The Steering the simplify-check step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  on demand  [repo]     docs/skillworks/simplify-check.md\n"
        "  on demand  [repo]     docs/skillworks/issue-tracker.md\n"
        "\n"
        "==> [repo] CLAUDE.md <==\n"
        "# Rules\n"
        "\n"
        "==> [repo] docs/skillworks/simplify-check.md <==\n"
        "# Simplify\n"
        "\n"
        "```yaml\n"
        "enabled: false\n"
        "```\n"
        "\n"
        "==> [repo] docs/skillworks/issue-tracker.md <==\n"
        "# Tracker\n"
    )), ran.err


def test_the_drift_check_shows_the_loop_file_the_tracker_the_domain_docs_and_the_surfaces(repo, home):
    write(repo.work, "CLAUDE.md", "# Rules\n")
    write(repo.work, "docs/skillworks/loop.json", '{"tracker": "github"}\n')
    write(repo.work, "docs/skillworks/issue-tracker.md", "# Tracker\n")
    write(repo.work, "docs/skillworks/domain.md", "# Domain\n")
    write(repo.work, "docs/skillworks/surfaces.md", "# Surfaces\n")

    ran = show("drift-check", where=repo.work, home=home)

    assert (ran.status, ran.out) == (0, (
        "The Steering the drift-check step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  on demand  [repo]     docs/skillworks/loop.json\n"
        "  on demand  [repo]     docs/skillworks/issue-tracker.md\n"
        "  on demand  [repo]     docs/skillworks/domain.md\n"
        "  on demand  [repo]     docs/skillworks/surfaces.md\n"
        "\n"
        "==> [repo] CLAUDE.md <==\n"
        "# Rules\n"
        "\n"
        "==> [repo] docs/skillworks/loop.json <==\n"
        '{"tracker": "github"}\n'
        "\n"
        "==> [repo] docs/skillworks/issue-tracker.md <==\n"
        "# Tracker\n"
        "\n"
        "==> [repo] docs/skillworks/domain.md <==\n"
        "# Domain\n"
        "\n"
        "==> [repo] docs/skillworks/surfaces.md <==\n"
        "# Surfaces\n"
    )), ran.err


def file_list(out):
    return out.split("\n\n==> ")[0] + "\n"


def test_under_sidecar_steering_both_claude_md_files_show_and_on_demand_files_come_from_the_sidecar(repo, home):
    sidecar = repo.work.parent / "work-skillworks"
    write(repo.work, "CLAUDE.md", "# Repo rules\n\n@docs/r.md\n")
    write(repo.work, "docs/r.md", "# R\n")
    write(repo.work, "docs/skillworks/rules/comments.md", "# The repo copy\n")
    write(sidecar, "docs/skillworks/loop.json", '{"tracker": "files", "target-branch": "pr"}\n')
    write(sidecar, "CLAUDE.md", "# Team rules\n\n@docs/team.md\n")
    write(sidecar, "docs/team.md", "# Team\n")
    write(sidecar, "docs/skillworks/rules/comments.md", "# The Sidecar copy\n")

    ran = show("sweep", where=repo.work, home=home)

    assert (ran.status, file_list(ran.out)) == (0, (
        "The Steering the sweep step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  always     [repo]     docs/r.md\n"
        "  always     [Sidecar]  CLAUDE.md\n"
        "  always     [Sidecar]  docs/team.md\n"
        "  on demand  [Sidecar]  docs/skillworks/rules/comments.md\n"
    )), ran.err


def test_the_users_claude_md_and_its_imports_show_first_labelled_user(repo, home):
    write(home, ".claude/CLAUDE.md", "# Mine\n\n@rules/mine.md\n")
    write(home, ".claude/rules/mine.md", "## My part\n\nText.\n")

    ran = show("gate", where=repo.work, home=home)

    assert (ran.status, ran.out) == (0, (
        "The Steering the gate step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md\n"
        "  always     [user]     ~/.claude/rules/mine.md\n"
        "  always     [repo]     CLAUDE.md  missing\n"
        "\n"
        "==> [user] ~/.claude/CLAUDE.md <==\n"
        "# Mine\n"
        "\n"
        "@rules/mine.md\n"
        "\n"
        "==> [user] ~/.claude/rules/mine.md <==\n"
        "[user]\n"
        "## My part\n"
        "\n"
        "Text.\n"
    )), ran.err


def test_an_import_deeper_than_5_levels_is_left_out(repo, home):
    write(repo.work, "CLAUDE.md", "@l1.md\n")
    for level in range(1, 7):
        write(repo.work, "l{}.md".format(level), "@l{}.md\n".format(level + 1))

    ran = show("gate", where=repo.work, home=home)

    assert (ran.status, file_list(ran.out)) == (0, (
        "The Steering the gate step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  always     [repo]     l1.md\n"
        "  always     [repo]     l2.md\n"
        "  always     [repo]     l3.md\n"
        "  always     [repo]     l4.md\n"
        "  always     [repo]     l5.md\n"
    )), ran.err


def test_an_import_cycle_shows_each_file_once(repo, home):
    write(repo.work, "CLAUDE.md", "@a.md\n")
    write(repo.work, "a.md", "@b.md\n")
    write(repo.work, "b.md", "@a.md\n@CLAUDE.md\n")

    ran = show("gate", where=repo.work, home=home)

    assert (ran.status, file_list(ran.out)) == (0, (
        "The Steering the gate step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  always     [repo]     a.md\n"
        "  always     [repo]     b.md\n"
    )), ran.err


def test_an_import_resolves_from_the_folder_of_the_file_that_holds_it(repo, home):
    write(repo.work, "CLAUDE.md", "@docs/a.md\n")
    write(repo.work, "docs/a.md", "@b.md\n")
    write(repo.work, "docs/b.md", "B\n")

    ran = show("gate", where=repo.work, home=home)

    assert (ran.status, file_list(ran.out)) == (0, (
        "The Steering the gate step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  always     [repo]     docs/a.md\n"
        "  always     [repo]     docs/b.md\n"
    )), ran.err


def test_an_import_from_the_home_folder_shows_as_a_user_file(repo, home):
    write(repo.work, "CLAUDE.md", "@~/.claude/mine.md\n")
    write(home, ".claude/mine.md", "Mine\n")

    ran = show("gate", where=repo.work, home=home)

    assert (ran.status, file_list(ran.out)) == (0, (
        "The Steering the gate step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  always     [user]     ~/.claude/mine.md\n"
    )), ran.err


def test_an_import_inside_a_sentence_loads_and_one_inside_code_does_not(repo, home):
    write(repo.work, "CLAUDE.md", (
        "Read @docs/a.md first, and mail me@example.invalid.\n"
        "\n"
        "Write `@docs/span.md` to import.\n"
        "\n"
        "```\n"
        "@docs/fenced.md\n"
        "```\n"
    ))
    for name in ("a", "span", "fenced"):
        write(repo.work, "docs/{}.md".format(name), "Text.\n")

    ran = show("gate", where=repo.work, home=home)

    assert (ran.status, file_list(ran.out)) == (0, (
        "The Steering the gate step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  always     [repo]     docs/a.md\n"
    )), ran.err


API_RULE = "---\npaths:\n  - \"src/api/**/*.ts\"\n  - tests/api/**\n---\n\n## The API\n\nText.\n"

WEB_RULE = "---\npaths: [\"src/**/*.{ts,tsx}\"]\n---\n\nUse hooks.\n"


def test_path_rules_from_the_repo_and_the_user_are_listed_last_under_may_load_with_their_globs(repo, home):
    write(repo.work, "CLAUDE.md", "# Rules\n")
    write(repo.work, ".claude/rules/api.md", API_RULE)
    write(home, ".claude/rules/web.md", WEB_RULE)

    ran = show("gate", where=repo.work, home=home)

    assert (ran.status, ran.out) == (0, (
        "The Steering the gate step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "\n"
        "==> [repo] CLAUDE.md <==\n"
        "# Rules\n"
        "\n"
        "May load:\n"
        "\n"
        "  [user]     ~/.claude/rules/web.md  src/**/*.{ts,tsx}\n"
        "  [repo]     .claude/rules/api.md  src/api/**/*.ts, tests/api/**\n"
    )), ran.err


def test_a_rule_with_no_paths_always_loads_and_shows_its_text(repo, home):
    write(repo.work, "CLAUDE.md", "# Rules\n")
    write(repo.work, ".claude/rules/style/plain.md", "## Style\n\nShort lines.\n")

    ran = show("gate", where=repo.work, home=home)

    assert (ran.status, ran.out) == (0, (
        "The Steering the gate step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "  always     [repo]     .claude/rules/style/plain.md\n"
        "\n"
        "==> [repo] CLAUDE.md <==\n"
        "# Rules\n"
        "\n"
        "==> [repo] .claude/rules/style/plain.md <==\n"
        "[repo]\n"
        "## Style\n"
        "\n"
        "Short lines.\n"
    )), ran.err


def test_path_shows_each_rule_a_read_of_that_file_would_load_with_its_text(repo, home):
    write(repo.work, "CLAUDE.md", "# Rules\n")
    write(repo.work, ".claude/rules/api.md", API_RULE)
    write(repo.work, ".claude/rules/docs.md", "---\npaths: docs/**/*.md\n---\n\nPlain words.\n")
    write(home, ".claude/rules/web.md", WEB_RULE)

    ran = show("gate", "--path", "src/api/orders.ts", where=repo.work, home=home)

    assert (ran.status, ran.out.split("\n\nA read of ")[-1]) == (0, (
        "src/api/orders.ts loads:\n"
        "\n"
        "==> [user] ~/.claude/rules/web.md <==\n"
        + WEB_RULE +
        "\n"
        "==> [repo] .claude/rules/api.md <==\n"
        "---\n"
        "paths:\n"
        "  - \"src/api/**/*.ts\"\n"
        "  - tests/api/**\n"
        "---\n"
        "\n"
        "[repo]\n"
        "## The API\n"
        "\n"
        "Text.\n"
    )), ran.err


def test_path_with_no_matching_rule_says_so_and_exits_with_0(repo, home):
    write(repo.work, "CLAUDE.md", "# Rules\n")
    write(repo.work, ".claude/rules/api.md", API_RULE)

    ran = show("gate", "--path", "src/web/page.tsx", where=repo.work, home=home)

    assert (ran.status, ran.out) == (0, (
        "The Steering the gate step reads:\n"
        "\n"
        "  always     [user]     ~/.claude/CLAUDE.md  missing\n"
        "  always     [repo]     CLAUDE.md\n"
        "\n"
        "==> [repo] CLAUDE.md <==\n"
        "# Rules\n"
        "\n"
        "No path rule matches src/web/page.tsx.\n"
    )), ran.err


def hook_files(where):
    payload = {"cwd": str(where), "session_id": "hook-session", "hook_event_name": "SessionStart", "source": "startup"}
    done = subprocess.run(
        ["node", (PLUGIN / "scripts" / "hooks" / "session-steering.mjs").as_posix()],
        input=json.dumps(payload), capture_output=True, encoding="utf-8")
    context = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
    return re.findall(r"^## (\S+)$", context, re.MULTILINE)


def always_files_shown(out, label):
    return [line.split()[-1] for line in file_list(out).splitlines()
            if line.startswith("  always     [{}]".format(label)) and not line.endswith("missing")]


def test_the_always_walk_finds_the_same_sidecar_files_as_the_sidecar_hook(repo, home):
    sidecar = repo.work.parent / "work-skillworks"
    write(sidecar, "docs/skillworks/loop.json", '{"tracker": "files", "target-branch": "pr"}\n')
    write(sidecar, "CLAUDE.md", "# Team\n\n@docs/a.md\n  @docs/b.md  \n@docs/gone.md\n@l1.md\n")
    write(sidecar, "docs/a.md", "@b.md\n@../CLAUDE.md\n")
    write(sidecar, "docs/b.md", "Read @c.md first, and not `@d.md`.\n\n```\n@e.md\n```\n")
    for name in ("c", "d", "e"):
        write(sidecar, "docs/{}.md".format(name), "Text.\n")
    for level in range(1, 7):
        write(sidecar, "l{}.md".format(level), "@l{}.md\n".format(level + 1))

    ran = show("gate", where=repo.work, home=home)

    shown = always_files_shown(ran.out, "Sidecar")
    assert (shown[:1], shown) == (["CLAUDE.md"], hook_files(repo.work)), ran.err


def test_a_folder_outside_a_git_repository_is_turned_down(tmp_path):
    outside = tmp_path / "loose"
    outside.mkdir()

    ran = show(where=outside)

    assert (ran.status != 0, ran.err) == (True, "FAIL  {} is not in a git repository.\n".format(outside))


def test_the_command_prints_the_step_list_to_the_caller(repo):
    ran = launch("show-steering", where=repo.work)

    assert (ran.status, ran.out) == (0, STEP_LIST), ran.err


def test_the_command_labels_each_text_of_the_repo_and_the_sidecar_with_its_layer(repo, home):
    sidecar = repo.work.parent / "work-skillworks"
    write(repo.work, "CLAUDE.md", "# Repo rules\n")
    write(sidecar, "docs/skillworks/loop.json", '{"tracker": "files", "target-branch": "pr"}\n')
    write(sidecar, "CLAUDE.md", "# Team rules\n")
    write(sidecar, "docs/skillworks/rules/comments.md", "# The Sidecar copy\n")

    ran = launch("show-steering", "sweep", where=repo.work,
                 env=dict(os.environ, HOME=str(home), USERPROFILE=str(home)))

    assert (ran.status, [line.split()[-2:] for line in file_list(ran.out).splitlines()[2:]
                         if "[user]" not in line]) == (0, [
        ["[repo]", "CLAUDE.md"], ["[Sidecar]", "CLAUDE.md"],
        ["[Sidecar]", "docs/skillworks/rules/comments.md"]]), ran.err
