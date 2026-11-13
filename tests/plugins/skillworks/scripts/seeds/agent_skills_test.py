import io

import pytest
from conftest import Ran, write_loop
from context_backfill.context_map import with_multi_context
from seeds import agent_skills

BASE = "docs/skillworks/.seeds/agent-skills.md"

RULES = ["comments.md", "testing.md"]

GITHUB_SINGLE = """## Agent skills

### Issue tracker

GitHub Issues, driven by the `gh` CLI. A spec is a parent issue; its tickets are its sub-issues. See `docs/skillworks/issue-tracker.md`.

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/skillworks/domain.md`.

### Steering

The rules in `docs/skillworks/rules/`, the review files in `docs/skillworks/`, and the Suite in `docs/skillworks/suite.json`. The team owns them.

### Rules

The rules load into every session through these imports. Each one lives in `docs/skillworks/rules/`.

@docs/skillworks/rules/comments.md
@docs/skillworks/rules/testing.md
"""


def set_up(work, rules=RULES):
    write_loop(work, "main")
    for rule in rules:
        write(work / "docs" / "skillworks" / "rules" / rule, "# {}\n".format(rule))


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def read(path):
    return path.read_text(encoding="utf-8")


def seed(runner, work, *flags, tracker="github", folder="docs/adr", contexts="single"):
    out, err = io.StringIO(), io.StringIO()
    argv = ["--tracker", tracker, "--adr-folder", folder, "--contexts", contexts, *flags]
    status = agent_skills.main(argv, runner, out, err, work.as_posix())
    return Ran(status, out.getvalue(), err.getvalue())


def test_a_repo_with_no_claude_md_gets_one_holding_the_block_and_its_base_copy(repo, runner):
    set_up(repo.work)

    ran = seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert read(repo.work / "CLAUDE.md") == GITHUB_SINGLE
    assert read(repo.work / BASE) == GITHUB_SINGLE
    assert "wrote CLAUDE.md\n" in ran.out


OWN_TRACKER = "Our tracker is GitHub, and the board lives in Projects.\n"
SEED_TRACKER = ("GitHub Issues, driven by the `gh` CLI. A spec is a parent issue; its tickets are its sub-issues. "
                "See `docs/skillworks/issue-tracker.md`.\n")
OLDER_TRACKER = "GitHub Issues, through `gh`. See `docs/skillworks/issue-tracker.md`.\n"
SEED_STEERING = "The team owns them.\n"
OLDER_STEERING = "The team keeps them.\n"


def on_disk(folder):
    return {path.relative_to(folder).as_posix(): path.read_bytes()
            for path in folder.rglob("*") if path.is_file() and ".git" not in path.relative_to(folder).parts}


def seeded_by_an_older_plugin(runner, work, base, held):
    set_up(work)
    seed(runner, work)
    write(work / BASE, base)
    write(work / "CLAUDE.md", held)


def older(block):
    return block.replace(SEED_STEERING, OLDER_STEERING)


def test_a_second_run_on_an_unchanged_repo_keeps_the_same_block(repo, runner):
    set_up(repo.work)
    seed(runner, repo.work)
    before = on_disk(repo.work)

    ran = seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert "kept CLAUDE.md, the same as the seed\n" in ran.out
    assert on_disk(repo.work) == before


def test_a_block_nobody_edited_is_brought_up_to_the_new_seed(repo, runner):
    seeded_by_an_older_plugin(runner, repo.work, older(GITHUB_SINGLE), older(GITHUB_SINGLE))

    ran = seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert read(repo.work / "CLAUDE.md") == GITHUB_SINGLE
    assert read(repo.work / BASE) == GITHUB_SINGLE
    assert "updated CLAUDE.md\n" in ran.out
    assert "+++ new-seed/CLAUDE.md\n" in ran.out


def test_an_edit_to_the_block_is_kept_when_the_seed_did_not_move(repo, runner):
    set_up(repo.work)
    seed(runner, repo.work)
    edited = GITHUB_SINGLE.replace(SEED_TRACKER, OWN_TRACKER)
    write(repo.work / "CLAUDE.md", edited)

    ran = seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert read(repo.work / "CLAUDE.md") == edited
    assert "kept CLAUDE.md, which you edited\n" in ran.out


def test_an_edit_and_a_change_to_the_seed_in_other_lines_are_merged(repo, runner):
    seeded_by_an_older_plugin(runner, repo.work, older(GITHUB_SINGLE),
                              older(GITHUB_SINGLE).replace(SEED_TRACKER, OWN_TRACKER))

    ran = seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert read(repo.work / "CLAUDE.md") == GITHUB_SINGLE.replace(SEED_TRACKER, OWN_TRACKER)
    assert read(repo.work / BASE) == GITHUB_SINGLE
    assert "merged CLAUDE.md, applying the seed's change:\n" in ran.out


