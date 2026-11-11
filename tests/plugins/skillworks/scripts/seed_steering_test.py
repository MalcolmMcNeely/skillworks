import io
import json
import re
from pathlib import Path

import pytest
import seed_steering
from branches.open_the_pull_request import open_the_pull_request
from conftest import PLUGIN, ROOT, Ran, Repo, git, launch
from seeds import agent_skills
from suite import Suite
from tracker.files import CLOSING_NOTE
from tracker.reading import DRIFT_REPORT, NAME_REPORT

SKILLS = PLUGIN / "skills"
SETUP = SKILLS / "skillworks-setup"

WHERE = {
    "comments.md": "docs/skillworks/rules/comments.md",
    "determinism.md": "docs/skillworks/rules/determinism.md",
    "file-placement.md": "docs/skillworks/rules/file-placement.md",
    "testing.md": "docs/skillworks/rules/testing.md",
    "words.md": "docs/skillworks/rules/words.md",
    "issue-tracker.md": "docs/skillworks/issue-tracker.md",
    "domain.md": "docs/skillworks/domain.md",
    "adr-format.md": "docs/skillworks/adr-format.md",
    "placement-checks.md": "docs/skillworks/placement-checks.md",
    "review-standards.md": "docs/skillworks/review-standards.md",
    "review-architecture.md": "docs/skillworks/review-architecture.md",
    "review-spec.md": "docs/skillworks/review-spec.md",
    "suite.json": "docs/skillworks/suite.json",
    "loop.json": "docs/skillworks/loop.json",
    "surfaces.md": "docs/skillworks/surfaces.md",
}

WORKING_FOLDERS = [".spec-loop/", ".handoff/", ".claude/worktrees/", ".context-backfill/"]

RULES = ["comments.md", "determinism.md", "file-placement.md", "testing.md", "words.md"]


def run_seed(runner, where, *flags):
    out, err = io.StringIO(), io.StringIO()
    status = seed_steering.main([where.as_posix(), *flags], runner, out, err)
    return Ran(status, out.getvalue(), err.getvalue())


def settings_block(path):
    text = path.read_text(encoding="utf-8")
    blocks = re.findall(r"```yaml\n(.*?)```", text, re.DOTALL)
    assert len(blocks) == 1, path
    return blocks[0].splitlines()


def seeded(name):
    return (SETUP / "seeds" / name).read_text(encoding="utf-8")


def seeded_for(name, default_branch):
    return seeded(name).replace(seed_steering.DEFAULT_BRANCH_PLACEHOLDER, default_branch)


def test_an_empty_repo_gets_every_seed(repo, runner):
    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    for seed, place in WHERE.items():
        assert (repo.work / place).read_text(encoding="utf-8") == seeded_for(seed, "main"), place
        assert "wrote {}\n".format(place) in ran.out


OLD_BASELINES = ["smell-baseline.md", "arrangement-baseline.md"]


def test_an_empty_repo_gets_no_file_under_an_old_baseline_name(repo, runner):
    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    for old in OLD_BASELINES:
        assert not (repo.work / "docs" / "skillworks" / old).exists(), old
        assert old not in ran.out, old


def test_an_empty_repo_gets_nothing_under_docs_agents(repo, runner):
    ran = run_seed(runner, repo.work)

    assert (ran.status, (repo.work / "docs" / "agents").exists()) == (0, False), ran.err


BASES = "docs/skillworks/.seeds"


def test_an_empty_repo_gets_an_exact_base_copy_of_every_seed_it_was_written(repo, runner):
    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    for seed, place in WHERE.items():
        base = repo.work / BASES / seed
        assert base.read_bytes() == (repo.work / place).read_bytes(), seed
        assert base.read_text(encoding="utf-8") == seeded_for(seed, "main"), seed


def test_the_base_folder_holds_a_readme_that_says_the_copies_are_setups():
    readme = seed_steering.BASES_README

    assert "setup" in readme
    assert "not to be edited" in readme


def test_the_base_folder_holds_the_base_copies_and_one_readme(repo, runner):
    ran = run_seed(runner, repo.work)

    held = sorted(path.name for path in (repo.work / BASES).iterdir())
    assert held == sorted(list(WHERE) + ["README.md"])
    assert (repo.work / BASES / "README.md").read_text(encoding="utf-8") == seed_steering.BASES_README
    assert "wrote {}/README.md\n".format(BASES) in ran.out


def test_a_second_run_leaves_the_base_folder_readme_as_it_is(repo, runner):
    run_seed(runner, repo.work)
    readme = repo.work / BASES / "README.md"
    readme.write_text("# Our note on the copies\n", encoding="utf-8", newline="\n")

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert readme.read_text(encoding="utf-8") == "# Our note on the copies\n"
    assert "README.md" not in ran.out


def test_a_seed_already_there_with_no_base_copy_gets_none(repo, runner):
    edited = repo.work / "docs" / "skillworks" / "domain.md"
    edited.parent.mkdir(parents=True)
    edited.write_text("# Our own domain notes\n", encoding="utf-8", newline="\n")

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert edited.read_text(encoding="utf-8") == "# Our own domain notes\n"
    assert "kept docs/skillworks/domain.md, which differs from the seed:\n" in ran.out
    assert not (repo.work / BASES / "domain.md").exists()


def with_no_base_copy_beside_a_file_to_update(repo, runner):
    seeded_by_an_older_plugin(repo, runner, "suite.json")
    seed_steering.write(repo.work / WHERE["domain.md"], "# Our own domain notes\n")
    (repo.work / BASES / "domain.md").unlink()


def test_a_file_with_no_base_copy_holds_the_whole_run_and_every_outcome_is_still_said(repo, runner):
    with_no_base_copy_beside_a_file_to_update(repo, runner)
    before = on_disk(repo.work)

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert on_disk(repo.work) == before
    assert "kept {}, which differs from the seed:\n".format(WHERE["domain.md"]) in ran.out
    assert "would update {}\n".format(WHERE["suite.json"]) in ran.out
    assert "updated {}\n".format(WHERE["suite.json"]) not in ran.out
    assert "Nothing was written." in ran.out
    assert "--settled" in ran.out.splitlines()[-1]


def test_a_run_that_settles_the_file_with_no_base_copy_writes_every_file_and_base_copy(repo, runner):
    with_no_base_copy_beside_a_file_to_update(repo, runner)

    ran = run_seed_settling(runner, repo.work, WHERE["domain.md"])

    assert ran.status == 0, ran.err
    assert (repo.work / WHERE["domain.md"]).read_text(encoding="utf-8") == "# Our own domain notes\n"
    assert (repo.work / BASES / "domain.md").read_text(encoding="utf-8") == seeded("domain.md")
    assert (repo.work / WHERE["suite.json"]).read_text(encoding="utf-8") == seeded("suite.json")
    assert (repo.work / BASES / "suite.json").read_text(encoding="utf-8") == seeded("suite.json")
    assert "updated {}\n".format(WHERE["suite.json"]) in ran.out
    assert "Nothing was written." not in ran.out


def run_seed_settling(runner, where, *places):
    return run_seed(runner, where, *[part for place in places for part in ("--settled", place)])


@pytest.mark.parametrize("seed", ["domain.md", "suite.json"])
def test_a_file_with_no_base_copy_gets_one_once_the_team_has_settled_it(repo, runner, seed):
    place = WHERE[seed]
    settled = "# What the team settled\n" if seed == "domain.md" else '{\n  "runs": 3,\n  "checks": []\n}\n'
    seed_steering.write(repo.work / place, settled)

    ran = run_seed_settling(runner, repo.work, place)

    assert ran.status == 0, ran.err
    assert (repo.work / place).read_text(encoding="utf-8") == settled
    assert (repo.work / BASES / seed).read_text(encoding="utf-8") == seeded_for(seed, "main")
    assert "kept {}, as you settled it, and wrote its base copy\n".format(place) in ran.out
    assert "differs" not in ran.out


def test_a_settled_file_is_weighed_against_its_new_base_copy_on_the_next_run(repo, runner):
    place = WHERE["domain.md"]
    seed_steering.write(repo.work / place, "# Our own domain notes\n")
    run_seed_settling(runner, repo.work, place)

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert "kept {}, which you edited\n".format(place) in ran.out


def test_a_file_with_no_base_copy_the_same_as_the_seed_gets_one(repo, runner):
    run_seed(runner, repo.work)
    (repo.work / BASES / "domain.md").unlink()

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert (repo.work / BASES / "domain.md").read_text(encoding="utf-8") == seeded("domain.md")
    assert "kept docs/skillworks/domain.md, the same as the seed, and wrote its base copy\n" in ran.out


def test_a_file_with_no_base_copy_settled_by_taking_the_whole_seed_gets_one(repo, runner):
    place = WHERE["domain.md"]
    seed_steering.write(repo.work / place, seeded("domain.md"))

    ran = run_seed_settling(runner, repo.work, place)

    assert ran.status == 0, ran.err
    assert (repo.work / BASES / "domain.md").read_text(encoding="utf-8") == seeded("domain.md")


def test_a_settling_that_names_no_file_without_a_base_copy_is_refused_and_nothing_is_written(repo, runner):
    run_seed(runner, repo.work)
    seed_steering.write(repo.work / WHERE["domain.md"], "# Our own domain notes\n")
    before = on_disk(repo.work)

    ran = run_seed_settling(runner, repo.work, "docs/skillworks/domain.md")

    assert ran.status == 1
    assert "docs/skillworks/domain.md" in ran.err
    assert "Nothing was written." in ran.err
    assert on_disk(repo.work) == before


def test_a_settling_with_no_file_prints_the_usage(repo, runner):
    out, err = io.StringIO(), io.StringIO()

    status = seed_steering.main([repo.work.as_posix(), "--settled"], runner, out, err)

    assert status == 64
    assert err.getvalue() == seed_steering.USAGE


def make_master_the_default(repo):
    git(repo.work, "push", "--quiet", "origin", "main:master")
    git(repo.origin, "symbolic-ref", "HEAD", "refs/heads/master")


def test_the_loop_file_names_the_remotes_default_branch_as_the_target_branch(repo, runner):
    make_master_the_default(repo)

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    loop = json.loads((repo.work / "docs" / "skillworks" / "loop.json").read_text(encoding="utf-8"))
    assert loop == {"tracker": "github", "target-branch": "master", "co-authored-by": "hide",
                    "session-trailer": "show", "export": False}


def test_a_loop_file_already_there_is_kept_and_its_difference_shown(repo, runner):
    make_master_the_default(repo)
    held = repo.work / "docs" / "skillworks" / "loop.json"
    held.parent.mkdir(parents=True)
    held.write_text('{\n  "target-branch": "pr"\n}\n', encoding="utf-8", newline="\n")

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert held.read_text(encoding="utf-8") == '{\n  "target-branch": "pr"\n}\n'
    assert "kept docs/skillworks/loop.json, which differs from the seed:\n" in ran.out
    assert '-  "target-branch": "pr"\n' in ran.out
    assert '+  "target-branch": "master",\n' in ran.out


def test_a_repo_with_no_origin_stops_before_anything_is_written(repo, runner):
    git(repo.work, "remote", "remove", "origin")

    ran = run_seed(runner, repo.work)

    assert ran.status == 1
    assert "origin" in ran.err
    assert "Nothing was written." in ran.err
    assert not (repo.work / "docs").exists()


def test_a_repo_with_no_origin_is_told_how_to_add_a_bare_one(repo, runner):
    git(repo.work, "remote", "remove", "origin")

    ran = run_seed(runner, repo.work)

    assert ran.status == 1
    assert "A bare repo on a shared drive is enough" in ran.err
    assert "git init --bare <shared-drive>/<repo>.git\n" in ran.err
    assert "git remote add origin <shared-drive>/<repo>.git\n" in ran.err
    assert "git push origin main\n" in ran.err


def test_every_seed_lands_under_docs_skillworks_and_the_rules_in_its_rules_folder(repo, runner):
    run_seed(runner, repo.work)

    assert not (repo.work / ".claude" / "rules").exists()
    assert sorted(seed_steering.PLACES) == sorted(WHERE)
    for seed, place in seed_steering.PLACES.items():
        assert place.startswith("docs/skillworks/"), place
        assert (place == "docs/skillworks/rules/" + seed) == (seed in RULES), place


def test_a_rule_already_in_the_rules_folder_is_kept_and_its_difference_shown(repo, runner):
    edited = repo.work / "docs" / "skillworks" / "rules" / "words.md"
    edited.parent.mkdir(parents=True)
    edited.write_text("# Our own words\n", encoding="utf-8", newline="\n")

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert edited.read_text(encoding="utf-8") == "# Our own words\n"
    assert "kept docs/skillworks/rules/words.md, which differs from the seed:\n" in ran.out
    assert "-# Our own words\n" in ran.out
    assert "wrote docs/skillworks/rules/words.md" not in ran.out


def test_the_seeds_folder_holds_the_listed_seeds_and_nothing_else():
    assert sorted(path.name for path in (SETUP / "seeds").iterdir()) == sorted(WHERE)


def test_the_rules_arrive_with_their_settings_empty(repo, runner):
    run_seed(runner, repo.work)
    rules = repo.work / "docs" / "skillworks" / "rules"

    placement = settings_block(rules / "file-placement.md")
    assert "slices: []" in placement
    assert "concerns: []" in placement
    assert "test-roots: {}" in placement
    assert "max-types-per-folder: 10" in placement
    assert "banned-words: {}" in settings_block(rules / "words.md")
    determinism = settings_block(rules / "determinism.md")
    assert "contexts: []" in determinism
    assert "clock: TimeProvider" in determinism
    assert "doc-comments: none" in settings_block(rules / "comments.md")


def test_the_domain_docs_arrive_naming_docs_adr_as_the_adr_folder(repo, runner):
    run_seed(runner, repo.work)

    assert settings_block(repo.work / WHERE["domain.md"]) == ["adr-folder: docs/adr"]


# Each context sits under src/ in the trees, so an ADR folder below that line belongs to a context.
def under_src(text):
    trees = [block for block in re.findall(r"```\n(.*?)```", text, re.DOTALL) if "/\n" in block]
    return [line for tree in trees for line in tree.split("src/", 1)[-1].splitlines() if "src/" in tree]


@pytest.mark.parametrize("page", [SETUP / "seeds" / "domain.md", SKILLS / "domain-modeling" / "SKILL.md"])
def test_a_folder_tree_holds_no_adr_folder_under_a_context(page):
    lines = under_src(page.read_text(encoding="utf-8"))

    assert lines
    assert [line for line in lines if "adr" in line] == []


def test_the_domain_docs_seed_names_the_setting_and_not_a_fixed_folder_for_a_reader():
    text = seeded("domain.md")
    read_these = text.split("## Before exploring, read these\n", 1)[1].split("\n## ", 1)[0]

    assert "`adr-folder`" in read_these
    assert "`docs/adr/`" not in read_these


def test_the_adr_format_seed_holds_the_skillworks_template_and_optional_sections():
    text = seeded("adr-format.md")
    template = section(text, "Template")
    optional = section(text, "Optional sections")

    assert "# {Short title of the decision}" in template
    assert "{1-3 sentences: what's the context, what did we decide, and why.}" in template
    for name in ("**Status**", "**Considered Options**", "**Consequences**"):
        assert name in optional, name


def test_an_empty_repo_gets_the_adr_shape_file(repo, runner):
    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert (repo.work / "docs" / "skillworks" / "adr-format.md").read_text(encoding="utf-8") == seeded("adr-format.md")


def test_this_repo_holds_the_adr_shape_file_with_the_seeds_text():
    assert (ROOT / "docs" / "skillworks" / "adr-format.md").read_text(encoding="utf-8") == seeded("adr-format.md")


def adr_writing_page():
    return (SKILLS / "domain-modeling" / "WRITING-ADRS.md").read_text(encoding="utf-8")


def test_domain_modeling_points_at_the_page_on_writing_adrs_and_no_page_named_for_the_adr_format():
    assert "[WRITING-ADRS.md](./WRITING-ADRS.md)" in skill_text("domain-modeling")
    assert not (SKILLS / "domain-modeling" / "ADR-FORMAT.md").exists()


def test_domain_modeling_reads_the_adr_shape_from_steering_and_the_folder_from_the_setting():
    page = adr_writing_page()

    assert read_of("docs/skillworks/adr-format.md") in page
    assert "`adr-folder`" in page
    assert read_of("docs/skillworks/domain.md") in page
    assert "## Template" not in page
    assert "## Optional sections" not in page
    assert "docs/adr" not in page


def test_domain_modeling_numbers_a_new_adr_at_the_folders_width():
    numbering = section(adr_writing_page(), "Numbering")

    assert "one above the highest" in numbering
    assert "digit count" in numbering
    assert "`0001`" in numbering


def test_domain_modeling_keeps_when_to_offer_an_adr():
    offer = section(adr_writing_page(), "When to offer an ADR")

    for test in ("**Hard to reverse**", "**Surprising without context**", "**The result of a real trade-off**"):
        assert test in offer, test


def paragraphs_naming(text, name):
    return [paragraph for paragraph in text.split("\n\n") if name in paragraph]


def test_context_backfill_drafts_each_adr_in_the_teams_shape():
    paragraphs = paragraphs_naming(skill_text("context-backfill"), read_of("docs/skillworks/adr-format.md"))

    assert any("ADR Draft" in paragraph and "`adr-folder`" in paragraph for paragraph in paragraphs)


def test_context_backfill_puts_the_reversal_phrases_wherever_the_shape_puts_a_status():
    paragraphs = paragraphs_naming(skill_text("context-backfill"), "wherever the shape puts a status")

    assert len(paragraphs) == 1
    assert "`Status: superseded by the decision below`" in paragraphs[0]
    assert "`This supersedes the decision above.`" in paragraphs[0]


def test_the_architecture_review_reads_and_writes_adrs_in_the_setting_and_the_shape():
    text = skill_text("improve-codebase-architecture")

    assert "`adr-folder`" in text
    assert read_of("docs/skillworks/domain.md") in text
    assert read_of("docs/skillworks/adr-format.md") in text
    assert "numbered one above the highest" in " ".join(text.split())


@pytest.mark.parametrize("page", ["context-backfill/SKILL.md", "improve-codebase-architecture/SKILL.md",
                                  "review-changes/architecture.md", "what-next/SKILL.md"])
def test_a_skill_that_reads_or_writes_adrs_names_the_setting_and_not_a_fixed_folder(page):
    text = (SKILLS / page).read_text(encoding="utf-8")

    assert "docs/adr" not in text
    assert "`adr-folder`" in text


def test_the_backfill_page_says_adrs_go_to_the_setting_in_the_teams_shape_at_the_folders_width():
    page = " ".join((ROOT / "docs" / "usage" / "context-backfill.md").read_text(encoding="utf-8").split())

    assert "`docs/skillworks/adr-format.md`" in page
    assert "`adr-folder`" in page
    assert "padded as wide as the file with the highest number" in page
    assert "docs/adr/" not in page


@pytest.mark.parametrize("page", ["README.md", "the-loop/stage-map.md", "the-loop/sessions.md",
                                  "the-loop/target-branch.md", "the-loop/export.md",
                                  "the-loop/name-check.md", "the-loop/the-grill.md"])
def test_a_user_docs_page_that_names_the_adr_folder_names_the_setting_and_not_a_fixed_path(page):
    text = (ROOT / "docs" / "usage" / page).read_text(encoding="utf-8")

    assert "`adr-folder`" in text
    assert "docs/adr/" not in text


def test_a_seed_already_there_is_kept_and_its_difference_shown(repo, runner):
    edited = repo.work / "docs" / "skillworks" / "issue-tracker.md"
    edited.parent.mkdir(parents=True)
    edited.write_text("# Our own tracker notes\n", encoding="utf-8", newline="\n")

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert edited.read_text(encoding="utf-8") == "# Our own tracker notes\n"
    assert "kept docs/skillworks/issue-tracker.md, which differs from the seed:\n" in ran.out
    assert "-# Our own tracker notes\n" in ran.out
    assert "+# Issue tracker: GitHub\n" in ran.out
    assert "wrote docs/skillworks/issue-tracker.md" not in ran.out


def test_a_seed_already_there_unchanged_says_so_and_shows_nothing(repo, runner):
    run_seed(runner, repo.work)

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert "kept docs/skillworks/suite.json, the same as the seed\n" in ran.out
    assert "differs" not in ran.out


OLDER = {
    "domain.md": "# Domain docs\n\nAn older seed.\n",
    "suite.json": '{\n  "runs": 2,\n  "checks": []\n}\n',
}


def seeded_by_an_older_plugin(repo, runner, seed):
    run_seed(runner, repo.work)
    seed_steering.write(repo.work / WHERE[seed], OLDER[seed])
    seed_steering.write(repo.work / BASES / seed, OLDER[seed])


@pytest.mark.parametrize("seed", sorted(OLDER))
def test_a_file_never_edited_whose_seed_moved_on_is_updated_with_its_base_copy(repo, runner, seed):
    seeded_by_an_older_plugin(repo, runner, seed)

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    place = WHERE[seed]
    assert (repo.work / place).read_text(encoding="utf-8") == seeded(seed)
    assert (repo.work / BASES / seed).read_bytes() == (repo.work / place).read_bytes()
    assert "updated {}\n".format(place) in ran.out
    assert "differs" not in ran.out


@pytest.mark.parametrize("seed", sorted(OLDER))
def test_an_updated_file_shows_the_change_from_the_old_seed_to_the_new_after_its_line(repo, runner, seed):
    seeded_by_an_older_plugin(repo, runner, seed)
    place = WHERE[seed]

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert "updated {}\n--- old-seed/{}\n+++ new-seed/{}\n".format(place, place, place) in ran.out
    older, newer = OLDER[seed].splitlines(keepends=True), seeded(seed).splitlines(keepends=True)
    gone = [line for line in older if line not in newer]
    came = [line for line in newer if line not in older]
    assert gone and came
    for line in gone:
        assert "-" + line in ran.out
    for line in came:
        assert "+" + line in ran.out


@pytest.mark.parametrize("seed", sorted(OLDER))
def test_a_file_edited_whose_seed_did_not_move_is_kept_as_it_is(repo, runner, seed):
    run_seed(runner, repo.work)
    place = WHERE[seed]
    seed_steering.write(repo.work / place, OLDER[seed])

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert (repo.work / place).read_text(encoding="utf-8") == OLDER[seed]
    assert (repo.work / BASES / seed).read_text(encoding="utf-8") == seeded(seed)
    assert "kept {}, which you edited\n".format(place) in ran.out
    assert "differs" not in ran.out


@pytest.mark.parametrize("seed", sorted(OLDER))
def test_a_file_unchanged_on_either_side_is_kept_the_same_as_the_seed(repo, runner, seed):
    run_seed(runner, repo.work)

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    place = WHERE[seed]
    assert (repo.work / place).read_text(encoding="utf-8") == seeded(seed)
    assert (repo.work / BASES / seed).read_text(encoding="utf-8") == seeded(seed)
    assert "kept {}, the same as the seed\n".format(place) in ran.out


def already_on_the_new_seed(repo, runner, seed):
    run_seed(runner, repo.work)
    seed_steering.write(repo.work / BASES / seed, OLDER[seed])


@pytest.mark.parametrize("seed", sorted(OLDER))
def test_a_file_already_the_same_as_a_seed_that_moved_on_brings_its_base_copy_up_to_the_seed(repo, runner, seed):
    already_on_the_new_seed(repo, runner, seed)

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    place = WHERE[seed]
    assert (repo.work / place).read_text(encoding="utf-8") == seeded(seed)
    assert (repo.work / BASES / seed).read_text(encoding="utf-8") == seeded(seed)
    assert "kept {}, the same as the seed, and brought its base copy up to the seed\n".format(place) in ran.out


@pytest.mark.parametrize("seed", sorted(OLDER))
def test_a_file_its_base_copy_and_its_seed_all_the_same_say_no_base_copy_changed(repo, runner, seed):
    run_seed(runner, repo.work)

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert "kept {}, the same as the seed\n".format(WHERE[seed]) in ran.out
    assert "base copy" not in ran.out


def moved_again(tmp_path, monkeypatch, seed):
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    for name in WHERE:
        (seeds / name).write_bytes((SETUP / "seeds" / name).read_bytes())
    later = seeded(seed).replace("\n", "\n\n", 1)
    seed_steering.write(seeds / seed, later)
    monkeypatch.setattr(seed_steering, "SEEDS", seeds)
    return later


@pytest.mark.parametrize("seed", sorted(OLDER))
def test_a_file_whose_base_copy_was_brought_up_is_updated_when_the_seed_moves_again(
        repo, runner, tmp_path, monkeypatch, seed):
    already_on_the_new_seed(repo, runner, seed)
    run_seed(runner, repo.work)
    later = moved_again(tmp_path, monkeypatch, seed)

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    place = WHERE[seed]
    assert (repo.work / place).read_text(encoding="utf-8") == later
    assert (repo.work / BASES / seed).read_text(encoding="utf-8") == later
    assert "updated {}\n".format(place) in ran.out
    assert "merged" not in ran.out
    assert "asks" not in ran.out


@pytest.mark.parametrize("seed", sorted(OLDER))
def test_a_file_the_team_deleted_is_written_again_and_its_base_copy_brought_up(repo, runner, seed):
    seeded_by_an_older_plugin(repo, runner, seed)
    place = WHERE[seed]
    (repo.work / place).unlink()

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert (repo.work / place).read_text(encoding="utf-8") == seeded(seed)
    assert (repo.work / BASES / seed).read_text(encoding="utf-8") == seeded(seed)
    assert "wrote {}\n".format(place) in ran.out
    assert "left out" not in ran.out


@pytest.mark.parametrize("seed", sorted(OLDER))
def test_a_seed_new_in_the_plugin_is_written_with_its_base_copy(repo, runner, seed):
    run_seed(runner, repo.work)
    place = WHERE[seed]
    (repo.work / place).unlink()
    (repo.work / BASES / seed).unlink()

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert (repo.work / place).read_text(encoding="utf-8") == seeded(seed)
    assert (repo.work / BASES / seed).read_bytes() == (repo.work / place).read_bytes()
    assert "wrote {}\n".format(place) in ran.out


def run_seed_choosing(runner, where, *choices):
    return run_seed(runner, where, *[part for choice in choices for part in ("--keep", choice)])


def on_disk(folder):
    return {path.relative_to(folder).as_posix(): path.read_bytes()
            for path in folder.rglob("*") if path.is_file() and ".git" not in path.relative_to(folder).parts}


# Each base is the Seed with its early lines older, and each edit is the team's change further down.
APART = {
    "domain.md": {
        "base": seeded("domain.md").replace("# Domain Docs\n", "# Domain docs\n"),
        "yours": seeded("domain.md").replace("# Domain Docs\n", "# Domain docs\n").replace(
            "## Flag ADR conflicts\n", "## Flag ADR conflicts early\n"),
        "merged": seeded("domain.md").replace("## Flag ADR conflicts\n", "## Flag ADR conflicts early\n"),
    },
    "suite.json": {
        "base": '{\n  "runs": 2,\n  "checks": []\n}\n',
        "yours": '{\n  "runs": 2,\n  "checks": [{"name": "unit", "run": ["pytest"]}]\n}\n',
        "merged": '{\n  "runs": 1,\n  "checks": [{"name": "unit", "run": ["pytest"]}]\n}\n',
    },
}

ACROSS = {
    "domain.md": {
        "base": seeded("domain.md").replace("# Domain Docs\n", "# Domain docs\n"),
        "yours": seeded("domain.md").replace("# Domain Docs\n", "# Our domain\n"),
    },
    "suite.json": {
        "base": '{\n  "runs": 2,\n  "checks": []\n}\n',
        "yours": '{\n  "runs": 3,\n  "checks": []\n}\n',
    },
}


def edited_on_both_sides(repo, runner, seed, sides):
    run_seed(runner, repo.work)
    seed_steering.write(repo.work / BASES / seed, sides["base"])
    seed_steering.write(repo.work / WHERE[seed], sides["yours"])


@pytest.mark.parametrize("seed", sorted(APART))
def test_a_file_edited_whose_seed_moved_elsewhere_is_merged_and_the_change_shown(repo, runner, seed):
    edited_on_both_sides(repo, runner, seed, APART[seed])
    place = WHERE[seed]

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert (repo.work / place).read_text(encoding="utf-8") == APART[seed]["merged"]
    assert (repo.work / BASES / seed).read_text(encoding="utf-8") == seeded(seed)
    assert "merged {}, applying the seed's change:\n".format(place) in ran.out
    theirs = seeded(seed).splitlines(keepends=True)[:2]
    base = APART[seed]["base"].splitlines(keepends=True)[:2]
    changed = [line for line in theirs if line not in base]
    assert changed
    for line in changed:
        assert "+" + line in ran.out
    assert "asks" not in ran.out


@pytest.mark.parametrize("seed", sorted(APART))
def test_a_merged_file_labels_its_diff_as_your_file_and_the_merged_file(repo, runner, seed):
    edited_on_both_sides(repo, runner, seed, APART[seed])
    place = WHERE[seed]

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert "merged {}, applying the seed's change:\n--- yours/{}\n+++ merged/{}\n".format(place, place, place) \
        in ran.out
    assert "seed/{}".format(place) not in ran.out


def test_a_file_with_no_base_copy_labels_its_diff_as_your_file_and_the_seed(repo, runner):
    place = WHERE["domain.md"]
    seed_steering.write(repo.work / place, "# Our own domain notes\n")

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert "which differs from the seed:\n--- yours/{}\n+++ seed/{}\n".format(place, place) in ran.out


@pytest.mark.parametrize("seed", sorted(ACROSS))
def test_a_file_whose_edit_and_seed_overlap_asks_shows_both_sides_and_writes_nothing(repo, runner, seed):
    edited_on_both_sides(repo, runner, seed, ACROSS[seed])
    (repo.work / WHERE["words.md"]).unlink()
    (repo.work / BASES / "words.md").unlink()
    before = on_disk(repo.work)

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert on_disk(repo.work) == before
    place = WHERE[seed]
    assert "asks {}, where your edit and the seed's change overlap:\n".format(place) in ran.out
    ours = [line for line in ACROSS[seed]["yours"].splitlines() if line not in ACROSS[seed]["base"].splitlines()]
    theirs = [line for line in seeded(seed).splitlines() if line not in ACROSS[seed]["base"].splitlines()]
    assert ours and theirs
    report = ran.out.splitlines()
    for line in ours + theirs:
        assert any(said.endswith(line) and said != line for said in report), line
    assert "overlap 1 in {}\n".format(place) in ran.out
    assert "would write {}\n".format(WHERE["words.md"]) in ran.out
    assert "wrote {}\n".format(WHERE["words.md"]) not in ran.out
    assert "Nothing was written." in ran.out


@pytest.mark.parametrize("seed", sorted(ACROSS))
@pytest.mark.parametrize("keep", ["yours", "seed"])
def test_a_choice_for_each_overlap_writes_the_merged_file_and_its_base_copy(repo, runner, seed, keep):
    edited_on_both_sides(repo, runner, seed, ACROSS[seed])
    place = WHERE[seed]

    ran = run_seed_choosing(runner, repo.work, "{}:1={}".format(place, keep))

    assert ran.status == 0, ran.err
    kept = ACROSS[seed]["yours"] if keep == "yours" else seeded(seed)
    assert (repo.work / place).read_text(encoding="utf-8") == kept
    assert (repo.work / BASES / seed).read_text(encoding="utf-8") == seeded(seed)
    assert "merged {}".format(place) in ran.out
    assert "asks" not in ran.out


def test_a_choice_that_names_no_overlap_is_refused_and_nothing_is_written(repo, runner):
    run_seed(runner, repo.work)
    before = on_disk(repo.work)

    ran = run_seed_choosing(runner, repo.work, "docs/skillworks/domain.md:1=yours")

    assert ran.status == 1
    assert "docs/skillworks/domain.md:1" in ran.err
    assert on_disk(repo.work) == before


@pytest.mark.parametrize("choice", ["docs/skillworks/domain.md:1", "docs/skillworks/domain.md=yours",
                                    "docs/skillworks/domain.md:x=yours", "docs/skillworks/domain.md:1=both"])
def test_a_choice_written_wrong_prints_the_usage(repo, runner, choice):
    ran = run_seed_choosing(runner, repo.work, choice)

    assert ran.status == 64
    assert ran.err == seed_steering.USAGE


BLENDS = {
    "domain.md": {
        "blend": "# Our Domain Docs\n",
        "blended": seeded("domain.md").replace("# Domain Docs\n", "# Our Domain Docs\n"),
    },
    "suite.json": {
        "blend": '  "runs": 4,\n',
        "blended": '{\n  "runs": 4,\n  "checks": []\n}\n',
    },
}


def blend_file(tmp_path, text):
    path = tmp_path / "blend.txt"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def run_seed_blending(runner, where, place, number, path, *flags):
    return run_seed(runner, where, "--blend", "{}:{}={}".format(place, number, path), *flags)


@pytest.mark.parametrize("seed", sorted(ACROSS))
def test_an_overlap_answered_with_a_blend_takes_the_blends_text_and_the_base_copy_takes_the_seed(
        repo, runner, tmp_path, seed):
    edited_on_both_sides(repo, runner, seed, ACROSS[seed])
    place = WHERE[seed]

    ran = run_seed_blending(runner, repo.work, place, 1, blend_file(tmp_path, BLENDS[seed]["blend"]))

    assert ran.status == 0, ran.err
    assert (repo.work / place).read_text(encoding="utf-8") == BLENDS[seed]["blended"]
    assert (repo.work / BASES / seed).read_text(encoding="utf-8") == seeded(seed)
    assert "merged {}".format(place) in ran.out


def test_a_blend_with_no_newline_at_its_end_still_ends_its_line(repo, runner, tmp_path):
    edited_on_both_sides(repo, runner, "domain.md", ACROSS["domain.md"])
    place = WHERE["domain.md"]

    ran = run_seed_blending(runner, repo.work, place, 1, blend_file(tmp_path, "# Our Domain Docs"))

    assert ran.status == 0, ran.err
    assert (repo.work / place).read_text(encoding="utf-8") == BLENDS["domain.md"]["blended"]


def test_a_blend_that_names_no_overlap_is_refused_and_nothing_is_written(repo, runner, tmp_path):
    run_seed(runner, repo.work)
    before = on_disk(repo.work)

    ran = run_seed_blending(runner, repo.work, "docs/skillworks/domain.md", 1, blend_file(tmp_path, "# Ours\n"))

    assert ran.status == 1
    assert "docs/skillworks/domain.md:1" in ran.err
    assert on_disk(repo.work) == before


def test_a_blend_whose_file_is_missing_is_refused_and_nothing_is_written(repo, runner, tmp_path):
    edited_on_both_sides(repo, runner, "domain.md", ACROSS["domain.md"])
    before = on_disk(repo.work)

    ran = run_seed_blending(runner, repo.work, WHERE["domain.md"], 1, tmp_path / "missing.txt")

    assert ran.status == 1
    assert "missing.txt" in ran.err
    assert on_disk(repo.work) == before


def test_a_blend_beside_a_keep_and_a_settled_choice_in_one_run_is_honoured_with_them(repo, runner, tmp_path):
    edited_on_both_sides(repo, runner, "domain.md", ACROSS["domain.md"])
    edited_on_both_sides(repo, runner, "suite.json", ACROSS["suite.json"])
    (repo.work / BASES / "testing.md").unlink()
    seed_steering.write(repo.work / WHERE["testing.md"], "# Our own testing rule\n")

    ran = run_seed_blending(runner, repo.work, WHERE["domain.md"], 1,
                            blend_file(tmp_path, BLENDS["domain.md"]["blend"]),
                            "--keep", "{}:1=seed".format(WHERE["suite.json"]),
                            "--settled", WHERE["testing.md"])

    assert ran.status == 0, ran.err
    assert {place: (repo.work / place).read_text(encoding="utf-8")
            for place in (WHERE["domain.md"], WHERE["suite.json"], WHERE["testing.md"])} == {
        WHERE["domain.md"]: BLENDS["domain.md"]["blended"],
        WHERE["suite.json"]: seeded("suite.json"),
        WHERE["testing.md"]: "# Our own testing rule\n",
    }


@pytest.mark.parametrize("choice", ["docs/skillworks/domain.md:1", "docs/skillworks/domain.md:1=", "docs/skillworks/domain.md=x"])
def test_a_blend_written_wrong_prints_the_usage(repo, runner, choice):
    ran = run_seed(runner, repo.work, "--blend", choice)

    assert ran.status == 64
    assert ran.err == seed_steering.USAGE


def test_the_usage_names_the_blend():
    assert "--blend <file>:<overlap>=<blend file>" in seed_steering.USAGE


def test_the_issue_tracker_seed_holds_the_two_conventions():
    tracker = seeded("issue-tracker.md")

    assert "### Two conventions the loop leans on" in tracker
    assert "`Ticket: #<n>`" in tracker
    assert "gh issue close <n> --comment" in tracker


def test_the_issue_tracker_seed_says_a_specs_checks_read_only_commits_that_name_its_tickets():
    tracker = seeded("issue-tracker.md")

    assert ("read only the commits whose `Ticket:` trailer names one of the spec's tickets, and never "
            "a commit with no trailer") in tracker
    assert ("A spec's checks read only the commits whose trailer names one of its tickets, and never "
            "a commit with no trailer") in tracker


def test_the_comments_rule_seed_holds_the_keep_and_cut_table():
    comments = seeded("comments.md")

    assert "## What a sweep keeps and cuts" in comments
    assert "| Comment | Verdict |" in comments
    assert "| `// increment the counter` | Cut: restates the line below it |" in comments
    assert "| `// must run before the auth middleware or the session is empty` | Keep: a hidden ordering constraint |" in comments


def test_the_comment_sweep_reads_its_table_from_the_comments_rule():
    sweep = (SKILLS / "comment-sweep" / "SKILL.md").read_text(encoding="utf-8")

    assert "| Comment | Verdict |" not in sweep
    assert "What a sweep keeps and cuts" in sweep


def test_neither_pass_of_the_comment_sweep_touches_what_the_comments_rule_leaves_alone():
    scope = section(skill_text("comment-sweep"), "What is in scope")

    assert ("out of scope in every file, and neither pass touches them: a doc comment the rules allow, "
            "and anything the rules say a sweep leaves alone.") in scope


def test_the_review_standards_seed_holds_the_smells_list():
    smells = seeded("review-standards.md")

    assert "## The twelve" in smells
    assert "- **Feature Envy** — a method that reaches into another object's data more than its own." in smells
    assert "## The four" in smells
    assert "- **Stub Echo** — a stub is handed a value" in smells
    assert len(re.findall(r"^- \*\*[A-Z][^*]+\*\* — ", smells, re.MULTILINE)) == 16


REVIEW_FILES = ["review-standards.md", "review-architecture.md", "review-spec.md"]


def section(text, heading):
    assert "\n## {}\n".format(heading) in text, heading
    return text.split("\n## {}\n".format(heading), 1)[1].split("\n## ", 1)[0]