def overlapping(runner, work):
    older_block = GITHUB_SINGLE.replace(SEED_TRACKER, OLDER_TRACKER)
    seeded_by_an_older_plugin(runner, work, older_block, older_block.replace(OLDER_TRACKER, OWN_TRACKER))


def test_an_edit_and_a_change_to_the_same_lines_ask_and_write_nothing(repo, runner):
    overlapping(runner, repo.work)
    before = on_disk(repo.work)

    ran = seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert on_disk(repo.work) == before
    assert "asks CLAUDE.md, where your edit and the seed's change overlap:\n" in ran.out
    assert "yours | " + OWN_TRACKER in ran.out
    assert "seed  | " + SEED_TRACKER in ran.out
    assert "Nothing was written. Run again with --keep" in ran.out


def test_an_overlap_answered_with_yours_keeps_the_edit_and_the_base_copy_takes_the_seed(repo, runner):
    overlapping(runner, repo.work)

    ran = seed(runner, repo.work, "--keep", "CLAUDE.md:1=yours")

    assert ran.status == 0, ran.err
    assert read(repo.work / "CLAUDE.md") == GITHUB_SINGLE.replace(SEED_TRACKER, OWN_TRACKER)
    assert read(repo.work / BASE) == GITHUB_SINGLE


def test_an_overlap_answered_with_the_seed_takes_the_seeds_lines(repo, runner):
    overlapping(runner, repo.work)

    ran = seed(runner, repo.work, "--keep", "CLAUDE.md:1=seed")

    assert ran.status == 0, ran.err
    assert read(repo.work / "CLAUDE.md") == GITHUB_SINGLE


def test_an_overlap_answered_with_a_blend_takes_the_blends_text(repo, runner, tmp_path):
    overlapping(runner, repo.work)
    blend = tmp_path / "blend.txt"
    write(blend, "GitHub Issues, driven by `gh`, with the board in Projects.")

    ran = seed(runner, repo.work, "--blend", "CLAUDE.md:1=" + blend.as_posix())

    assert ran.status == 0, ran.err
    assert read(repo.work / "CLAUDE.md") == GITHUB_SINGLE.replace(
        SEED_TRACKER, "GitHub Issues, driven by `gh`, with the board in Projects.\n")


def test_a_choice_that_names_no_overlap_is_refused_and_nothing_is_written(repo, runner):
    set_up(repo.work)
    seed(runner, repo.work)
    before = on_disk(repo.work)

    ran = seed(runner, repo.work, "--keep", "CLAUDE.md:1=seed")

    assert ran.status == 1
    assert "CLAUDE.md:1 names no overlap" in ran.err
    assert on_disk(repo.work) == before


def with_no_base_copy(work):
    set_up(work)
    write(work / "CLAUDE.md", "# Repo\n\n" + GITHUB_SINGLE.replace(SEED_TRACKER, OWN_TRACKER))


def test_a_block_with_no_base_copy_shows_the_difference_and_writes_nothing(repo, runner):
    with_no_base_copy(repo.work)
    before = on_disk(repo.work)

    ran = seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert on_disk(repo.work) == before
    assert "kept CLAUDE.md, which differs from the seed:\n" in ran.out
    assert "-" + OWN_TRACKER in ran.out
    assert "+" + SEED_TRACKER in ran.out
    assert "Nothing was written. Run again with --settled" in ran.out


def test_a_settled_block_is_kept_as_it_is_left_and_gets_its_base_copy(repo, runner):
    with_no_base_copy(repo.work)

    ran = seed(runner, repo.work, "--settled", "CLAUDE.md")

    assert ran.status == 0, ran.err
    assert read(repo.work / "CLAUDE.md") == "# Repo\n\n" + GITHUB_SINGLE.replace(SEED_TRACKER, OWN_TRACKER)
    assert read(repo.work / BASE) == GITHUB_SINGLE
    assert "kept CLAUDE.md, as you settled it, and wrote its base copy\n" in ran.out


def test_a_settling_of_a_block_that_has_a_base_copy_is_refused_and_nothing_is_written(repo, runner):
    set_up(repo.work)
    seed(runner, repo.work)
    write(repo.work / "CLAUDE.md", GITHUB_SINGLE.replace(SEED_TRACKER, OWN_TRACKER))
    before = on_disk(repo.work)

    ran = seed(runner, repo.work, "--settled", "CLAUDE.md")

    assert ran.status == 1
    assert "Nothing was written." in ran.err
    assert on_disk(repo.work) == before


def test_a_repo_with_agents_md_and_no_claude_md_gets_the_block_in_agents_md(repo, runner):
    set_up(repo.work)
    write(repo.work / "AGENTS.md", "# Agents\n")

    ran = seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert read(repo.work / "AGENTS.md") == "# Agents\n\n" + GITHUB_SINGLE
    assert not (repo.work / "CLAUDE.md").exists()
    assert "wrote AGENTS.md\n" in ran.out


def test_a_switch_to_multi_context_made_by_context_backfill_is_taken_with_no_question(repo, runner):
    set_up(repo.work)
    seed(runner, repo.work)
    edited = GITHUB_SINGLE.replace(SEED_STEERING, "The team owns them, and reviews them each quarter.\n")
    write(repo.work / "CLAUDE.md", with_multi_context(edited, "docs/adr"))

    ran = seed(runner, repo.work, contexts="multi")

    assert ran.status == 0, ran.err
    assert "asks" not in ran.out
    assert read(repo.work / "CLAUDE.md") == with_multi_context(edited, "docs/adr")
    assert read(repo.work / BASE) == with_multi_context(GITHUB_SINGLE, "docs/adr")


def test_a_new_rule_file_adds_its_import_to_the_block(repo, runner):
    set_up(repo.work)
    seed(runner, repo.work)
    write(repo.work / "docs" / "skillworks" / "rules" / "words.md", "# Words\n")

    ran = seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert read(repo.work / "CLAUDE.md") == GITHUB_SINGLE + "@docs/skillworks/rules/words.md\n"
    assert "updated CLAUDE.md\n" in ran.out


def test_text_outside_the_block_is_left_alone(repo, runner):
    set_up(repo.work)
    write(repo.work / BASE, older(GITHUB_SINGLE))
    write(repo.work / "CLAUDE.md",
          "# Repo\n\nIntro.\n\n" + older(GITHUB_SINGLE) + "\n\n## Working here\n\nKeep this.\n")

    ran = seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert read(repo.work / "CLAUDE.md") == (
        "# Repo\n\nIntro.\n\n" + GITHUB_SINGLE + "\n\n## Working here\n\nKeep this.\n")


def test_a_claude_md_with_no_block_gets_it_after_its_own_text(repo, runner):
    set_up(repo.work)
    write(repo.work / "CLAUDE.md", "# Repo\n\nIntro.\n")

    ran = seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert read(repo.work / "CLAUDE.md") == "# Repo\n\nIntro.\n\n" + GITHUB_SINGLE
    assert "wrote CLAUDE.md\n" in ran.out


def test_a_deleted_block_is_written_again(repo, runner):
    set_up(repo.work)
    seed(runner, repo.work)
    write(repo.work / "CLAUDE.md", "# Repo\n")

    ran = seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert read(repo.work / "CLAUDE.md") == "# Repo\n\n" + GITHUB_SINGLE
    assert "wrote CLAUDE.md\n" in ran.out


def test_the_files_tracker_line_names_the_specs_folder(repo, runner):
    set_up(repo.work)

    seed(runner, repo.work, tracker="files")

    assert read(repo.work / "CLAUDE.md") == GITHUB_SINGLE.replace(
        SEED_TRACKER, "Committed files in `.specs/`, one folder per spec and one file per ticket. "
                      "See `docs/skillworks/issue-tracker.md`, under The files Tracker.\n")


def test_the_domain_docs_line_names_the_adr_folder(repo, runner):
    set_up(repo.work)

    seed(runner, repo.work, folder="docs/decisions/")

    assert ("Single-context: `CONTEXT.md` and `docs/decisions/` at the repo root. See `docs/skillworks/domain.md`.\n"
            in read(repo.work / "CLAUDE.md"))


def test_a_checkout_with_no_loop_file_is_sent_to_seed_steering_and_nothing_is_written(repo, runner):
    before = on_disk(repo.work)

    ran = seed(runner, repo.work)

    assert ran.err == "FAIL  docs/skillworks/loop.json is missing. Run seed-steering to write it. Nothing was written.\n"
    assert on_disk(repo.work) == before


@pytest.mark.parametrize("argv", [
    [],
    ["--tracker", "jira", "--adr-folder", "docs/adr", "--contexts", "single"],
    ["--tracker", "github", "--adr-folder", "docs/adr", "--contexts", "some"],
    ["--tracker", "github", "--contexts", "single"],
    ["--tracker", "github", "--adr-folder", "docs/adr", "--contexts", "single", "--keep", "CLAUDE.md:1=mine"],
])
def test_a_command_written_wrong_prints_the_usage(repo, runner, argv):
    out, err = io.StringIO(), io.StringIO()

    status = agent_skills.main(argv, runner, out, err, repo.work.as_posix())

    assert status == 64
    assert err.getvalue() == agent_skills.USAGE