def test_the_review_architecture_seed_holds_the_nine_failures_and_their_weighting():
    failures = seeded("review-architecture.md")

    assert "- **Wrong-way dependency** — a module now imports from one that ought to depend on *it*" in failures
    assert "## Weighting" in failures
    nine = section(failures, "The nine")
    assert len(re.findall(r"^- \*\*[A-Z][^*]+\*\* — ", nine, re.MULTILINE)) == 9


def outside_fences(text):
    return re.sub(r"^```.*?^```", "", text, flags=re.MULTILINE | re.DOTALL)


def items(text):
    return re.findall(r"^\s*[-*] ", outside_fences(text), re.MULTILINE)


@pytest.mark.parametrize("seed", REVIEW_FILES)
def test_a_review_seed_explains_the_shape_of_a_check_and_holds_no_check(seed):
    checks = section(seeded(seed), "Checks")

    for part in ("what to look for", "hard breach", "judgement call", "paths"):
        assert part in checks, part
    assert items(checks) == []


@pytest.mark.parametrize("seed", REVIEW_FILES)
def test_a_review_seed_holds_an_empty_do_not_report_list(seed):
    assert items(section(seeded(seed), "Do not report")) == []


def test_an_item_in_a_list_is_counted_and_one_inside_a_fence_is_not():
    text = "Before.\n\n```markdown\n- **Handlers** — idempotent.\n```\n\n- `generated/`\n"

    assert len(items(text)) == 1


def above_the_checks(text):
    return text.split("\n## Checks\n", 1)[0]


@pytest.mark.parametrize("seed", REVIEW_FILES)
def test_this_repos_review_files_hold_the_seeds_lists_and_both_team_lists(seed):
    ours = (ROOT / WHERE[seed]).read_text(encoding="utf-8")

    assert above_the_checks(ours) == above_the_checks(seeded(seed))
    for heading in ("Checks", "Do not report"):
        assert "\n## {}\n".format(heading) in ours, heading


def test_this_repo_holds_no_file_under_an_old_baseline_name():
    for old in OLD_BASELINES:
        assert not (ROOT / "docs" / "skillworks" / old).exists(), old


@pytest.mark.parametrize("page", [SETUP / "seeds" / "placement-checks.md", ROOT / WHERE["placement-checks.md"]])
def test_the_placement_checks_name_the_review_architecture_file(page):
    text = page.read_text(encoding="utf-8")

    assert "[`review-architecture.md`](review-architecture.md)" in text
    for old in OLD_BASELINES:
        assert old not in text, old


WHERE_IT_LIVES = "**Where it lives:**"

SURFACE_PARTS = [WHERE_IT_LIVES, "**The question:**", "**What to capture:**"]


def surfaces(text):
    outside_fences = re.sub(r"^```.*?^```", "", text, flags=re.MULTILINE | re.DOTALL)
    sections = re.split(r"^## ", outside_fences, flags=re.MULTILINE)[1:]
    return {section.split("\n", 1)[0]: section for section in sections}


def where_it_lives(section):
    return section.split(WHERE_IT_LIVES, 1)[1].split("\n", 1)[0]


def test_the_surfaces_seed_holds_the_readme_and_the_user_docs_each_with_its_three_parts(repo, runner):
    run_seed(runner, repo.work)

    held = surfaces((repo.work / WHERE["surfaces.md"]).read_text(encoding="utf-8"))

    assert list(held) == ["The README", "The user docs"]
    for name, section in held.items():
        for part in SURFACE_PARTS:
            assert section.count(part) == 1, "{} lacks {}".format(name, part)


def worked_examples(text):
    return re.findall(r"^```markdown\n(.*?)^```", text, re.MULTILINE | re.DOTALL)


def test_the_surfaces_seed_carries_one_worked_example_that_is_no_surface_of_its_own():
    fences = worked_examples(seeded("surfaces.md"))

    assert len(fences) == 1
    assert fences[0].startswith("## The sample app\n")
    assert "`samples/`" in fences[0]
    for part in SURFACE_PARTS:
        assert fences[0].count(part) == 1, part
    assert "The sample app" not in surfaces(seeded("surfaces.md"))


@pytest.mark.parametrize("page", ["docs/skillworks/surfaces.md", "docs/usage/steering.md"])
def test_this_repos_surfaces_and_the_steering_page_show_the_seeds_worked_example(page):
    assert worked_examples(seeded("surfaces.md"))[0] in worked_examples((ROOT / page).read_text(encoding="utf-8"))


def test_a_surface_written_only_inside_a_fence_is_not_counted():
    text = "# Surfaces\n\n```markdown\n## The changelog\n```\n\n## The README\n"

    assert list(surfaces(text)) == ["The README"]


def test_this_repos_surfaces_list_the_usage_docs():
    held = surfaces((ROOT / "docs" / "skillworks" / "surfaces.md").read_text(encoding="utf-8"))

    assert "`docs/usage/`" in [where_it_lives(section).strip() for section in held.values()]


def test_this_repos_surfaces_hold_the_seeds_readme_surface():
    ours = surfaces((ROOT / "docs" / "skillworks" / "surfaces.md").read_text(encoding="utf-8"))

    assert ours.get("The README") == surfaces(seeded("surfaces.md"))["The README"]


def test_no_skill_holds_the_smells():
    pages = sorted([*SKILLS.glob("*/SKILL.md"), *SKILLS.glob("review-changes/*.md")])
    assert SKILLS / "review-changes" / "standards.md" in pages

    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert "Feature Envy" not in text, page
        assert "Stub Echo" not in text, page
        assert "twelve" not in text.lower(), page


def test_review_standards_renames_a_name_whose_meaning_the_change_moved_in_the_same_ticket():
    text = axis_text("review-standards")

    assert "rename it in the same ticket" in text
    assert "a comment edited above a declaration whose name did not change" in text
    assert "optional" not in text.lower()


@pytest.mark.parametrize("skill", ["review-standards", "review-architecture", "review-spec"])
def test_each_axis_always_fixes_a_hard_breach_and_leaves_a_judgement_call_only_with_its_reason(skill):
    fixing = section(axis_text(skill), "Fix what you find")

    assert "A hard breach is always fixed and never left" in fixing
    assert "a team check" in fixing
    assert "a rule marked hard" in fixing
    assert "A judgement call may be left, with the reason" in fixing


def test_implements_fixing_section_never_leaves_a_hard_breach():
    fixing = section(skill_text("implement"), "Fixing")

    assert "A hard breach is always fixed and never left" in fixing
    assert "A judgement call may be left" in fixing


@pytest.mark.parametrize("page", [page for seed in REVIEW_FILES for page in (SETUP / "seeds" / seed, ROOT / WHERE[seed])])
def test_a_review_seed_and_this_repos_copy_say_a_check_that_shapes_the_build_is_a_rule(page):
    checks = section(page.read_text(encoding="utf-8"), "Checks")

    assert "A check that should also shape the build goes in a rule in `docs/skillworks/rules/` instead." in checks
    assert "this file is read only by its review" in checks


def ticket_shape(tracker):
    lines = tracker.splitlines()
    assert "## The ticket shape" in lines, "no ticket shape"
    start = lines.index("## The ticket shape")
    fenced = False
    for end in range(start + 1, len(lines)):
        if lines[end].startswith("```"):
            fenced = not fenced
        elif not fenced and lines[end].startswith("## "):
            return "\n".join(lines[start:end])
    return "\n".join(lines[start:])


def test_the_issue_tracker_seed_holds_the_ticket_shape():
    shape = ticket_shape(seeded("issue-tracker.md"))

    assert "single fresh context window" in shape
    assert '"TICKET:"' in shape
    assert "## Acceptance criteria" in shape
    assert "## Blocked by" in shape
    assert "avoid specific file paths" in shape


def test_this_repos_tracker_docs_hold_the_seeds_ticket_shape():
    ours = (ROOT / "docs" / "skillworks" / "issue-tracker.md").read_text(encoding="utf-8")

    assert ticket_shape(ours) == ticket_shape(seeded("issue-tracker.md"))


def files_tracker(tracker):
    assert "\n## The files Tracker\n" in tracker, "no files Tracker"
    return tracker.split("\n## The files Tracker\n", 1)[1].split("\n## ", 1)[0]


def test_the_issue_tracker_seed_says_how_a_ticket_closes_with_the_files_tracker():
    files = files_tracker(seeded("issue-tracker.md"))

    assert "`.specs/`" in files
    assert "`Ticket: <spec>/<ticket>`" in files
    assert "`status: closed`" in files
    assert "`{}`".format(CLOSING_NOTE) in files
    assert "closed in the commit that holds its code" in files


def test_this_repos_tracker_docs_hold_the_seeds_files_tracker():
    ours = (ROOT / "docs" / "skillworks" / "issue-tracker.md").read_text(encoding="utf-8")

    assert files_tracker(ours) == files_tracker(seeded("issue-tracker.md"))


READ_A_TICKET = "`gh issue view <number> --json number,title,state,labels,body,comments`"


def ticket_reads(tracker):
    return [line for line in tracker.splitlines() if "gh issue view <number>" in line]


# With `--comments` and its output in a pipe, `gh` prints the comments and never the body.
def test_the_issue_tracker_seed_reads_a_ticket_with_its_body_and_its_comments():
    assert ticket_reads(seeded("issue-tracker.md")) == [
        "- **Read an issue**: {}.".format(READ_A_TICKET),
        "Run {}.".format(READ_A_TICKET),
    ]


def test_this_repos_tracker_docs_read_a_ticket_as_the_seed_does():
    ours = (ROOT / "docs" / "skillworks" / "issue-tracker.md").read_text(encoding="utf-8")

    assert ticket_reads(ours) == ticket_reads(seeded("issue-tracker.md"))


def test_to_tickets_reads_the_ticket_shape_from_the_tracker_docs():
    to_tickets = (SKILLS / "to-tickets" / "SKILL.md").read_text(encoding="utf-8")

    assert "The ticket shape" in to_tickets
    assert "context window" not in to_tickets
    assert "TICKET:" not in to_tickets
    assert "## Acceptance criteria" not in to_tickets
    assert "-template>" not in to_tickets


def test_to_tickets_reads_the_tracker_docs_by_their_path_from_the_repo_root():
    assert ('Read `steering-file docs/skillworks/issue-tracker.md`. Its section "The ticket shape"'
            in (SKILLS / "to-tickets" / "SKILL.md").read_text(encoding="utf-8"))


# A heading that calls the step optional is leave to skip it, and the read of the domain docs with it.
def test_to_tickets_finds_the_glossary_through_the_domain_docs_in_a_step_it_may_not_skip():
    to_tickets = (SKILLS / "to-tickets" / "SKILL.md").read_text(encoding="utf-8")

    assert ("\n### 2. Explore the codebase\n\nRead `steering-file docs/skillworks/domain.md`: it says where this repo keeps its "
            "glossary and its ADRs.") in to_tickets
    assert "CONTEXT.md" not in to_tickets


def skill_text(skill):
    return (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")


def read_of(path):
    return "`steering-file {}`".format(path)


def names_steering(text, path):
    return read_of(path) in text


AXIS_FILE_OF = {
    "review-standards": "standards.md",
    "review-architecture": "architecture.md",
    "review-spec": "spec.md",
}


def axis_page(skill):
    return SKILLS / "review-changes" / AXIS_FILE_OF[skill]


def axis_text(skill):
    return axis_page(skill).read_text(encoding="utf-8")


def test_to_tickets_publishes_to_the_files_tracker_and_no_scratch_folder():
    to_tickets = skill_text("to-tickets")

    assert ".scratch" not in to_tickets
    assert "tracker-publish tickets <spec> <file>..." in to_tickets
    assert "`blocked-by`" in to_tickets
    assert "`status: open`" in to_tickets


def test_to_spec_publishes_to_the_files_tracker_on_the_specs_branch_in_pr_mode():
    to_spec = skill_text("to-spec")

    assert "tracker-publish spec <slug> .spec-loop/drafts/<slug>.md" in to_spec
    assert "tracker-publish spec <slug> .spec-loop/drafts/<slug>.md <the branch own-branch printed>" in to_spec
    assert "`.specs/`" in to_spec


PR_MODE_BRANCH_SECTIONS = [("domain-modeling", "### The spec's branch"), ("to-spec", "## The spec's branch")]


def test_in_pr_mode_the_grill_runs_the_branch_check_before_its_first_question():
    first = grill_cut(skill_text("grill"))

    for named in ["PR mode", "`own-branch`", "before the first question"]:
        assert named in first, named


def test_on_a_refused_branch_the_grill_asks_no_question_and_writes_nothing():
    first = grill_cut(skill_text("grill"))
    refused = first.split("`own-branch`", 1)[1].split("\n#### ", 1)[0]

    for named in ["refuses", "Ask no question", "write nothing", "Pass on what it said"]:
        assert named in refused, named


def test_in_pr_mode_to_spec_runs_the_branch_check_and_publishes_nothing_on_a_refusal():
    text = under_heading(skill_text("to-spec"), "## The spec's branch")

    for named in ["`own-branch`", "refuses", "publish no spec", "write nothing"]:
        assert named in text, named


def test_only_the_grill_and_to_spec_run_the_branch_check():
    naming = sorted(str(page.relative_to(SKILLS)).replace("\\", "/") for page in SKILLS.rglob("*.md")
                    if "own-branch" in page.read_text(encoding="utf-8"))

    assert naming == ["grill/SKILL.md", "to-spec/SKILL.md"]


@pytest.mark.parametrize("skill, heading", PR_MODE_BRANCH_SECTIONS)
def test_in_pr_mode_the_specs_branch_is_the_developers_branch_the_session_is_on(skill, heading):
    text = under_heading(skill_text(skill), heading)

    for named in ["the branch this session is on", "the developer's own branch", "Open no pull request"]:
        assert named in text, named


@pytest.mark.parametrize("skill, heading", PR_MODE_BRANCH_SECTIONS)
def test_in_pr_mode_no_git_step_and_no_gh_call_cuts_a_branch_or_opens_a_pull_request(skill, heading):
    text = under_heading(skill_text(skill), heading)

    assert git_and_gh_lines(text) == []


def test_in_pr_mode_context_backfill_refuses_a_branch_that_cannot_hold_a_design_and_reads_the_default_branch():
    text = " ".join(under_heading(skill_text("context-backfill"), "## Check the clone").split())

    for named in ["PR mode", "the branch this session starts on", "refuses, and writes nothing",
                  "on the default branch, on a branch under `skillworks/` and on no branch",
                  "In PR mode the history is read from the default branch, and not from the Target branch"]:
        assert named in text, named


def test_in_pr_mode_the_backfill_apply_cuts_no_branch_opens_no_pull_request_and_ends_with_the_loops_hint():
    text = under_heading(skill_text("context-backfill"), "### Apply the sheet")

    for named in ["run it on the branch this session started on", "commits on the branch it started on",
                  "cuts no branch of its own and opens no pull request",
                  "`{}`".format(open_the_pull_request("<branch>").split(".")[0])]:
        assert named in text, named


@pytest.mark.parametrize("named", ["spec/<slug>", "spec/context-backfill", "gh pr create", ".default_branch"])
def test_no_skill_cuts_a_spec_branch_opens_a_pull_request_or_asks_gh_for_the_default_branch(named):
    walked = {str(page.relative_to(SKILLS)).replace("\\", "/"): page.read_text(encoding="utf-8")
              for page in SKILLS.rglob("*.md")}
    naming = sorted(name for name, text in walked.items() if named in text)

    assert ("grill/SKILL.md" in walked, naming) == (True, [])


def test_to_spec_reports_the_branch_in_pr_mode():
    [report] = re.findall(r"^\d+\. Report .*$", skill_text("to-spec"), re.MULTILINE)

    assert "In PR mode, report the branch the spec was published with" in report
    assert "pull request's URL" not in report


def under_heading(text, heading):
    return text.split("\n" + heading + "\n", 1)[1].split("\n#", 1)[0]


EXPORT_BRANCH_SECTIONS = [("domain-modeling", "### The spec's branch with the Export"),
                          ("to-spec", "## The spec's branch with the Export")]


def grill_cut(grill):
    return grill.split("\n### 1. ", 1)[1].split("\n### ", 1)[0]


def git_and_gh_lines(text):
    return [line for line in text.split("\n")
            if line.startswith(("gh ", "git ", "default=")) or "gh pr" in line or "gh api" in line]


def test_the_grills_first_step_cuts_the_target_branch_when_loop_json_is_missing_on_disk():
    grill = skill_text("grill")
    steps = grill_steps(grill)
    cut = grill_cut(grill)

    assert "Target branch" in steps[0]
    assert "Interview" in steps[1]
    for named in ["`docs/skillworks/loop.json` is missing on disk", "before the first question",
                  "`cut-target-branch`", "`skillworks/spec/<the Export branch>`", "`skillworks/steering`",
                  "Open no pull request"]:
        assert named in cut, named


def test_the_grill_runs_no_git_step_and_no_gh_call_by_hand_for_the_cut():
    cut = grill_cut(skill_text("grill"))

    assert git_and_gh_lines(cut) == []


def test_an_existing_target_branch_stops_the_grill_with_a_switch_and_a_new_session():
    cut = grill_cut(skill_text("grill"))
    existing = [line for line in cut.split("\n") if "already exists" in line]

    assert len(existing) == 1
    assert "switches to that branch" in existing[0] and "starts a new session there" in existing[0]


def test_a_steering_branch_that_does_not_rebase_or_is_not_on_origin_stops_the_grill_with_no_question():
    cut = grill_cut(skill_text("grill"))

    assert "does not rebase" in cut and "no Steering branch is on `origin`" in cut
    assert "stop the grill" in cut and "Ask no question" in cut


@pytest.mark.parametrize("skill", ["domain-modeling", "to-spec"])
def test_on_an_export_branch_domain_modeling_and_to_spec_stop_and_send_the_developer_to_the_grill(skill):
    text = under_heading(skill_text(skill), "## On an Export branch")

    assert "`docs/skillworks/loop.json` is missing on disk" in text
    assert "stop" in text.lower() and "/skillworks:grill" in text


STEERING_WRITERS = ["architecture-tests", "context-backfill"]


@pytest.mark.parametrize("skill", STEERING_WRITERS)
def test_a_skill_that_writes_steering_stops_on_an_export_branch_and_names_the_steering_branch(skill):
    text = under_heading(skill_text(skill), "## On an Export branch")

    for named in ["`docs/skillworks/loop.json` is missing on disk", "Stop here", "`skillworks/steering`", "push"]:
        assert named in text, named


@pytest.mark.parametrize("skill", STEERING_WRITERS)
def test_a_skill_that_writes_steering_stops_before_anything_it_runs(skill):
    text = skill_text(skill)
    headings = [line for line in text.split("\n") if line.startswith("## ")]

    assert headings[0] == "## On an Export branch"
    assert "```" not in text.split("## On an Export branch", 1)[0]


def test_no_skill_but_the_grill_names_the_cut_command():
    naming = sorted(str(page.relative_to(SKILLS)).replace("\\", "/") for page in SKILLS.rglob("*.md")
                    if "cut-target-branch" in page.read_text(encoding="utf-8"))

    assert naming == ["grill/SKILL.md"]


@pytest.mark.parametrize("skill, heading", EXPORT_BRANCH_SECTIONS)
def test_with_the_export_the_target_branch_the_grill_cut_takes_every_later_change(skill, heading):
    text = under_heading(skill_text(skill), heading)

    for named in ["`export`", "`skillworks/spec/<the Export branch>`", "`skillworks/steering`",
                  "Open no pull request"]:
        assert named in text, named


@pytest.mark.parametrize("skill, heading", EXPORT_BRANCH_SECTIONS)
def test_with_the_export_no_git_step_and_no_gh_call_is_run_by_hand(skill, heading):
    text = under_heading(skill_text(skill), heading)

    assert git_and_gh_lines(text) == []


@pytest.mark.parametrize("skill, heading", [("domain-modeling", "### The spec's branch"),
                                            ("to-spec", "## The spec's branch")])
def test_the_spec_branch_without_the_export_sends_the_export_case_to_its_own_section(skill, heading):
    text = under_heading(skill_text(skill), heading)

    assert "With `export` set to `true`" in text and "with the Export" in text


def spec_template(to_spec):
    return to_spec.split("<spec-template>", 1)[1].split("</spec-template>", 1)[0]


def test_the_spec_template_has_a_surfaces_section_for_what_the_grill_captured():
    template = spec_template(skill_text("to-spec"))
    headings = re.findall(r"^## (.+)$", template, re.MULTILINE)
    surfaces_section = template.split("\n## Surfaces\n", 1)[1].split("\n## ", 1)[0]

    assert "Surfaces" in headings
    assert headings.index("Surfaces") > headings.index("Implementation Decisions")
    assert read_of(WHERE["surfaces.md"]) in surfaces_section
    assert "the grill captured" in surfaces_section


def grill_steps(grill):
    return re.findall(r"^### \d+\. (.+)$", grill, re.MULTILINE)


def test_the_grills_skill_is_named_grill_and_stays_hidden_from_claude():
    front = skill_text("grill").split("---\n")[1]

    assert "name: grill\n" in front
    assert "disable-model-invocation: true\n" in front


HIDDEN_SKILLS = ("implement", "to-tickets", "grill", "spec-loop", "context-backfill")

VISIBLE_SKILLS = ("tdd", "review-changes", "comment-sweep", "grilling", "domain-modeling", "codebase-design",
                  "diagnosing-bugs", "prototype", "unslop", "architecture-tests", "skillsmith")


def front_matter(skill):
    return skill_text(skill).split("---\n")[1]


# A folded description runs over the indented lines below its key, up to the next key.
def description(skill):
    folded = re.split(r"\n\S", front_matter(skill).split("description:", 1)[1])[0]
    return " ".join(folded.split()).removeprefix("> ")


def hidden(skill):
    return "disable-model-invocation: true\n" in front_matter(skill)


def test_every_hidden_skill_carries_the_flag():
    assert [skill for skill in HIDDEN_SKILLS if not hidden(skill)] == []


def test_every_visible_skill_can_be_invoked_by_claude():
    assert [skill for skill in VISIBLE_SKILLS if hidden(skill)] == []


# The Grill calls to-spec through the Skill tool, which refuses a hidden skill.
def test_to_spec_can_be_invoked_by_claude():
    assert not hidden("to-spec")


FRONT_MATTER_KEYS = {"name", "description", "argument-hint", "disable-model-invocation"}


# Claude Code ignores a key it does not know and says nothing, so a misspelt flag would show a hidden skill to Claude.
def test_every_skill_keeps_to_the_front_matter_keys_the_plugin_uses():
    strays = {}
    for skill in sorted(folder.name for folder in SKILLS.iterdir() if (folder / "SKILL.md").exists()):
        keys = set(re.findall(r"^([A-Za-z_-]+):", front_matter(skill), re.MULTILINE))
        if keys - FRONT_MATTER_KEYS or not {"name", "description"} <= keys:
            strays[skill] = sorted(keys)

    assert strays == {}


def test_to_spec_points_a_plain_talk_at_the_grill():
    assert description("to-spec").endswith(
        "Not for turning a plain talk into a spec: the developer starts the Dev loop with "
        "/skillworks:grill, which runs this skill at its end.")


def test_to_spec_reports_the_spec_loop_as_the_next_step_and_no_other_skill():
    [report] = re.findall(r"^\d+\. Report .*$", skill_text("to-spec"), re.MULTILINE)

    skills = {folder.name for folder in SKILLS.iterdir() if (folder / "SKILL.md").exists()}

    assert set(re.findall(r"[\w-]+", report)) & skills == {"spec-loop"}


def skill_tool_calls():
    calls = []
    for page in sorted(SKILLS.rglob("*.md")):
        for line in page.read_text(encoding="utf-8").split("\n"):
            if "Skill tool" in line:
                calls += [(page.relative_to(SKILLS).as_posix(), called)
                          for called in re.findall(r'"skillworks:([\w-]+)"', line)]
    return calls


# The Skill tool refuses a skill that sets the flag, so such a call would fail in every Session.
def test_no_skill_calls_a_hidden_skill_through_the_skill_tool():
    assert [call for call in skill_tool_calls() if hidden(call[1])] == []


# `.spec-loop/` is a working folder and `spec-loop/<n>` is a branch, so neither points into a skill's folder.
def paths_into(skill, text):
    return re.findall(r"(?:\.\./|skills/){0}/|(?<![\w.-]){0}/[\w./-]*\w\.\w+".format(re.escape(skill)), text)


def hidden_skills():
    return sorted(folder.name for folder in SKILLS.iterdir() if (folder / "SKILL.md").exists() and hidden(folder.name))


# A skill that reads a hidden skill's file follows it by other means, which the Skill tool's refusal forbids.
def test_no_skill_names_a_path_into_a_hidden_skills_folder():
    assert set(AXIS_FILE_OF) <= set(hidden_skills())
    named = [(page.relative_to(SKILLS).as_posix(), skill)
             for page in sorted(SKILLS.rglob("*.md")) for skill in hidden_skills()
             if paths_into(skill, page.read_text(encoding="utf-8"))]

    assert named == []


@pytest.mark.parametrize("text", ["`../review-spec/SKILL.md`", "plugins/skillworks/skills/review-spec/", "review-spec/notes.md"])
def test_a_path_into_a_skills_folder_is_caught(text):
    assert paths_into("review-spec", text)


@pytest.mark.parametrize("text", ["`.spec-loop/<spec>/base.sha`", "`spec-loop/<spec-number>/ticket-<n>-kept-<k>`",
                                  "`/skillworks:spec-loop 42`"])
def test_a_working_folder_or_a_branch_is_not_a_path_into_a_skills_folder(text):
    assert paths_into("spec-loop", text) == []


def test_the_walk_for_skill_tool_calls_finds_the_grills_call_to_to_spec():
    assert ("grill/SKILL.md", "to-spec") in skill_tool_calls()


# A loop Session may not write outside its checkout, and one rule for all four stops a copy bringing it back.
@pytest.mark.parametrize("skill", ["to-spec", "to-tickets", "spec-drift", "spec-names"])
def test_a_skill_that_publishes_writes_its_file_in_the_ignored_loop_folder(skill):
    text = skill_text(skill)

    assert "`.spec-loop/" in text and "mktemp" not in text and "outside the repo" not in text


def test_the_spec_loop_skill_leaves_cutting_the_tickets_to_the_driver():
    spec_loop = skill_text("spec-loop")

    assert "to-tickets" not in spec_loop
    assert "into tickets" not in description("spec-loop")


def test_the_grill_ends_by_naming_only_the_spec_loop_as_the_next_command():
    grill = skill_text("grill")
    last_step = grill_steps(grill)[-1]
    end = grill.split(". " + last_step + "\n", 1)[1].split("\n## ", 1)[0]
    report = end.split('"skillworks:to-spec"', 1)[1]

    assert re.findall(r"/skillworks:[\w-]+", report) == ["/skillworks:spec-loop"]
    assert "`/skillworks:spec-loop <n>`" in report


def test_grilling_sends_a_design_that_ends_in_a_spec_to_the_grill():
    front = skill_text("grilling").split("---\n")[1]

    assert "Not for a design that should end in a spec: the user starts that with /skillworks:grill," in front


OLD_GRILL = "grill" + "-with-docs"


def user_docs(root):
    return list((root / "docs" / "usage").rglob("*.md"))


def test_the_user_docs_are_read_in_the_folders_below_too(tmp_path):
    below = tmp_path / "docs" / "usage" / "the-loop" / "tracker.md"
    below.parent.mkdir(parents=True)
    below.write_text("# The Tracker\n", encoding="utf-8")

    assert user_docs(tmp_path) == [below]


def test_no_skill_seed_script_or_user_doc_names_the_grills_old_skill():
    pages = [path for path in PLUGIN.rglob("*") if path.is_file() and path.suffix in (".md", ".py", ".mjs", ".json")]
    pages += user_docs(ROOT)
    pages += [ROOT / "docs" / "skillworks" / "domain.md"]
    assert {SKILLS / "grill" / "SKILL.md", SETUP / "seeds" / "domain.md", ROOT / "docs" / "usage" / "the-loop.md"} <= set(pages)

    named = [str(path.relative_to(ROOT)) for path in pages if OLD_GRILL in path.read_text(encoding="utf-8")]

    assert named == []


OLD_SKILLSMITH = "writing" + "-for-agents"


def test_no_skill_seed_script_or_user_doc_names_skillsmiths_old_name():
    pages = [path for path in PLUGIN.rglob("*") if path.is_file() and path.suffix in (".md", ".py", ".mjs", ".json")]
    pages += user_docs(ROOT)
    assert {SKILLS / "skillsmith" / "SKILL.md", SETUP / "seeds" / "domain.md", ROOT / "docs" / "usage" / "steering.md"} <= set(pages)

    named = [str(path.relative_to(ROOT)) for path in pages if OLD_SKILLSMITH in path.read_text(encoding="utf-8")]

    assert named == []


def test_skillsmith_carries_its_own_description():
    assert description("skillsmith").strip('"') == (
        "Rules for writing a document an agent reads. Use when creating or editing a skill, a CLAUDE.md or AGENTS.md,"
        " a rule file, a subagent brief, or a prompt a script sends. Not for prose a person reads: that is unslop.")


def test_the_grill_walks_the_surfaces_after_the_design_questions_and_before_the_sum_up():
    grill = skill_text("grill")
    steps = grill_steps(grill)
    walk = [step for step in steps if "Surfaces" in step]

    assert len(walk) == 1
    assert "Interview" in steps[steps.index(walk[0]) - 1]
    assert "sum up" in steps[steps.index(walk[0]) + 1].lower()


def test_the_grill_names_the_surfaces_file_and_the_four_rules_for_asking():
    grill = skill_text("grill")
    walk = grill.split("Surfaces", 1)[1].split("\n### ", 1)[0]

    assert read_of(WHERE["surfaces.md"]) in walk
    for rule in ("one Surface at a time", "never present the list", "does not touch", "requirement",
                 "never copy"):
        assert rule in walk, rule
    assert "no Surface" in walk
    assert "skip" in walk


def test_the_grills_sum_up_lists_each_surfaces_answer():
    grill = skill_text("grill")
    sum_up = grill.split("Sum up", 1)[1].split("\n### ", 1)[0]

    assert "Surface" in sum_up


def stage_map_row(stage):
    stage_map = STAGE_MAP_PAGE.read_text(encoding="utf-8").split("<!-- stage map -->", 1)[1]
    rows = [line for line in stage_map.splitlines() if line.startswith("| {} |".format(stage))]
    assert len(rows) == 1, stage
    return rows[0]


@pytest.mark.parametrize("stage", ["The grill", "The spec", "`spec`", "The drift check"])
def test_the_stage_map_names_the_surfaces_file_for_each_stage_that_reads_it(stage):
    assert "`surfaces.md`" in stage_map_row(stage)


@pytest.mark.parametrize("stage", ["The grill", "Context backfill"])
def test_the_stage_map_shows_each_adr_writer_loading_the_adr_shape_file(stage):
    assert "`adr-format.md`" in stage_map_row(stage)


def test_the_grill_page_says_a_settled_adr_goes_to_the_setting_in_the_teams_shape():
    page = (ROOT / "docs" / "usage" / "the-loop" / "the-grill.md").read_text(encoding="utf-8")
    paragraphs = [paragraph for paragraph in page.split("\n\n") if "`docs/skillworks/adr-format.md`" in paragraph]

    assert len(paragraphs) == 1
    assert "`adr-folder`" in paragraphs[0]


def test_the_steering_page_has_a_row_for_the_adr_shape_file():
    rows = [line for line in STEERING_PAGE.read_text(encoding="utf-8").splitlines()
            if line.startswith("| `adr-format.md` |")]

    assert len(rows) == 1
    assert "template" in rows[0]
    assert "grill" in rows[0]
    assert "Skillworks shape" in rows[0]


def test_the_tickets_keep_each_surface_inside_the_ticket_that_needs_it():
    to_tickets = skill_text("to-tickets")

    assert "Surfaces section" in to_tickets
    assert "inside the ticket whose change needs it" in to_tickets
    assert "No ticket only updates a Surface" in to_tickets


def test_the_spec_review_checks_each_surface_the_spec_names_for_the_ticket():
    review = axis_text("review-spec")

    assert "Surfaces section" in review
    assert "Surface the spec names" in review


def test_the_drift_check_checks_and_reports_each_surface_the_spec_names():
    drift = skill_text("spec-drift")

    assert "Surfaces section" in drift
    assert "every Surface the spec names" in drift
    assert "In step" in drift


def test_the_drift_check_given_a_list_of_items_judges_those_alone():
    drift = skill_text("spec-drift")

    assert "`/skillworks:spec-drift 42 a1b2c3d S2, D1, The user docs`" in drift
    assert "judge only those items" in drift
    assert "write Verdicts for those alone" in drift


def test_the_files_tracker_docs_say_how_to_list_what_is_open_and_record_a_drift_report():
    files = files_tracker(seeded("issue-tracker.md"))

    assert "**List what is open**" in files
    assert "tracker-publish drift <spec> <file>" in files
    assert "`{}`".format(DRIFT_REPORT) in files
    assert "tracker-publish names <spec> <file>" in files
    assert "`{}`".format(NAME_REPORT) in files


@pytest.mark.parametrize("page", [SKILLS / "what-next" / "SKILL.md", SKILLS / "review-changes" / "spec.md",
                                  SKILLS / "spec-drift" / "SKILL.md", SKILLS / "spec-names" / "SKILL.md"],
                         ids=lambda page: page.relative_to(SKILLS).as_posix())
def test_a_skill_that_reads_the_tracker_reads_it_through_the_tracker_docs(page):
    text = page.read_text(encoding="utf-8")

    assert "docs/skillworks/issue-tracker.md" in text
    assert "docs/skillworks/loop.json" in text
    assert re.search(r"\bgh\b", text) is None


GITHUB_ONLY_NAMES = ("the ticket's issue number", "the spec's issue number", "sub-issues of the spec")


@pytest.mark.parametrize("page", [SKILLS / "review-changes" / "standards.md", SKILLS / "review-changes" / "architecture.md",
                                  SKILLS / "spec-loop" / "SKILL.md", SKILLS / "what-next" / "SKILL.md"],
                         ids=lambda page: page.relative_to(SKILLS).as_posix())
def test_a_skill_names_a_spec_or_a_ticket_in_words_that_fit_either_tracker(page):
    text = page.read_text(encoding="utf-8")

    assert "docs/skillworks/issue-tracker.md" in text
    assert [name for name in GITHUB_ONLY_NAMES if name in text] == []


def test_what_next_lists_open_specs_and_startable_tickets_from_the_files_tracker():
    what_next = skill_text("what-next")

    assert "`.specs/`" in what_next
    assert "startable" in what_next
    assert "List what is open" in what_next


def test_review_spec_reads_a_files_ticket_from_its_folder_in_the_worktree():
    review_spec = axis_text("review-spec")

    assert "`<spec>/<ticket>`" in review_spec
    assert "`spec.md`" in review_spec
    assert "worktree" in review_spec


def test_spec_drift_records_its_report_with_the_spec_under_the_heading_the_loop_reads():
    spec_drift = skill_text("spec-drift")

    assert "tracker-publish drift <spec> .spec-loop/<spec>/drift-report.md" in spec_drift
    assert "`{}`".format(DRIFT_REPORT) in spec_drift
    assert "`spec.md`" in spec_drift


def test_spec_drift_reads_the_spec_commits_and_judges_the_target_branch_as_it_stands():
    spec_drift = skill_text("spec-drift")

    assert "spec-commits <spec> <base>" in spec_drift
    assert "git diff <base>..origin/<target>" not in spec_drift
    assert "Judge the Target branch as it stands" in spec_drift
    assert "behaviour in the spec's commits that no story and no ticket asked for" in spec_drift
    assert "only when it still stands on `origin/<target>`" in spec_drift


def test_spec_drift_finds_the_glossary_through_the_domain_docs_and_names_no_glossary_file_itself():
    spec_drift = skill_text("spec-drift")

    assert "`steering-file docs/skillworks/domain.md` says where this repo keeps its glossaries." in spec_drift
    assert "CONTEXT.md" not in spec_drift


# A hand run with the files Tracker fetches as the tracker docs say, so the ban holds only where the driver fetched.
def test_spec_drift_runs_no_fetch_of_its_own_under_the_loop_alone():
    assert ("Under the spec loop, run no `git fetch` of your own, even where "
            "`steering-file docs/skillworks/issue-tracker.md` names one.") in skill_text("spec-drift")


def test_spec_drift_says_its_report_is_recorded_when_the_command_prints_where_it_went():
    assert ("The report is recorded when the command prints the comment's URL, or the path of "
            "`spec.md`.") in skill_text("spec-drift")


def test_spec_drift_posts_nothing_on_the_spec_after_its_report_because_the_loop_reads_the_last_comment():
    assert ("the loop reads the last one, so post nothing on the spec after the report"
            in skill_text("spec-drift"))


@pytest.mark.parametrize("command", ["spec-commits", "tracker-publish"])
def test_spec_drift_ends_a_command_that_refuses_twice_on_the_blocked_line_under_the_loop(command):
    refused = [paragraph for paragraph in skill_text("spec-drift").split("\n\n")
               if "If `{}` refuses".format(command) in paragraph]

    assert [all(said in paragraph for said in ("run it again once", "If it refuses again, stop",
                                               "Under the spec loop", "`BLOCKED`"))
            for paragraph in refused] == [True]


def test_spec_names_reads_only_the_spec_commits_and_the_glossary_and_records_a_name_report():
    spec_names = skill_text("spec-names")

    assert "spec-commits <spec> <base>" in spec_names
    assert "git diff <base>..origin/<target>" not in spec_names
    assert "**The glossary of each context the spec's commits touch.**" in spec_names
    assert "**List a name only when it still stands on the Target branch.**" in spec_names
    assert "Read nothing else: not the spec, not its tickets, not the drift report" in spec_names
    assert "**A name whose meaning moved.**" in spec_names
    assert "**A concept two tickets named two ways.**" in spec_names
    assert 'A rename is never "Optional"' in spec_names
    assert "The first line is `{}`.".format(NAME_REPORT) in spec_names
    assert "The `### Renames` list comes next." in spec_names
    assert "tracker-publish names <spec> .spec-loop/<spec>/names-report.md" in spec_names


def test_spec_names_finds_the_glossary_through_the_domain_docs_and_names_no_glossary_file_itself():
    spec_names = skill_text("spec-names")

    assert "`steering-file docs/skillworks/domain.md` says where this repo keeps its glossaries." in spec_names
    assert "CONTEXT.md" not in spec_names


# Each fence says to read nothing else, so one that names no Steering file cuts the team's files out.
def test_spec_names_keeps_the_steering_files_it_names_outside_both_read_fences():
    spec_names = skill_text("spec-names")
    fence = [paragraph for paragraph in spec_names.split("\n\n") if paragraph.startswith("Read nothing else")]

    assert ["the Steering files this skill reads through `steering-file`" in paragraph for paragraph in fence] == [True]
    assert ("The same three reads go beyond the two as in [What you read](#what-you-read)."
            in section(spec_names, "The Name re-check"))


@pytest.mark.parametrize("command", ["spec-commits", "tracker-publish"])
def test_spec_names_ends_a_command_that_refuses_twice_on_the_blocked_line_under_the_loop(command):
    refused = [paragraph for paragraph in skill_text("spec-names").split("\n\n")
               if "If `{}` refuses".format(command) in paragraph]

    assert [all(said in paragraph for said in ("run it again once", "If it refuses again, stop",
                                               "Under the spec loop", "`BLOCKED`"))
            for paragraph in refused] == [True]


def test_tdd_finds_the_glossary_through_the_domain_docs_and_names_no_glossary_file_itself():
    tdd = skill_text("tdd")

    assert "read `steering-file docs/skillworks/domain.md`: it says where this repo keeps its glossary and its ADRs." in tdd
    assert "CONTEXT.md" not in tdd


# `tests.md` holds the pointer to the determinism rule, so a body that drops its link leaves that pointer unread.
def test_tdd_says_when_to_read_the_file_that_names_the_determinism_rule():
    assert "Read [tests.md](tests.md) before the first test when" in skill_text("tdd")


def codebase_design_pages():
    return {page.name: page.read_text(encoding="utf-8") for page in sorted((SKILLS / "codebase-design").glob("*.md"))}


def test_codebase_design_finds_the_glossary_through_the_domain_docs_and_names_no_glossary_file_itself():
    pages = codebase_design_pages()

    assert ("read `steering-file docs/skillworks/domain.md`: it says where this repo keeps its glossary and its ADRs."
            in pages["DESIGN-IT-TWICE.md"])
    assert [name for name, text in pages.items() if "CONTEXT.md" in text] == []


def test_codebase_design_lets_the_testing_rule_win_where_the_two_differ_on_what_to_fake():
    categories = codebase_design_pages()["DEEPENING.md"].split("\n## Dependency categories\n", 1)[1].split("\n## ", 1)[0]

    assert ("Where `steering-file docs/skillworks/rules/testing.md` prints the rule and it rules differently on what to fake or mock, "
            "the rule wins.") in categories


# Each file holds a pointer to a Steering file, so a body that drops its pointer leaves that Steering file unread.
@pytest.mark.parametrize("page", ["DEEPENING.md", "DESIGN-IT-TWICE.md"])
def test_codebase_design_says_when_to_read_each_file_that_names_a_steering_file(page):
    assert "Read `${{CLAUDE_SKILL_DIR}}/{}` when".format(page) in skill_text("codebase-design")


def stops(skill, *names):
    return says_stop((SKILLS / skill / "SKILL.md").read_text(encoding="utf-8"), *names)


def says_stop(text, *names):
    return any(
        "stop" in paragraph.lower()
        and "missing" in paragraph
        and "`/skillworks:skillworks-setup`" in paragraph
        and all(name in paragraph for name in names)
        for paragraph in text.split("\n\n")
    )


REVIEW_FILE_OF = {
    "review-standards": "review-standards.md",
    "review-architecture": "review-architecture.md",
    "review-spec": "review-spec.md",
}


def test_each_axis_stops_when_its_review_file_is_missing():
    for skill, name in REVIEW_FILE_OF.items():
        assert says_stop(axis_text(skill), read_of(WHERE[name])), skill


def test_each_axis_begins_its_loop_mode_report_with_a_blocked_line_when_its_review_file_is_missing():
    for skill, name in REVIEW_FILE_OF.items():
        assert says_stop(axis_text(skill), read_of(WHERE[name]), "`BLOCKED`", "In loop mode"), skill


def test_review_changes_stops_when_the_tracker_docs_are_missing():
    assert stops("review-changes", read_of("docs/skillworks/issue-tracker.md"))


def test_to_tickets_stops_when_the_tracker_docs_or_the_ticket_shape_is_missing():
    assert stops("to-tickets", read_of("docs/skillworks/issue-tracker.md"), '"The ticket shape"')


def test_to_tickets_stops_when_the_domain_docs_are_missing():
    assert stops("to-tickets", read_of("docs/skillworks/domain.md"))


def test_to_tickets_begins_its_last_message_with_a_blocked_line_under_the_loop_when_a_file_or_the_ticket_shape_is_missing():
    assert stops("to-tickets", "`BLOCKED`", "Under the spec loop", "begin your last message",
                 read_of("docs/skillworks/issue-tracker.md"), read_of("docs/skillworks/domain.md"), '"The ticket shape"')


def test_to_tickets_ends_a_command_that_stops_twice_on_one_fault_on_the_blocked_line_under_the_loop():
    stopped = [paragraph for paragraph in skill_text("to-tickets").split("\n\n")
               if "If the command stops a second time on the same fault, stop." in paragraph]

    assert [all(said in paragraph for said in ("Quote what it printed", "Under the spec loop", "`BLOCKED`"))
            for paragraph in stopped] == [True]


def test_tdd_stops_when_the_testing_rule_is_missing():
    assert stops("tdd", read_of("docs/skillworks/rules/testing.md"))


def test_tdd_stops_when_the_domain_docs_are_missing():
    assert stops("tdd", read_of("docs/skillworks/domain.md"))


def test_tdd_begins_its_report_with_a_blocked_line_under_the_loop_when_a_steering_file_it_reads_is_missing():
    assert stops("tdd", "`BLOCKED`", "Under the spec loop", "begin your report",
                 read_of("docs/skillworks/rules/testing.md"), read_of("docs/skillworks/domain.md"))


def test_the_comment_sweep_stops_when_the_comments_rule_is_missing():
    assert stops("comment-sweep", read_of("docs/skillworks/rules/comments.md"))


def test_the_comment_sweep_begins_its_report_with_a_blocked_line_under_the_loop_when_the_comments_rule_is_missing():
    assert stops("comment-sweep", read_of("docs/skillworks/rules/comments.md"), "`BLOCKED`", "Under the spec loop")


SPEC_DRIFT_READS = [read_of(WHERE[name])
                    for name in ("loop.json", "issue-tracker.md", "surfaces.md", "domain.md")]


def test_spec_drift_stops_when_a_steering_file_it_reads_is_missing():
    assert stops("spec-drift", *SPEC_DRIFT_READS)


def test_spec_drift_begins_its_last_message_with_a_blocked_line_under_the_loop_when_a_steering_file_is_missing():
    assert stops("spec-drift", "`BLOCKED`", "Under the spec loop", "begin your last message", *SPEC_DRIFT_READS)


SPEC_NAMES_READS = [read_of(WHERE[name]) for name in ("loop.json", "issue-tracker.md", "domain.md")]


def test_spec_names_stops_when_a_steering_file_it_reads_is_missing():
    assert stops("spec-names", *SPEC_NAMES_READS)


def test_spec_names_begins_its_last_message_with_a_blocked_line_under_the_loop_when_a_steering_file_is_missing():
    assert stops("spec-names", "`BLOCKED`", "Under the spec loop", "begin your last message", *SPEC_NAMES_READS)


def test_implement_stops_on_the_blocked_line_when_a_steering_file_it_reads_is_missing():
    before = section(skill_text("implement"), "Before you start")

    assert says_stop(before, "`BLOCKED`", *(read_of(WHERE[name])
                                           for name in ("loop.json", "issue-tracker.md", "suite.json")))


def test_a_missing_lever_that_only_sends_the_user_to_setup_is_caught():
    tells = "If `docs/skillworks/issue-tracker.md` is missing, tell the user to run `/skillworks:skillworks-setup`."

    assert not says_stop(tells, "`docs/skillworks/issue-tracker.md`")


def test_the_issue_tracker_seed_says_how_to_read_a_commits_sessions_back():
    tracker = seeded("issue-tracker.md")

    assert "`Skillworks-Session: <id>`" in tracker
    assert "git log -1 <commit> --format='%(trailers:key=Skillworks-Session,valueonly)'" in tracker
    assert "claude --resume" in tracker


def test_the_starting_suite_is_valid_and_left_empty_is_not_ready(repo, runner):
    run_seed(runner, repo.work)

    parsed = json.loads((repo.work / "docs" / "skillworks" / "suite.json").read_text(encoding="utf-8"))
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


def test_the_handoff_folder_is_created_beside_a_new_gitignore(repo, runner):
    (repo.work / ".gitignore").unlink(missing_ok=True)

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert (repo.work / ".handoff").is_dir()
    assert "created .handoff/\n" in ran.out
    assert ".handoff/" in (repo.work / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_a_run_that_asks_says_it_would_create_the_handoff_folder_and_creates_nothing(repo, runner):
    edited_on_both_sides(repo, runner, "suite.json", ACROSS["suite.json"])
    (repo.work / ".handoff").rmdir()

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert "would create .handoff/\n" in ran.out
    assert not (repo.work / ".handoff").exists()
    assert "Nothing was written." in ran.out


def test_a_second_run_creates_nothing_more(repo, runner):
    run_seed(runner, repo.work)
    before = on_disk(repo.work)

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert "create" not in ran.out
    assert on_disk(repo.work) == before
    assert list((repo.work / ".handoff").iterdir()) == []


def next_step(ran):
    assert ran.status == 0, ran.err
    lines = [line for line in ran.out.splitlines() if line.startswith("next step: ")]
    assert len(lines) == 1, ran.out
    return lines[0]


def empty_repo(root):
    origin, work = root / "origin.git", root / "work"
    work.mkdir(parents=True)
    git(root, "init", "--quiet", "--bare", "--initial-branch=main", origin.as_posix())
    git(work, "init", "--quiet", "--initial-branch=main")
    for name, value in Repo.SETTINGS:
        git(work, "config", name, value)
    git(work, "remote", "add", "origin", origin.as_posix())
    # Setup refuses an origin with no default branch, so the emptiest repo it can run in holds one empty commit.
    git(work, "commit", "--quiet", "--allow-empty", "-m", "Start")
    git(work, "push", "--quiet", "origin", "main")
    return Path(git(work, "rev-parse", "--show-toplevel").strip())


def test_a_repo_with_a_history_and_no_glossary_is_sent_to_the_backfill_before_architecture_tests(repo, runner):
    step = next_step(run_seed(runner, repo.work))

    assert step == "next step: /skillworks:context-backfill, then /skillworks:architecture-tests"


def test_an_empty_repo_is_sent_to_architecture_tests_alone(tmp_path, runner):
    step = next_step(run_seed(runner, empty_repo(tmp_path)))

    assert step == "next step: /skillworks:architecture-tests"


def test_a_repo_whose_only_commit_is_setups_own_is_sent_to_architecture_tests_alone(tmp_path, runner):
    work = empty_repo(tmp_path)
    run_seed(runner, work)
    git(work, "add", "-A")
    git(work, "commit", "--quiet", "-m", "Set up Skillworks")

    step = next_step(run_seed(runner, work))

    assert step == "next step: /skillworks:architecture-tests"


@pytest.mark.parametrize("glossary", ["CONTEXT.md", "CONTEXT-MAP.md"])
def test_a_repo_with_a_history_and_a_glossary_is_sent_to_architecture_tests_alone(repo, runner, glossary):
    (repo.work / glossary).write_text("# Glossary\n", encoding="utf-8", newline="\n")

    step = next_step(run_seed(runner, repo.work))

    assert step == "next step: /skillworks:architecture-tests"


def test_the_allowlist_names_the_short_commands_and_no_tool_of_a_suite():
    allowed = json.loads((SETUP / "settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]
    commands = sorted(path.name for path in (PLUGIN / "bin").iterdir())

    assert len(commands) == 16
    for command in commands:
        assert "Bash({}:*)".format(command) in allowed
    assert "Bash(git commit:*)" in allowed
    assert "Bash(git push:*)" in allowed
    assert "Bash(gh issue:*)" in allowed
    assert "Bash(gh api:*)" in allowed
    for entry in [entry for entry in allowed if entry.startswith("Bash(")]:
        tool = entry[len("Bash("):].split(" ")[0].split(":")[0]
        assert tool in ["gh", "git"] + commands, entry


def test_the_allowlist_lets_a_skill_read_the_files_of_an_installed_plugin():
    allowed = json.loads((SETUP / "settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]

    assert "Read(~/.claude/plugins/**)" in allowed


def test_the_allowlist_keeps_the_pull_request_commands_a_review_reads_with():
    allowed = json.loads((SETUP / "settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]

    for command in ["gh pr view", "gh pr diff"]:
        assert "Bash({}:*)".format(command) in allowed


def test_the_allowlist_grants_no_pull_request_create_because_the_developer_opens_it():
    allowed = json.loads((SETUP / "settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]

    assert [entry for entry in allowed if entry.startswith("Bash(gh pr create")] == []


def test_the_allowlist_grants_no_pull_request_ready_because_the_loop_marks_none():
    allowed = json.loads((SETUP / "settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]

    assert [entry for entry in allowed if entry.startswith("Bash(gh pr ready")] == []


def test_setup_asks_for_the_tracker_and_suggests_one_from_the_remote():
    step = setup_section("### 2. Ask for the Tracker")

    assert "suggest `github`" in step
    assert "`files`" in step
    assert "github.com" in step
    assert "`tracker`" in step
    assert "`docs/skillworks/loop.json`" in step


def test_setup_says_the_files_tracker_folder_is_committed_and_why():
    step = setup_section("### 2. Ask for the Tracker")

    assert "`.specs/`" in step
    assert "cannot be gitignored" in step
    assert "worktree" in step


def test_setup_skips_the_github_steps_with_the_files_tracker():
    text = (SETUP / "SKILL.md").read_text(encoding="utf-8")
    step = setup_section("### 5. Preflight and labels")

    assert "GitHub only" not in text
    assert "With `files`, it needs no `gh` and creates no label." in step


def test_setup_refuses_a_repo_with_no_remote_with_either_tracker():
    text = (SETUP / "SKILL.md").read_text(encoding="utf-8")

    assert "refuses a repo with no remote, with either Tracker" in text
    assert "A bare repo on a shared drive is enough" in text


def test_setup_asks_for_the_target_branch_and_never_requires_main():
    text = (SETUP / "SKILL.md").read_text(encoding="utf-8")
    step = setup_section("### 3. Ask for the Target branch")

    assert "suggest the remote's default branch" in step
    assert "Offer one other answer: `pr`." in step
    assert "`target-branch`" in step
    assert "`main`" not in text


def test_setup_describes_pr_as_the_developer_making_the_branch_and_opening_the_pull_request():
    step = setup_section("### 3. Ask for the Target branch")

    assert "you make the branch and open the pull request" in step


def test_setup_writes_no_output_style(repo, runner):
    settings = json.loads((SETUP / "settings.json").read_text(encoding="utf-8"))

    run_seed(runner, repo.work)

    assert "outputStyle" not in settings
    assert not (repo.work / ".claude" / "output-styles").exists()
    assert not list(SETUP.rglob("*output-style*"))
    assert "outputStyle" not in (SETUP / "SKILL.md").read_text(encoding="utf-8")


EXPORT_QUESTION = "### First, ask where the work goes"
STEERING_COMMIT = "### Then, with the Export, commit the Steering branch"


def test_setup_asks_whether_the_work_goes_to_a_team_that_does_not_use_skillworks_before_it_seeds():
    text = (SETUP / "SKILL.md").read_text(encoding="utf-8")
    question = setup_section(EXPORT_QUESTION)

    assert text.index(EXPORT_QUESTION) < text.index("### 1. Seed the Steering")
    assert "a team that does not use Skillworks" in question
    assert "With `no`, setup runs as it always has" in question


def test_setup_reads_an_earlier_export_answer_from_the_steering_branch_on_origin():
    question = setup_section(EXPORT_QUESTION)

    assert "git show origin/skillworks/steering:docs/skillworks/loop.json" in question


def test_with_the_export_and_the_files_tracker_setup_tells_the_developer_to_own_origin_first():
    question = setup_section(EXPORT_QUESTION)
    told = [paragraph for paragraph in question.split("\n\n") if "`files`" in paragraph and "`origin`" in paragraph]

    assert len(told) == 1
    assert "a remote of their own" in told[0]
    assert "before" in told[0]


def test_with_the_export_setup_writes_the_steering_on_the_steering_branch_cut_from_the_default_branch():
    question = setup_section(EXPORT_QUESTION)

    for named in ["`skillworks/steering`", "git switch -c skillworks/steering origin/<the default branch>",
                  "`\"export\": true`", "`\"target-branch\": \"pr\"`"]:
        assert named in question, named


def test_with_the_export_setup_asks_no_target_branch_and_writes_pr():
    step = setup_section("### 3. Ask for the Target branch")

    assert "With the Export, ask nothing here, and write `pr`." in step


def test_with_the_export_setup_commits_and_pushes_the_steering_branch_and_switches_back():
    text = (SETUP / "SKILL.md").read_text(encoding="utf-8")
    commit = setup_section(STEERING_COMMIT)

    assert text.index("### 6. Write the settings") < text.index(STEERING_COMMIT) < text.index("### 7. Report")
    for named in ["git push -u origin skillworks/steering", "git switch <the branch they were on>",
                  "no Steering file"]:
        assert named in commit, named


def test_the_setup_page_holds_the_export_question_and_the_advice_to_own_origin():
    page = SETUP_PAGE.read_text(encoding="utf-8")
    questions = page.split("## The questions setup asks", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in questions.splitlines()
            if line.startswith("| Will the work go to a team that does not use Skillworks? |")]

    assert len(rows) == 1
    assert "`files`" in rows[0] and "a remote of your own" in rows[0]
    assert "`skillworks/steering`" in page


def test_the_export_page_names_setup_as_the_first_step_of_the_flow():
    page = (ROOT / "docs" / "usage" / "the-loop" / "export.md").read_text(encoding="utf-8")
    flow = page.split("## Your flow", 1)[1].split("\n## ", 1)[0]
    first = [line for line in flow.splitlines() if line.startswith("1. ")]

    assert len(first) == 1 and "/skillworks:skillworks-setup" in first[0]


def test_the_export_page_says_the_export_needs_pr():
    page = (ROOT / "docs" / "usage" / "the-loop" / "export.md").read_text(encoding="utf-8")

    assert '`"target-branch": "pr"`' in page


OLD_SPEC_VALUE = re.compile(r'"target-branch":\s*"spec"|`target-branch` (?:is|says) `spec`|target-branch says spec')


def test_no_skill_or_seed_names_spec_as_a_value_of_the_target_branch():
    pages = list((ROOT / "plugins" / "skillworks" / "skills").rglob("*.md"))
    named = [path.relative_to(ROOT).as_posix() for path in pages
             if OLD_SPEC_VALUE.search(path.read_text(encoding="utf-8"))]

    assert ROOT / "plugins" / "skillworks" / "skills" / "to-spec" / "SKILL.md" in pages and named == []


def test_the_stops_page_says_an_old_spec_value_is_refused_and_how_to_fix_it():
    page = " ".join(STOPS_PAGE.read_text(encoding="utf-8").split())

    assert '`"target-branch": "spec"`' in page
    assert 'write `"target-branch": "pr"` in `docs/skillworks/loop.json`' in page


# Each is a name only this repository uses, so finding one means a seed was copied, not written.
THIS_REPO = ["Skillworks.", "slnx", "Studio", "Dashboard", "Loki", "Aspire", "dotnet", "npm",
             "dependency-cruiser", "ADR 00", "../adr/", "tests/plugins", "NSubstitute"]


def test_the_seeds_carry_no_fact_about_this_repo():
    names = sorted(WHERE)
    assert len(names) == 15
    for name in names:
        text = seeded(name)
        for fact in THIS_REPO:
            assert fact not in text, "{} names {}".format(name, fact)


def test_the_seed_command_seeds_the_top_of_the_repository(repo):
    below = repo.work / "src" / "deep"
    below.mkdir(parents=True)

    ran = launch("seed-steering", where=below)

    assert ran.status == 0, ran.err
    assert (repo.work / "docs" / "skillworks" / "suite.json").is_file()
    assert not (below / "docs").exists()
    assert git(repo.work, "status", "--porcelain", "--", "docs").strip()


LINK = re.compile(r"\]\(([^)\s]+)\)")


# A link that climbs out of the Plugin resolves only while the Plugin sits in this repo.
def links_out_of_the_plugin(page, text):
    out = []
    for target in LINK.findall(text):
        path = target.split("#")[0]
        if not path or "://" in path or path.startswith("mailto:"):
            continue
        if not (page.parent / path).resolve().is_relative_to(PLUGIN.resolve()):
            out.append(target)
    return out


def test_no_plugin_skill_links_out_of_the_plugin():
    pages = sorted(SKILLS.rglob("*.md"))
    assert pages

    for page in pages:
        assert links_out_of_the_plugin(page, page.read_text(encoding="utf-8")) == [], page


def test_a_link_that_climbs_out_of_the_plugin_is_caught():
    page = SKILLS / "spec-loop" / "SKILL.md"
    text = "[suite](../../../../docs/skillworks/suite.json) and [skill](../tdd/SKILL.md)"

    assert links_out_of_the_plugin(page, text) == ["../../../../docs/skillworks/suite.json"]


def test_no_plugin_skill_names_a_rule_under_the_old_rules_folder():
    pages = sorted(path for path in SKILLS.rglob("*") if path.is_file())
    assert pages

    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert ".claude/rules" not in text, page
        for rule in RULES:
            assert "docs/skillworks/{}".format(rule) not in text, "{} names {} outside the rules folder".format(page, rule)


STEERING_NAMED = {
    "review-standards": ["review-standards.md"],
    "review-architecture": ["placement-checks.md", "review-architecture.md"],
    "review-spec": ["review-spec.md"],
}


def test_the_axis_files_name_each_steering_file_by_its_path_from_the_repo_root():
    for skill, names in STEERING_NAMED.items():
        text = axis_text(skill)
        for name in names:
            assert read_of(WHERE[name]) in text, "{} names {}".format(skill, name)
            assert "{}](".format(read_of(WHERE[name])) not in text, "{} links {}".format(skill, name)


RULES_FOLDER = "docs/skillworks/rules/"

RULES_FOLDER_READERS = ["review-changes/standards.md", "architecture-tests/SKILL.md"]

# A page that drops its pointer leaves the team's file unread, and no other check would show it.
STEERING_READERS = {
    "comments.md": ["comment-sweep/SKILL.md"],
    "determinism.md": ["tdd/tests.md"],
    "file-placement.md": ["review-changes/architecture.md"],
    "testing.md": ["tdd/SKILL.md", "to-spec/SKILL.md", "codebase-design/DEEPENING.md"],
    "issue-tracker.md": ["implement/SKILL.md", "to-tickets/SKILL.md", "spec-drift/SKILL.md", "spec-names/SKILL.md",
                         "spec-loop/SKILL.md", "what-next/SKILL.md", "review-changes/SKILL.md",
                         "review-changes/standards.md", "review-changes/spec.md", "review-changes/architecture.md"],
    "domain.md": ["review-changes/standards.md", "review-changes/architecture.md", "spec-drift/SKILL.md",
                  "spec-names/SKILL.md", "to-tickets/SKILL.md", "tdd/SKILL.md",
                  "codebase-design/DESIGN-IT-TWICE.md", "context-backfill/SKILL.md",
                  "improve-codebase-architecture/SKILL.md"],
    "adr-format.md": ["domain-modeling/WRITING-ADRS.md", "context-backfill/SKILL.md",
                      "improve-codebase-architecture/SKILL.md"],
    "placement-checks.md": ["review-changes/architecture.md", "architecture-tests/SKILL.md"],
    "review-standards.md": ["review-changes/standards.md"],
    "review-architecture.md": ["review-changes/architecture.md"],
    "review-spec.md": ["review-changes/spec.md"],
    "suite.json": ["implement/SKILL.md", "architecture-tests/SKILL.md", "resolve-conflict/SKILL.md"],
    "loop.json": ["implement/SKILL.md", "to-spec/SKILL.md", "spec-drift/SKILL.md", "spec-names/SKILL.md",
                  "domain-modeling/SKILL.md", "spec-loop/SKILL.md", "what-next/SKILL.md", "review-changes/spec.md"],
    "surfaces.md": ["grill/SKILL.md", "to-spec/SKILL.md", "spec-drift/SKILL.md", "review-changes/spec.md"],
}


def test_every_page_that_reads_a_steering_file_names_it_by_its_path_from_the_repo_root():
    for seed, pages in STEERING_READERS.items():
        for page in pages:
            text = (SKILLS / page).read_text(encoding="utf-8")
            assert names_steering(text, WHERE[seed]), "{} names {}".format(page, seed)


def test_every_page_that_reads_the_rules_folder_names_it_by_its_path_from_the_repo_root():
    for page in RULES_FOLDER_READERS:
        assert names_steering((SKILLS / page).read_text(encoding="utf-8"), RULES_FOLDER), page


# A rule needs no page of its own, because the Standards axis reads every file in the rules folder.
def unread_steering(seeds, readers, folder_readers):
    return sorted(seed for seed in seeds if not readers.get(seed) and not (seed in RULES and folder_readers))


def test_every_steering_file_setup_seeds_has_a_page_that_reads_it():
    assert unread_steering(seed_steering.PLACES, STEERING_READERS, RULES_FOLDER_READERS) == []


def test_a_seed_no_page_reads_is_caught():
    assert unread_steering(["words.md", "new-baseline.md"], STEERING_READERS, RULES_FOLDER_READERS) == ["new-baseline.md"]


STEERING_PATH = re.compile(r"docs/skillworks/[\w./*<>-]*")

PATHS_SETUP_WRITES = set(seed_steering.PLACES.values()) | {
    "docs/skillworks/", RULES_FOLDER, RULES_FOLDER + "*.md", seed_steering.BASES + "/",
    seed_steering.BASES + "/" + agent_skills.BASE_NAME}


# A page that points at a file setup never writes sends a team's session to a file that is not there.
def unseeded_steering(text):
    return sorted({path.rstrip(".") for path in STEERING_PATH.findall(text)} - PATHS_SETUP_WRITES)


def test_no_plugin_page_names_a_steering_file_setup_does_not_seed():
    pages = sorted(SKILLS.rglob("*.md"))
    assert pages

    for page in pages:
        assert unseeded_steering(page.read_text(encoding="utf-8")) == [], page


def test_a_steering_path_setup_does_not_seed_is_caught():
    text = "Read `docs/skillworks/review-standards.md`, then `docs/skillworks/review-standard.md`. The rules sit in docs/skillworks/rules/."

    assert unseeded_steering(text) == ["docs/skillworks/review-standard.md"]


TEAM_CHECK_STEP = {
    "review-standards": "3. Every breach of a team check. Name the check and quote the hunk.",
    "review-architecture": "5. Does anything the change added breach a team check?",
    "review-spec": "Then walk the team checks in `steering-file docs/skillworks/review-spec.md`. A breach of one is a finding.",
}


@pytest.mark.parametrize("skill", list(AXIS_FILE_OF))
def test_each_axis_holds_the_change_to_each_team_check_on_the_paths_the_check_names(skill):
    text = axis_text(skill)

    assert "axis always reads its review file, {}".format(read_of(WHERE[REVIEW_FILE_OF[skill]])) in text
    assert "Apply each team check only to the paths it names. A check that names no paths covers the whole change." in text
    assert TEAM_CHECK_STEP[skill] in text


@pytest.mark.parametrize("skill", list(AXIS_FILE_OF))
def test_each_axis_skips_every_path_and_kind_of_finding_the_teams_do_not_report_list_names(skill):
    assert 'Skip every path and every kind of finding that "Do not report" names.' in axis_text(skill)


def test_the_architecture_axis_reads_its_review_file_before_it_skips_and_never_skips_past_a_team_check():
    skipping = axis_text("review-architecture").split("\n### When to skip\n", 1)[1].split("\n### ", 1)[0]

    assert "Read the review file before you skip" in skipping
    assert "Where a team check covers a path the change touches, do not skip." in skipping


def test_the_standards_axis_reads_every_file_in_the_rules_folder():
    assert "Read every file {} lists, each with `steering-file <path>`.".format(read_of(RULES_FOLDER)) in axis_text(
        "review-standards")


def test_the_standards_axis_finds_the_glossary_through_the_domain_doc_and_reports_a_word_it_rejects():
    text = axis_text("review-standards")

    assert "{} says where this repo keeps its glossaries.".format(read_of(WHERE["domain.md"])) in text
    assert "A word the glossary rejects is a finding on this axis." in text


# A repo with one context has a glossary and no map, so a page that takes the map as given finds no file.
def test_the_axes_read_the_context_map_only_where_the_repo_has_one():
    assert "Where the repo has a `CONTEXT-MAP.md`, the map says which glossary claims which file." in axis_text("review-standards")
    assert "Read the context map beside it, where the repo has one," in axis_text("review-architecture")


def test_code_review_is_renamed_review_changes_which_sends_a_check_on_correctness_to_claude_codes_own():
    front = skill_text("review-changes").split("---\n")[1]

    assert not (SKILLS / "code-review").exists()
    assert "name: review-changes\n" in front
    assert front.rstrip().endswith("Not for a check on correctness alone: that is Claude Code's own /code-review.")
    assert "disable-model-invocation" not in front


def test_review_changes_names_no_steering_file():
    text = skill_text("review-changes")

    for names in STEERING_NAMED.values():
        for steering in names:
            assert steering not in text, steering


def test_review_changes_sends_each_sub_agent_to_its_axis_file_in_report_only_mode():
    text = skill_text("review-changes")

    assert "follow it in report-only mode" in text
    for skill in AXIS_FILE_OF:
        assert "`{}`".format(AXIS_FILE_OF[skill]) in text, skill


@pytest.mark.parametrize("skill", list(AXIS_FILE_OF))
def test_each_axis_skill_follows_its_axis_file_in_loop_mode(skill):
    text = skill_text(skill)

    assert "`${{CLAUDE_PLUGIN_ROOT}}/skills/review-changes/{}`".format(AXIS_FILE_OF[skill]) in text
    assert "follow it in loop mode" in text


@pytest.mark.parametrize("skill", list(AXIS_FILE_OF))
def test_each_axis_skill_stays_hidden_and_holds_none_of_the_axis_steps(skill):
    assert hidden(skill)
    assert "## " not in skill_text(skill)


@pytest.mark.parametrize("skill", list(AXIS_FILE_OF))
def test_each_axis_file_is_a_plain_file_and_no_skill(skill):
    assert not axis_text(skill).startswith("---")


def test_the_spec_axis_judges_a_departure_and_a_broken_rule_is_asked_for_built_wrong():
    judging = " ".join(section(axis_text("review-spec"), "Judging a Departure").split())

    assert "`DEPARTS`" in judging
    assert "Do both parts really name the point?" in judging
    assert "Was the stricter one taken?" in judging
    assert "Where the rule did not hold, it is an **Asked for, built wrong** finding" in judging
    assert "Where the rule held, there is no finding" in judging


def test_spec_drift_judges_a_departure_and_where_the_rule_held_the_part_that_lost_contradicts():
    judging = " ".join(section(skill_text("spec-drift"), "Judging a Departure").split())

    assert "`DEPARTS`" in judging
    assert "Do both parts really name the point?" in judging
    assert "Was the stricter one taken?" in judging
    assert ("Where the rule held, the item for the part that lost gets **Contradicts**, and the "
            "Departure is its one sentence of reason") in judging
    assert "Where the rule did not hold, the item gets the Verdict the code earns" in judging


def test_the_drift_check_page_says_a_departure_where_the_rule_held_keeps_the_spec_open():
    page = " ".join(DRIFT_CHECK_PAGE.read_text(encoding="utf-8").split())

    assert "The drift check reads every `DEPARTS` line the spec's builds wrote" in page
    assert ("Where the rule held, the part that lost gets Contradicts, so the loop stops at the "
            "end with the spec open") in page


def test_review_changes_holds_no_brief_or_binding_rule_of_its_own():
    text = skill_text("review-changes")

    for words in ["The brief", "Cite or drop it", "Diff-introduced only", "The repo overrides", "Skip the axis"]:
        assert words not in text, words


def test_review_changes_finds_the_spec_from_the_ticket_trailer_then_the_argument_then_asks():
    finding = section(skill_text("review-changes"), "Find the spec")

    assert finding.index("`Ticket:` trailer") < finding.index("argument") < finding.index("ask the user")
    assert "Closes" not in skill_text("review-changes")


@pytest.mark.parametrize("skill", list(STEERING_NAMED))
def test_each_axis_reports_and_edits_nothing_for_review_changes_and_edits_the_worktree_for_the_loop(skill):
    modes = section(axis_text(skill), "Two modes")

    assert "**Report-only mode** is how `/skillworks:review-changes` runs this axis" in modes
    assert "--stat -M" in modes
    assert "edits nothing" in modes
    assert "**Loop mode** is how the loop's review step runs this axis, through `/skillworks:{}`".format(skill) in modes
    assert "This axis edits what it finds" in modes


def test_implement_reviews_with_review_changes_and_the_ticket_number():
    reviewing = section(skill_text("implement"), "Reviewing")

    assert "/skillworks:review-changes" in reviewing
    assert "ticket number" in reviewing


def test_what_next_names_review_changes_and_the_three_review_files():
    text = skill_text("what-next")

    assert "/skillworks:review-changes" in text
    for names in STEERING_NAMED.values():
        assert read_of(WHERE[names[-1]]) in text, names


def test_what_next_names_skillsmith_among_the_skills_for_any_time():
    any_time = section(skill_text("what-next"), "Skills for any time")

    assert "\n- **`/skillworks:skillsmith`** — " in any_time


# What loads skillsmith is Claude's own judgement, so no skill reaches for it on Claude's behalf.
def test_no_skill_calls_skillsmith_through_the_skill_tool():
    assert [call for call in skill_tool_calls() if call[1] == "skillsmith"] == []


def test_the_licence_notices_name_review_changes_among_the_skills_we_changed():
    notices = " ".join((ROOT / "THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8").split())

    assert "`implement`, `to-spec`, `to-tickets`, `review-changes`, `wayfinder`" in notices
    assert "code-review" not in notices


def test_the_licence_notices_name_skillsmith_among_the_skills_that_are_ours():
    notices = " ".join((ROOT / "THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8").split())
    ours = notices.split(" except ", 1)[1].split("which are ours", 1)[0]

    assert "`skillsmith`" in ours


def test_no_plugin_file_or_steering_doc_names_the_old_review_skill():
    pages = [path for folder in (PLUGIN, ROOT / "docs" / "usage", ROOT / "docs" / "skillworks")
             for path in folder.rglob("*") if path.is_file() and path.suffix in (".md", ".py", ".mjs", ".json")]
    assert pages

    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert "skillworks:code-review" not in text, page
        assert "`code-review`" not in text, page


def test_spec_loop_says_why_the_script_picks_the_ticket_and_links_no_research_note():
    text = (SKILLS / "spec-loop" / "SKILL.md").read_text(encoding="utf-8")

    assert "docs/research" not in text
    assert "A script reads the blocking edges and picks the same ticket every time." in text


def test_spec_loop_reads_a_clean_finish_off_the_end_line_and_judges_no_report():
    skill = (SKILLS / "spec-loop" / "SKILL.md").read_text(encoding="utf-8")

    line = skill.split("**A clean finish**", 1)[1].split("\n", 1)[0]
    assert "is the log's `END` line" in line
    assert "Do not judge the drift report yourself" in line
    assert "lists nothing Missing, Partial or Contradicts" not in skill


def test_spec_loop_names_each_unrequested_item_before_the_close_offer():
    skill = (SKILLS / "spec-loop" / "SKILL.md").read_text(encoding="utf-8")

    named = skill.index("Name each of those items to the user, one by one, before any close offer")
    assert skill.index("`NOTE  Unrequested:`") < named < skill.index("make one offer")


def test_spec_loop_says_no_pull_request_is_marked_ready_or_closes_the_spec():
    skill = (SKILLS / "spec-loop" / "SKILL.md").read_text(encoding="utf-8")

    assert [said for said in ("ready for review", "`READY`", "the pull request closes the spec")
            if said in skill] == []


def test_spec_loop_in_pr_mode_tells_the_user_to_open_the_pull_request_with_either_tracker():
    skill = (SKILLS / "spec-loop" / "SKILL.md").read_text(encoding="utf-8")

    told = [line for line in skill.splitlines()
            if line.startswith(("- **With the files Tracker**", "- **With the GitHub Tracker and `pr`**"))]
    assert [("its `CLOSE` line" in line, "open the pull request from that branch" in line)
            for line in told] == [(True, True), (True, True)]


def test_spec_loop_names_each_departure_first_then_each_choice_and_hand_check_before_the_close_offer_and_at_a_stop():
    skill = (SKILLS / "spec-loop" / "SKILL.md").read_text(encoding="utf-8")

    named = skill.index("Name each Departure first, then each Choice and each Hand check, from the "
                        "list at the end of the log to the user, one by one, before any close "
                        "offer and at an early stop as well.")
    assert skill.index("### 3. Report") < named < skill.index("make one offer")


def test_the_stops_page_says_an_unexpected_error_ends_the_log_with_the_departures_first():
    page = STOPS_PAGE.read_text(encoding="utf-8")

    unexpected = page.split("**An error the driver did not expect.**", 1)[1].split("```", 1)[0]
    assert "then the Departures, the Choices and the Hand checks" in " ".join(unexpected.split())


LOOP_OVERVIEW = ROOT / "docs" / "usage" / "the-loop.md"

DRIFT_CHECK_PAGE = ROOT / "docs" / "usage" / "the-loop" / "drift-check.md"

NAME_CHECK_PAGE = ROOT / "docs" / "usage" / "the-loop" / "name-check.md"

FULL_RUN_PAGE = ROOT / "docs" / "usage" / "the-loop" / "full-run.md"

STOPS_PAGE = ROOT / "docs" / "usage" / "the-loop" / "stops.md"

READING_A_RUN_PAGE = ROOT / "docs" / "usage" / "the-loop" / "reading-a-run.md"

STAGE_MAP_PAGE = ROOT / "docs" / "usage" / "the-loop" / "stage-map.md"


def full_run_chart():
    finish = FULL_RUN_PAGE.read_text(encoding="utf-8").split("\n## A clean finish\n", 1)[1]
    return finish.split("```mermaid\n", 1)[1].split("```", 1)[0]


def test_the_full_run_page_says_the_driver_decides_a_clean_finish_after_the_full_run():
    page = " ".join(FULL_RUN_PAGE.read_text(encoding="utf-8").split())

    assert "The script decides a clean finish, and nothing else does." in page
    assert ("every Verdict Done or In step, no rename owed in [the Name "
            "report](name-check.md) or every rename Done in [the Name "
            "re-check](name-check.md#the-name-re-check), and [the full "
            "run](#the-full-run) green") in page
    assert ("It runs once, at the end, after the drift check, its count and [the Name "
            "check](name-check.md).") in page


def test_the_drift_check_page_describes_the_gap_ticket_and_the_one_round():
    text = DRIFT_CHECK_PAGE.read_text(encoding="utf-8")
    page = " ".join(text.split())

    assert "\n## The Gap round\n" in text
    assert "There is one round." in page
    assert ('"The drift check did not judge this exactly once. Check it, and build it if it is not '
            'there."') in page
    assert "on the Gap items alone" in page
    assert "through [the same steps](steps.md) as every other ticket" in page


def test_the_stage_map_page_shows_the_gap_ticket():
    assert "| The Gap ticket |" in STAGE_MAP_PAGE.read_text(encoding="utf-8")


def test_the_reading_a_run_page_shows_the_gap_ticket_in_the_log():
    assert "FILED #210 under spec #200" in READING_A_RUN_PAGE.read_text(encoding="utf-8")


def test_the_stops_page_shows_the_stop_for_a_gap_left():
    assert ("STOP  the drift check still finds 2 Gaps on spec #200 after the Gap ticket was built"
            in STOPS_PAGE.read_text(encoding="utf-8"))


def test_the_drift_check_page_holds_the_drift_check_its_verdicts_the_count_and_the_gap_round():
    text = DRIFT_CHECK_PAGE.read_text(encoding="utf-8")

    assert text.startswith("# The drift check\n")
    for heading in ["\n## Verdicts\n", "\n## The count\n", "\n## The Gap round\n"]:
        assert heading in text, heading
    overview = LOOP_OVERVIEW.read_text(encoding="utf-8")
    assert "## The drift check" not in overview
    assert "### The count" not in overview


def test_the_full_run_page_holds_the_full_run_and_a_clean_finish():
    text = FULL_RUN_PAGE.read_text(encoding="utf-8")

    assert text.startswith("# The full run\n")
    assert "\n## A clean finish\n" in text
    overview = LOOP_OVERVIEW.read_text(encoding="utf-8")
    assert "## The full run" not in overview
    assert "### A clean finish" not in overview


def test_the_full_run_page_shows_the_end_of_a_run_in_its_chart_beside_a_clean_finish():
    chart = full_run_chart()

    for node in ['drift["Drift check', 'clean["A clean finish', 'hint["A hint: open the pull request']:
        assert node in chart, node


def test_the_name_check_page_describes_the_name_check_and_its_report():
    text = NAME_CHECK_PAGE.read_text(encoding="utf-8")
    page = " ".join(text.split())

    assert text.startswith("# The Name check\n")
    assert "\n## The Name report\n" in text
    assert "/skillworks:spec-names <spec> <base>" in page
    assert "the commits the spec's tickets Landed after the base commit, through `spec-commits`" in page
    assert "A name is a finding only while it still stands on the Target branch." in page
    assert "A rename is never \"Optional\"." in page
    assert "`.spec-loop/<spec>/names.md`, beside `drift.md`" in page
    assert "With no rename there is no rename ticket and no Name re-check" in page
    assert "## The Name check" not in LOOP_OVERVIEW.read_text(encoding="utf-8")


def test_the_full_run_page_shows_the_name_check_in_its_chart():
    assert 'names["Name check' in full_run_chart()


def test_the_stage_map_page_shows_the_name_check():
    assert "| The Name check |" in STAGE_MAP_PAGE.read_text(encoding="utf-8")


def test_the_name_check_page_describes_the_rename_ticket_and_the_name_re_check():
    text = NAME_CHECK_PAGE.read_text(encoding="utf-8")
    page = " ".join(text.split())

    assert "\n## The rename ticket\n" in text
    assert "\n## The Name re-check\n" in text
    assert "The build never edits a glossary." in page
    assert "/skillworks:spec-names <spec> <base> <rename ticket>" in page
    assert "`.spec-loop/<spec>/names-renames.md`" in page
    assert "the way it files [the Gap ticket](drift-check.md#the-gap-round)" in page
    assert "as [When a step fails](stops.md) shows" in page


def test_the_full_run_page_shows_the_rename_ticket_in_its_chart():
    assert 'renames["The rename ticket' in full_run_chart()


def test_the_stage_map_page_shows_the_rename_ticket():
    assert "| The rename ticket |" in STAGE_MAP_PAGE.read_text(encoding="utf-8")


def test_the_stops_page_shows_the_stop_for_a_rename_not_made():
    assert ("STOP  the Name re-check finds 1 rename not made on spec #200"
            in STOPS_PAGE.read_text(encoding="utf-8"))


def test_the_reading_a_run_page_shows_the_rename_ticket_in_the_log():
    text = READING_A_RUN_PAGE.read_text(encoding="utf-8")

    assert "FILED #211 under spec #200 makes 2 renames" in text
    assert "NOTE  Gap and Hole has no glossary word" in text


def test_the_steering_page_says_the_name_check_reads_the_glossary():
    rows = [line for line in (ROOT / "docs" / "usage" / "steering.md").read_text(
        encoding="utf-8").split("\n") if line.startswith(("| `surfaces.md`", "| `CONTEXT.md`"))]

    assert len(rows) == 2
    for row in rows:
        assert "The Name check" in row
        assert "glossary" in row


def setup_section(heading):
    text = (SETUP / "SKILL.md").read_text(encoding="utf-8")
    return re.split(r"\n### \d", text.split(heading, 1)[1], maxsplit=1)[0]


def test_setup_points_claude_md_at_the_rules_before_the_preflight_checks_their_imports():
    text = (SETUP / "SKILL.md").read_text(encoding="utf-8")
    steps = re.findall(r"^### \d+\. (.+)$", text, re.MULTILINE)

    assert steps.index("Point CLAUDE.md at the docs") < steps.index("Preflight and labels")


def test_setup_leaves_the_claude_md_block_in_place_when_the_preflight_fails():
    step = setup_section("### 5. Preflight and labels")

    assert "If it fails, stop and report." in step
    assert "safe to leave" in step


def test_the_settings_step_names_every_top_level_key_of_the_settings_file():
    shipped = json.loads((SETUP / "settings.json").read_text(encoding="utf-8"))
    step = setup_section("### 6. Write the settings")

    assert {"promptCacheTtl", "subagentPromptCacheTtl"} <= shipped.keys()
    for key in shipped:
        assert "`{}".format(key) in step, key


def test_the_settings_step_adds_a_missing_cache_key_and_keeps_one_the_team_set():
    step = setup_section("### 6. Write the settings")
    lines = [line for line in step.split("\n") if "`promptCacheTtl`" in line]

    assert len(lines) == 1
    assert "`subagentPromptCacheTtl`" in lines[0]
    assert "where missing" in lines[0]
    assert "keep" in lines[0]


def test_the_outputs_name_both_prompt_cache_keys():
    outputs = (SETUP / "SKILL.md").read_text(encoding="utf-8").split("## Process", 1)[0]
    rows = [line for line in outputs.split("\n") if '`"promptCacheTtl"' in line]

    assert len(rows) == 1
    assert '`"subagentPromptCacheTtl"' in rows[0]


def test_the_outputs_say_the_attribution_block_is_rewritten_from_the_answer_on_every_run():
    outputs = (SETUP / "SKILL.md").read_text(encoding="utf-8").split("## Process", 1)[0]
    rows = [line for line in outputs.split("\n") if line.startswith("| An `attribution` block")]

    assert len(rows) == 1
    assert "when the team hides" not in rows[0]
    assert "`co-authored-by`" in rows[0]
    assert "every time" in rows[0]


def settings_row(page):
    rows = [line for line in (ROOT / "docs" / "usage" / page).read_text(encoding="utf-8").split("\n")
            if line.startswith("| `.claude/settings.json` |")]
    assert len(rows) == 1
    return rows[0]


def test_the_setup_page_names_the_cache_keys_and_what_a_second_run_does_with_them():
    row = settings_row("setup.md")

    assert "`promptCacheTtl`" in row
    assert "`subagentPromptCacheTtl`" in row
    assert "adds a cache key that is missing and keeps one your team set" in row


def test_auto_memory_is_a_lever_off_by_default_and_not_fixed():
    page = (ROOT / "docs" / "usage" / "steering.md").read_text(encoding="utf-8")
    row = settings_row("steering.md")
    fixed = page.split("## What is fixed", 1)[1]

    assert "Auto-memory, off by default" in row.split(" | ")[-1]
    assert "memory" not in fixed.lower()


def test_the_steering_page_names_the_cache_keys():
    row = settings_row("steering.md")

    assert "`promptCacheTtl`" in row
    assert "`subagentPromptCacheTtl`" in row


POINTER_STEP = "### 4. Point CLAUDE.md at the docs"


def test_setup_builds_the_claude_md_block_with_seed_agent_skills_after_it_settles_the_adr_folder():
    step = " ".join(setup_section(POINTER_STEP).split())

    assert step.index("Write the answer into `adr-folder`") < step.index("seed-agent-skills --tracker")
    assert "--adr-folder <adr-folder> --contexts <single|multi>" in step


def test_the_setup_skill_holds_none_of_the_claude_md_blocks_text():
    text = (SETUP / "SKILL.md").read_text(encoding="utf-8")

    for words in ("### Issue tracker", "### Domain docs", "Single-context:", "Multi-context:", "@docs/skillworks/rules/"):
        assert words not in text, words


def test_setup_suggests_the_adr_folder_the_domain_docs_name_then_one_it_finds_then_docs_adr():
    step = " ".join(setup_section(POINTER_STEP).split())
    named = step.index("1. The folder `adr-folder` names in `docs/skillworks/domain.md`")
    found = step.index("2. Else a folder that holds numbered Markdown files and has `adr` or `decision` in its path.")
    default = step.index("3. Else `docs/adr`.")

    assert named < found < default
    assert "List every such folder you find, and suggest the one with the most files." in step


def test_setup_reads_an_earlier_adr_folder_before_the_seed_writes_its_default():
    step = " ".join(setup_section("### 1. Seed the Steering").split())

    assert "Before you run it, read `adr-folder` from the YAML block at the end of `docs/skillworks/domain.md`" in step
    assert "the seed writes `docs/adr` into a file that names none" in step


def test_setup_writes_the_adr_folder_answer_into_the_domain_docs_yaml_block():
    step = " ".join(setup_section(POINTER_STEP).split())

    assert ("Write the answer into `adr-folder` in the YAML block at the end of `docs/skillworks/domain.md`, "
            "and change no other line.") in step


def test_setup_puts_each_question_on_the_block_to_the_developer_with_a_blend_and_writes_nothing_itself():
    step = " ".join(setup_section(POINTER_STEP).split())

    assert "so you write none of it yourself" in step
    assert "show the `yours` side, the `seed` side, and a blend you write to fit the repo" in step
    assert "--blend CLAUDE.md:2=" in step
    assert "--settled CLAUDE.md" in step
    assert "Ask every question before you change anything." in step


def test_setup_says_a_second_run_merges_the_claude_md_block():
    step = setup_section("### 5. Preflight and labels")

    assert "a second run of setup merges it" in step
    assert "in place" not in step


def test_the_setup_page_lists_the_adr_folder_among_the_questions_setup_asks():
    questions = SETUP_PAGE.read_text(encoding="utf-8").split("## The questions setup asks", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in questions.splitlines() if line.startswith("| Where do your ADRs go? |")]

    assert len(rows) == 1
    for words in ("`adr-folder`", "`adr` or `decision`", "the most files", "`docs/adr`", "On a second run"):
        assert words in rows[0], words


def test_the_report_names_the_folder_each_steering_file_lives_in():
    report = setup_section("### 7. Report")

    assert "`docs/skillworks/rules/`" in report
    assert "`docs/skillworks/`" in report
    for seed in WHERE:
        assert "`{}`".format(seed) in report, seed


def test_the_report_names_architecture_tests_as_the_next_step_and_what_it_fills():
    report = setup_section("### 7. Report")
    paragraphs = [paragraph for paragraph in report.split("\n\n") if "`/skillworks:architecture-tests`" in paragraph]

    assert len(paragraphs) == 1
    assert "next step" in paragraphs[0]
    for filled in ("`{}`".format(WHERE["suite.json"]), "`{}`".format(WHERE["placement-checks.md"]), "allowlist"):
        assert filled in paragraphs[0], filled


HISTORY_STEP = "a repo with a history and no glossary"


def test_the_report_names_the_backfill_before_architecture_tests_for_a_repo_with_a_history():
    report = setup_section("### 7. Report")
    paragraph = [paragraph for paragraph in report.split("\n\n") if "`/skillworks:architecture-tests`" in paragraph][0]

    assert "`next step:`" in paragraph
    assert HISTORY_STEP in paragraph
    assert paragraph.index("`/skillworks:context-backfill`") < paragraph.index("`/skillworks:architecture-tests`")


BACKFILL_SENTENCE = ("A repo built before it had these files fills them once with `/skillworks:context-backfill`, "
                     "and setup names it as the next step.")


def test_the_domain_docs_seed_and_this_repos_copy_say_how_a_repo_with_a_history_fills_them():
    copy = (ROOT / "docs" / "skillworks" / "domain.md").read_text(encoding="utf-8")

    assert BACKFILL_SENTENCE in seeded("domain.md")
    assert BACKFILL_SENTENCE in copy


def test_the_setup_page_names_the_backfill_beside_turning_the_rules_into_tests():
    section = usage_section("## Turn the rules into tests")

    assert "`/skillworks:context-backfill`" in section
    assert HISTORY_STEP in section
    assert "](context-backfill.md)" in section


def test_what_next_names_the_backfill_in_the_words_setup_uses():
    any_time = section(skill_text("what-next"), "Skills for any time")
    entry = [line for line in any_time.splitlines() if line.startswith("- **`/skillworks:context-backfill`** — ")]

    assert len(entry) == 1
    assert HISTORY_STEP in entry[0]


# Each holds only for this repository, so a skill that says one tells a team about a repo it is not in.
SKILL_HABITS = ["slice rules", "slice whose job it serves", "no branches and no pull requests", "under checks"]


def test_no_plugin_skill_says_a_habit_of_this_repo():
    pages = sorted(path for path in SKILLS.rglob("*.md") if (SETUP / "seeds") not in path.parents)
    assert pages

    for page in pages:
        text = page.read_text(encoding="utf-8").lower()
        for habit in SKILL_HABITS:
            assert habit not in text, "{} says {}".format(page, habit)


# The hook adds the line as the team chose and refuses one a model typed, so a skill or a seed that shows it invites a refusal.
CO_AUTHOR = re.compile(r"(?<!-)co[-_ ]?authored[-_ ]?by\s*:|noreply@anthropic\.com", re.IGNORECASE)


def test_no_plugin_skill_or_seed_names_a_co_author_line():
    pages = sorted(path for path in SKILLS.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    assert pages

    named = [page.relative_to(SKILLS).as_posix() for page in pages
             if CO_AUTHOR.search(page.read_text(encoding="utf-8", errors="replace"))]

    assert named == []


@pytest.mark.parametrize("line", ["Co-Authored-By: Claude", "co-authored-by:", "noreply@anthropic.com",
                                  'git commit -m "Fix\\n\\nCo-Authored-By: A Person"'])
def test_a_co_author_line_is_caught(line):
    assert CO_AUTHOR.search(line)


@pytest.mark.parametrize("line", ["`co-authored-by` says `show`", "set-co-authored-by hide", "the credit line",
                                  '"Bash(set-co-authored-by:*)",'])
def test_the_key_and_the_command_are_free(line):
    assert not CO_AUTHOR.search(line)


def test_no_seed_promises_a_check_the_team_has_not_added():
    for name in sorted(WHERE):
        assert "the check reads" not in seeded(name).lower(), name


STEERING_PAGE = ROOT / "docs" / "usage" / "steering.md"


def unnamed_steering(page, folder):
    return sorted(path.relative_to(folder).as_posix() for path in folder.rglob("*")
                  if path.is_file() and "`{}`".format(path.name) not in page)


# The page is for a team's repo, so it names what setup writes there and not this repo's own files.
def test_the_steering_page_names_every_file_setup_seeds():
    page = STEERING_PAGE.read_text(encoding="utf-8")

    assert unnamed_steering(page, seed_steering.SEEDS) == []


def test_a_steering_file_the_page_does_not_name_is_caught(tmp_path):
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "comments.md").write_text("", encoding="utf-8")
    (tmp_path / "new-baseline.md").write_text("", encoding="utf-8")

    assert unnamed_steering("`comments.md`", tmp_path) == ["new-baseline.md"]


def test_the_steering_page_says_which_files_always_load():
    page = STEERING_PAGE.read_text(encoding="utf-8")
    loads = page.split("## What always loads", 1)[1].split("\n## ", 1)[0]

    for rule in RULES:
        assert "`{}`".format(rule) in loads, rule


def test_the_steering_page_lists_the_machinery_no_team_edits():
    page = STEERING_PAGE.read_text(encoding="utf-8")
    fixed = page.split("## What is fixed", 1)[1]

    for machinery in ("`tdd`", "`codebase-design`", "`unslop`", "`skillsmith`", "output style"):
        assert machinery in fixed, machinery


def test_the_usage_front_page_lists_the_steering_page():
    assert "(steering.md)" in (ROOT / "docs" / "usage" / "README.md").read_text(encoding="utf-8")


USAGE_FRONT_PAGE = "https://github.com/MalcolmMcNeely/skillworks/blob/main/docs/usage/README.md"


def test_the_report_ends_with_a_link_to_the_usage_front_page():
    last = setup_section("### 7. Report").strip().splitlines()[-1]

    assert "]({})".format(USAGE_FRONT_PAGE) in last
    assert (ROOT / USAGE_FRONT_PAGE.split("/blob/main/", 1)[1]).is_file()


SETUP_PAGE = ROOT / "docs" / "usage" / "setup.md"


OUTCOMES = ["`wrote`", "`updated`", "`kept ..., which you edited`", "`kept ..., the same as the seed`",
            "`kept ..., the same as the seed, and brought its base copy up to the seed`",
            "`kept ..., the same as the seed, and wrote its base copy`", "`merged`", "`asks`",
            "`kept ..., which differs from the seed`", "`kept ..., as you settled it`"]


def test_the_seed_step_names_each_outcome_the_questions_and_the_review_before_commit():
    step = setup_section("### 1. Seed the Steering")

    for outcome in OUTCOMES:
        assert "| {} |".format(outcome) in step, outcome
    assert "--keep " in step
    assert "--settled " in step
    assert "before you change anything" in step
    assert "before they commit" in step


def test_the_seed_step_offers_a_blend_beside_yours_and_the_seed_for_each_overlap():
    step = setup_section("### 1. Seed the Steering")

    assert "show the `yours` side, the `seed` side, and a blend you write to fit the repo" in step
    assert "seed-steering --blend docs/skillworks/domain.md:1=" in step
    assert "You write nothing into the Steering file yourself" in step


def test_the_setup_page_offers_a_blend_for_an_overlap_in_the_questions_and_the_merge():
    page = SETUP_PAGE.read_text(encoding="utf-8")
    questions, again = page.split("## Run setup again", 1)

    assert "| Which do you keep for this overlap: yours, the Seed's, or a blend? |" in questions
    assert "a blend" in again.split("### Each Steering file", 1)[1].split("\n### ", 1)[0]


def test_the_seed_step_and_the_setup_page_say_a_file_with_no_base_copy_holds_every_change():
    step = setup_section("### 1. Seed the Steering")
    again = SETUP_PAGE.read_text(encoding="utf-8").split("## Run setup again", 1)[1]

    assert "When a line says `asks` or `kept ..., which differs from the seed`, the script has written nothing" in step
    assert "A file with no base copy is a question too" in again


def test_the_setup_page_explains_each_outcome_of_a_second_run():
    again = SETUP_PAGE.read_text(encoding="utf-8").split("## Run setup again", 1)[1]

    for outcome in OUTCOMES:
        assert "| {} |".format(outcome) in again, outcome
    assert "`docs/skillworks/.seeds/`" in again
    assert "before you commit" in again


def test_the_seed_step_and_the_setup_page_say_a_deleted_file_is_written_again():
    step = setup_section("### 1. Seed the Steering")
    again = SETUP_PAGE.read_text(encoding="utf-8").split("## Run setup again", 1)[1]

    for text in (step, again):
        assert "`left out`" not in text
    assert "The seed is new, or the file is missing, even one the team deleted." in step
    assert "Setup writes a deleted Steering file again." in again


DIFF_LABELS = ["`old-seed/`", "`new-seed/`", "`yours/`", "`merged/`", "`seed/`"]


def test_the_seed_step_and_the_setup_page_name_each_label_on_a_shown_diff():
    step = setup_section("### 1. Seed the Steering")
    again = SETUP_PAGE.read_text(encoding="utf-8").split("## Run setup again", 1)[1]

    for label in DIFF_LABELS:
        assert label in step, label
        assert label in again, label


def test_the_usage_front_page_lists_the_setup_page():
    assert "(setup.md)" in (ROOT / "docs" / "usage" / "README.md").read_text(encoding="utf-8")


def test_the_setup_page_lists_the_target_branch_among_the_questions_setup_asks():
    questions = SETUP_PAGE.read_text(encoding="utf-8").split("## The questions setup asks", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in questions.splitlines() if line.startswith("| Which is your Target branch? |")]

    assert len(rows) == 1
    assert "`pr`" in rows[0]
    assert "default branch" in rows[0]


def test_the_setup_page_never_requires_main():
    page = SETUP_PAGE.read_text(encoding="utf-8")

    assert "`main`" not in page


def test_the_steering_page_describes_the_loop_file():
    page = (ROOT / "docs" / "usage" / "steering.md").read_text(encoding="utf-8")
    rows = [line for line in page.splitlines() if line.startswith("| `loop.json` |")]

    assert len(rows) == 1
    assert "`target-branch`" in rows[0]
    assert "`pr`" in rows[0]


def test_the_steering_page_names_the_credit_answer_in_the_loop_file():
    page = (ROOT / "docs" / "usage" / "steering.md").read_text(encoding="utf-8")
    row = [line for line in page.splitlines() if line.startswith("| `loop.json` |")][0]

    assert "`co-authored-by`: `show` or `hide`. The Seed sets it to `hide`, and setup asks." in row


def test_the_setup_page_names_every_file_setup_writes():
    page = SETUP_PAGE.read_text(encoding="utf-8")

    for place in list(WHERE.values()) + WORKING_FOLDERS + [".gitignore", "CLAUDE.md", ".claude/settings.json"]:
        assert "`{}`".format(place) in page, place


def test_setup_asks_whether_commits_credit_claude_and_suggests_hide():
    step = setup_section("### 6. Write the settings")

    assert "should commits and pull requests credit Claude?" in step
    assert "On a first run, suggest `hide`" in step
    assert "If `co-authored-by` in `docs/skillworks/loop.json` already names an answer" in step
    assert "`set-co-authored-by hide`" in step
    assert "`set-co-authored-by show`" in step
    assert "rewrites the `attribution` block of `.claude/settings.json` from the answer every time it runs" in step
    assert "read the memory line and the credit answer out with it" in step
    assert "Never write `\"attribution\": false`" in step


def test_no_skill_seed_or_allowlist_names_the_old_credit_command():
    pages = sorted(path for path in SKILLS.rglob("*") if path.is_file() and "__pycache__" not in path.parts)

    named = [page.relative_to(SKILLS).as_posix() for page in pages
             if "set-attribution" in page.read_text(encoding="utf-8", errors="replace")]

    assert SETUP / "settings.json" in pages and named == []


def test_setup_writes_no_attribution_false_and_no_local_settings():
    text = (SETUP / "SKILL.md").read_text(encoding="utf-8")
    settings = json.loads((SETUP / "settings.json").read_text(encoding="utf-8"))

    assert "attribution" not in settings
    assert "Leave `.claude/settings.local.json` alone." in text
    for line in text.splitlines():
        if "\"attribution\": false" in line:
            assert "Never write" in line, line


def test_the_setup_page_explains_the_credit_question_and_both_answers():
    page = SETUP_PAGE.read_text(encoding="utf-8")
    credit = page.split("## Credit for Claude", 1)[1].split("\n## ", 1)[0]

    assert "`set-co-authored-by` writes it to `co-authored-by` in `docs/skillworks/loop.json`" in credit
    assert "**Claude Code's commit credit is always off.**" in credit
    assert "| `show` | The Plugin's hook adds the credit line to each commit Claude makes." in credit
    assert "Pull requests follow the same answer through Claude Code" in credit
    assert "The hook refuses a Claude credit line the model typed" in credit
    assert "never touches a line that credits a person" in credit
    assert "A repo with no answer keeps Claude Code's own credit." in credit
    assert "Setup rewrites the block from your answer each time it runs." in credit
    assert "Setup never writes `\"attribution\": false`." in credit
    assert "Setup never writes `.claude/settings.local.json`." in credit


def test_the_setup_page_says_setup_writes_the_credit_answer_and_rewrites_the_block_from_it():
    page = SETUP_PAGE.read_text(encoding="utf-8")
    question = [line for line in page.splitlines() if line.startswith("| Should commits and pull requests credit Claude? |")]
    files = [line for line in page.splitlines() if line.startswith("| `docs/skillworks/loop.json` |")]
    second_run = page.split("### The other outputs", 1)[1]

    assert len(question) == 1 and "`co-authored-by`" in question[0] and "suggests that one" in question[0]
    assert "`co-authored-by` holds your answer on the credit for Claude" in files[0]
    assert "rewrites the `attribution` block from `co-authored-by` in `docs/skillworks/loop.json`" in second_run


ARCHITECTURE_TESTS = SKILLS / "architecture-tests"


def architecture_reference():
    return (ARCHITECTURE_TESTS / "REFERENCE.md").read_text(encoding="utf-8")


def setting_keys(text):
    settings = re.findall(r"```yaml\n(.*?)```", text, re.DOTALL)[0]
    return re.findall(r"^\"?([a-z][a-z-]*)\"?:", settings, re.MULTILINE)


def seed_rules(text):
    numbered = re.findall(r"^\d+\. \*\*(.+?)\*\*", text, re.MULTILINE)
    return numbered + ["`{}`".format(key) for key in setting_keys(text)]


def reference_rows(reference, seed):
    section = reference.split("\n## `{}`\n".format(seed), 1)
    if len(section) < 2:
        return []
    table = [line for line in section[1].split("\n## ", 1)[0].splitlines() if line.startswith("|")]
    return [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in table[2:]]


def unmapped(seed, text, reference):
    firsts = [row[0] for row in reference_rows(reference, seed)]
    return [rule for rule in seed_rules(text) if not any(rule in first for first in firsts)]


# A rule with no setting has nothing a check could read, so architecture-tests has nothing to map for it.
CHECKED_RULES = [rule for rule in RULES if setting_keys(seeded(rule))]


def test_every_rule_seed_but_testing_names_a_setting_a_check_reads():
    assert CHECKED_RULES == ["comments.md", "determinism.md", "file-placement.md", "words.md"]


def test_the_architecture_tests_reference_maps_every_rule_in_the_seeds():
    reference = architecture_reference()

    for rule in CHECKED_RULES:
        assert seed_rules(seeded(rule)), rule
        assert unmapped(rule, seeded(rule), reference) == [], rule


def test_a_rule_added_to_a_seed_without_a_line_in_the_reference_is_caught():
    reference = architecture_reference()
    added = seeded("file-placement.md").replace(
        "8. **A new job", "9. **A Slice holds no cycle.** Nothing loops back.\n8. **A new job").replace(
        "test-roots: {}\n", "test-roots: {}\nmax-depth: 4\n")

    assert unmapped("file-placement.md", added, reference) == ["A Slice holds no cycle.", "`max-depth`"]


def test_every_line_of_the_reference_names_a_tool_or_a_starter_test():
    reference = architecture_reference()

    for rule in CHECKED_RULES:
        rows = reference_rows(reference, rule)
        assert rows, rule
        for row in rows:
            assert len(row) == 5, row
            assert any(cell not in ("", "—") for cell in row[1:]), row


def test_the_architecture_tests_skill_can_be_invoked_by_the_model_and_states_the_method():
    text = skill_text("architecture-tests")

    assert "name: architecture-tests\n" in text
    assert "disable-model-invocation" not in text
    assert "(REFERENCE.md)" in text
    assert "/skillworks:tdd" in text
    for place in [WHERE["suite.json"], WHERE["placement-checks.md"], ".claude/settings.json"]:
        assert "`{}`".format(place) in text, place
    assert read_of("docs/skillworks/rules/") in text
    assert "`ignores`" in text
    assert "`when`" not in text
    assert "never quietly weakened" in text


def allowlist_fallback_gaps(text):
    step = text.split("3. **The allowlist.**", 1)[1].split("\n## ", 1)[0]
    report = text.split("\n## Report\n", 1)[1]
    wanted = {
        "the write goes through the Plugin's command": "`allow-commands`" in step,
        "a turned-down write does not stop the skill": "**If the write is turned down.**" in step,
        "the developer is shown the file and the exact entries": "Show the developer the file, `.claude/settings.json`, and the exact entries" in step,
        "the developer is asked to add them": "Ask the developer to add them." in step,
        "the file is read back": "Then read the file back" in step,
        "the step is never done with an entry missing": "Never report it done while an entry is missing." in step,
        "the report names each missing entry": "Name each allowlist entry still missing" in report,
    }
    return [need for need, met in wanted.items() if not met]


def test_architecture_tests_falls_back_to_the_developer_when_the_allowlist_write_is_turned_down():
    assert allowlist_fallback_gaps(skill_text("architecture-tests")) == []


def test_architecture_tests_writes_a_baseline_with_the_quickest_command_that_shows_the_code_compiles():
    step = skill_text("architecture-tests").split("1. **The Suite.**", 1)[1].split("\n2. ", 1)[0]

    assert "`baseline`" in step
    assert "the quickest command that shows the code compiles" in step


def test_setup_s_description_of_the_suite_file_names_the_baseline_key_and_what_it_is_for():
    report = setup_section("### 7. Report")
    entry = [line for line in report.splitlines() if line.startswith("- `{}`:".format(WHERE["suite.json"]))][0]

    assert "`baseline`" in entry
    assert "checks the Target branch with before the Cut" in entry


def test_a_skill_that_drops_the_allowlist_fallback_is_caught():
    text = skill_text("architecture-tests")
    step = text.split("   **If the write is turned down.**", 1)[1].split("\n\n", 1)[0]

    assert allowlist_fallback_gaps(text.replace(step, "")) != []


ENFORCED = "enforced only once a check exists"


def enforcement_paragraph(text):
    paragraphs = [paragraph for paragraph in text.split("\n\n") if ENFORCED in paragraph]
    assert len(paragraphs) == 1, "expected one paragraph saying what is {}".format(ENFORCED)
    return paragraphs[0]


def unnamed(keys, text):
    return [key for key in keys if "`{}`".format(key) not in text]


def test_each_rule_seed_names_every_setting_enforced_only_once_a_check_exists():
    for rule in RULES:
        text = seeded(rule)
        paragraph = enforcement_paragraph(text)

        assert unnamed(setting_keys(text), paragraph) == [], rule
        if rule in CHECKED_RULES:
            assert "`/skillworks:architecture-tests`" in paragraph, rule


def test_the_testing_seed_holds_no_setting_and_says_the_standards_review_is_its_only_judge():
    paragraph = enforcement_paragraph(seeded("testing.md"))

    assert settings_block(SETUP / "seeds" / "testing.md") == []
    assert "No check reads this rule" in paragraph
    assert "`standards` review" in paragraph


def test_the_determinism_rule_leaves_its_fakes_to_the_testing_rule():
    for text in (seeded("determinism.md"), (ROOT / WHERE["determinism.md"]).read_text(encoding="utf-8")):
        order = text.split("\n## Order of events\n", 1)[1].split("\n## ", 1)[0]

        assert "Fakes" not in text
        assert "`{}`".format(WHERE["testing.md"]) in order
    assert "\n## Fakes\n" in seeded("testing.md")


def test_this_repo_imports_its_testing_rule_with_its_own_fake_library():
    rule = ROOT / WHERE["testing.md"]

    assert "@{}".format(WHERE["testing.md"]) in (ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
    assert "`NSubstitute`" in rule.read_text(encoding="utf-8")
    assert settings_block(rule) == []


def test_a_setting_added_to_a_seed_without_being_named_as_enforced_is_caught():
    added = seeded("words.md").replace("skip-folders: []\n", "skip-folders: []\nmax-length: 4\n")

    assert unnamed(setting_keys(added), enforcement_paragraph(added)) == ["max-length"]


def enforced_row(section, rule):
    rows = [line for line in section.splitlines() if line.startswith("| `{}` |".format(rule))]
    assert len(rows) == 1, rule
    return rows[0]


def test_the_stage_map_names_every_setting_enforced_only_once_a_check_exists():
    section = STAGE_MAP_PAGE.read_text(encoding="utf-8")

    assert ENFORCED in section
    assert "`/skillworks:architecture-tests`" in section
    for rule in RULES:
        assert unnamed(setting_keys(seeded(rule)), enforced_row(section, rule)) == [], rule
    assert "`standards` review" in enforced_row(section, "testing.md")


def usage_section(heading):
    page = SETUP_PAGE.read_text(encoding="utf-8")
    assert "\n{}\n".format(heading) in page, heading
    return page.split("\n{}\n".format(heading), 1)[1].split("\n## ", 1)[0]


def test_the_usage_docs_explain_what_architecture_tests_reads_chooses_and_writes():
    section = usage_section("## Turn the rules into tests")

    assert "`/skillworks:architecture-tests`" in section
    assert "`docs/skillworks/rules/`" in section
    for way in ("common tool", "starter test"):
        assert way in section, way
    assert "red first" in section
    assert "green" in section
    for written in (WHERE["suite.json"], WHERE["placement-checks.md"], ".claude/settings.json"):
        assert "`{}`".format(written) in section, written
    assert "both tables" in section
    assert "allowlist" in section
    assert "adds a language or a rule" in section


def test_the_usage_docs_say_what_happens_when_the_allowlist_write_is_turned_down():
    section = usage_section("## Turn the rules into tests")

    assert "`allow-commands`" in section
    assert "Claude Code can turn down a" in section
    assert "asks you to add them" in section
    assert "reads the file back" in section
    assert "names any entry still missing" in section


def test_implement_reads_the_suite_from_the_suite_file():
    text = (SKILLS / "implement" / "SKILL.md").read_text(encoding="utf-8")

    assert "README.md" not in text
    assert read_of(WHERE["suite.json"]) in text


def test_implement_builds_with_skillworks_suite_and_leaves_the_loop_s_suite_to_the_driver():
    text = (SKILLS / "implement" / "SKILL.md").read_text(encoding="utf-8")
    building = text.split("## Building", 1)[1].split("\n## ", 1)[0]

    assert "run `skillworks-suite`" in building
    assert "In a loop the driver runs the Suite" in building


def test_implement_says_what_blocked_is_and_how_to_report_it_right_after_test_runs():
    text = skill_text("implement")

    assert text.split("\n## Test runs\n", 1)[1].split("\n## ", 2)[1].startswith(
        "Blocked\n\n"
        "A step is Blocked when you cannot do its work: a tool call was denied and no allowed way "
        "exists, or the ticket has nothing left to build. Begin your report with one line that "
        "starts with `BLOCKED` and says what blocks the step, such as:\n\n"
        "    BLOCKED .claude/settings.json: the write was refused as a sensitive file.\n\n"
        "Say the rest below that line. A driver stops its loop on that line, so a person reads it "
        "before more work is spent. A tool call that was denied, and that you then made in a way "
        "the rules allow, blocks nothing and earns no line.\n")


def test_implement_s_refused_write_ends_on_the_blocked_line_and_not_the_open_ticket():
    refused = section(skill_text("implement"), "A write under `.claude/` refused")

    assert "the driver reads the `BLOCKED` line as the stop" in refused
    assert ("Begin your report with the `BLOCKED` line, and say the same below it, so it reaches "
            "the driver's log as well.") in refused
    assert "the driver reads the open ticket as the stop" not in refused


def test_implement_s_refused_write_keeps_the_ticket_open_through_finishing_and_through_a_nudge():
    text = skill_text("implement")
    refused = section(text, "A write under `.claude/` refused")
    finishing = section(text, "Finishing")

    assert "commit as its step 3 says, and skip the close in its steps 2 and 5" in refused
    assert "Begin your answer to it with the `BLOCKED` line, and close nothing." in refused
    assert "\n2. **With the files Tracker, close the ticket now**" in finishing
    assert "\n3. **Commit to the branch you are on.**" in finishing
    assert "\n5. **With the GitHub Tracker, close the ticket**" in finishing


def test_implement_ends_its_refusal_of_a_blocked_ticket_on_the_blocked_line():
    before = section(skill_text("implement"), "Before you start")

    assert ("A ticket with an open blocker is work you cannot do, so begin that report with the "
            "`BLOCKED` line, as Blocked says below.") in before


# Running the suite never runs in a loop, so a path named only there leaves a build with no Suite file.
def test_implement_s_building_names_the_suite_file_by_its_path():
    building = section(skill_text("implement"), "Building")

    assert read_of(WHERE["suite.json"]) in building


def test_implement_runs_the_suite_by_its_command_in_a_hand_run():
    running = section(skill_text("implement"), "Running the suite")

    assert "Run `skillworks-suite` with no arguments" in running
    assert read_of(WHERE["suite.json"]) in running


READ_THROUGH_STEERING_FILE = re.compile(r"steering-file (docs/skillworks/[\w./*<>-]*)")


# An Export branch holds no Steering on disk, so a path read any other way is a file that is not there.
def steering_read_past_steering_file(text):
    through = {match.start(1) for match in READ_THROUGH_STEERING_FILE.finditer(text)}
    return [match.group(0) for match in STEERING_PATH.finditer(text) if match.start() not in through]


# Setup keeps its own Export route and runs where the Steering is on disk, and the Seeds under it never change.
SKILL_PAGES = sorted(str(page.relative_to(SKILLS)).replace("\\", "/")
                     for page in SKILLS.rglob("*")
                     if page.is_file() and page.relative_to(SKILLS).parts[0] != "skillworks-setup")

# These ask where this branch is and not what the Steering says, so they test the disk on purpose.
DISK_CHECK = re.compile(r"`docs/skillworks/loop\.json` is (?:missing )?on disk")

# A skill that writes Steering stops on an Export branch first, so each write lands on a branch that holds the file.
STEERING_WRITES = {
    "architecture-tests/SKILL.md": ["Add the test's command to `docs/skillworks/suite.json`",
                                    "Fill both tables in `docs/skillworks/placement-checks.md`"],
    "context-backfill/SKILL.md": ["an empty banned-words list, written `[]`, to `docs/skillworks/rules/words.md`"],
}


def without_front_matter(text):
    return text.split("---\n", 2)[2] if text.startswith("---\n") else text


def reads_of_steering(page):
    text = DISK_CHECK.sub("", without_front_matter((SKILLS / page).read_text(encoding="utf-8")))
    for write in STEERING_WRITES.get(page, []):
        text = text.replace(write, "")
    return text


def test_the_sweep_reaches_every_plugin_skill_but_setup():
    swept = {page.split("/", 1)[0] for page in SKILL_PAGES}
    skills = {folder.name for folder in SKILLS.iterdir() if folder.is_dir()}

    assert skills - swept == {"skillworks-setup"}


def test_each_steering_write_a_skill_names_is_still_in_its_page():
    for page, writes in STEERING_WRITES.items():
        text = (SKILLS / page).read_text(encoding="utf-8")
        for write in writes:
            assert write in text, "{} no longer writes {}".format(page, write)


@pytest.mark.parametrize("page", SKILL_PAGES)
def test_a_plugin_skill_reads_each_steering_path_through_steering_file(page):
    assert steering_read_past_steering_file(reads_of_steering(page)) == []


def test_a_steering_path_read_past_steering_file_is_caught():
    text = "Read `steering-file docs/skillworks/domain.md`, then `docs/skillworks/loop.json`."

    assert steering_read_past_steering_file(text) == ["docs/skillworks/loop.json"]


def test_a_disk_check_of_the_export_branch_is_no_steering_read():
    assert DISK_CHECK.sub("", "When `docs/skillworks/loop.json` is missing on disk, stop.") == "When , stop."
