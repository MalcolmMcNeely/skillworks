import io
import json
import re

import pytest
import seed_steering
from conftest import PLUGIN, ROOT, Ran, git, launch
from suite import Suite

SKILLS = PLUGIN / "skills"
SETUP = SKILLS / "skillworks-setup"

WHERE = {
    "comments.md": "docs/agents/rules/comments.md",
    "determinism.md": "docs/agents/rules/determinism.md",
    "file-placement.md": "docs/agents/rules/file-placement.md",
    "words.md": "docs/agents/rules/words.md",
    "issue-tracker.md": "docs/agents/issue-tracker.md",
    "domain.md": "docs/agents/domain.md",
    "placement-checks.md": "docs/agents/placement-checks.md",
    "smell-baseline.md": "docs/agents/smell-baseline.md",
    "arrangement-baseline.md": "docs/agents/arrangement-baseline.md",
    "suite.json": "docs/agents/suite.json",
    "loop.json": "docs/agents/loop.json",
}

WORKING_FOLDERS = [".spec-loop/", ".handoff/", ".claude/worktrees/"]

RULES = ["comments.md", "determinism.md", "file-placement.md", "words.md"]


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


BASES = "docs/agents/.seeds"


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
    edited = repo.work / "docs" / "agents" / "domain.md"
    edited.parent.mkdir(parents=True)
    edited.write_text("# Our own domain notes\n", encoding="utf-8", newline="\n")

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert edited.read_text(encoding="utf-8") == "# Our own domain notes\n"
    assert "kept docs/agents/domain.md, which differs from the seed:\n" in ran.out
    assert not (repo.work / BASES / "domain.md").exists()
    assert (repo.work / BASES / "suite.json").is_file()


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
    assert "kept docs/agents/domain.md, the same as the seed\n" in ran.out


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

    ran = run_seed_settling(runner, repo.work, "docs/agents/domain.md")

    assert ran.status == 1
    assert "docs/agents/domain.md" in ran.err
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
    loop = json.loads((repo.work / "docs" / "agents" / "loop.json").read_text(encoding="utf-8"))
    assert loop == {"target-branch": "master"}


def test_a_loop_file_already_there_is_kept_and_its_difference_shown(repo, runner):
    make_master_the_default(repo)
    held = repo.work / "docs" / "agents" / "loop.json"
    held.parent.mkdir(parents=True)
    held.write_text('{\n  "target-branch": "spec"\n}\n', encoding="utf-8", newline="\n")

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert held.read_text(encoding="utf-8") == '{\n  "target-branch": "spec"\n}\n'
    assert "kept docs/agents/loop.json, which differs from the seed:\n" in ran.out
    assert '-  "target-branch": "spec"\n' in ran.out
    assert '+  "target-branch": "master"\n' in ran.out


def test_a_repo_with_no_origin_stops_before_anything_is_written(repo, runner):
    git(repo.work, "remote", "remove", "origin")

    ran = run_seed(runner, repo.work)

    assert ran.status == 1
    assert "origin" in ran.err
    assert "Nothing was written." in ran.err
    assert not (repo.work / "docs").exists()


def test_every_seed_lands_under_docs_agents_and_the_rules_in_its_rules_folder(repo, runner):
    run_seed(runner, repo.work)

    assert not (repo.work / ".claude" / "rules").exists()
    assert sorted(seed_steering.PLACES) == sorted(WHERE)
    for seed, place in seed_steering.PLACES.items():
        assert place.startswith("docs/agents/"), place
        assert (place == "docs/agents/rules/" + seed) == (seed in RULES), place


def test_a_rule_already_in_the_rules_folder_is_kept_and_its_difference_shown(repo, runner):
    edited = repo.work / "docs" / "agents" / "rules" / "words.md"
    edited.parent.mkdir(parents=True)
    edited.write_text("# Our own words\n", encoding="utf-8", newline="\n")

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert edited.read_text(encoding="utf-8") == "# Our own words\n"
    assert "kept docs/agents/rules/words.md, which differs from the seed:\n" in ran.out
    assert "-# Our own words\n" in ran.out
    assert "wrote docs/agents/rules/words.md" not in ran.out


def test_the_seeds_folder_holds_the_listed_seeds_and_nothing_else():
    assert sorted(path.name for path in (SETUP / "seeds").iterdir()) == sorted(WHERE)


def test_the_rules_arrive_with_their_settings_empty(repo, runner):
    run_seed(runner, repo.work)
    rules = repo.work / "docs" / "agents" / "rules"

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


@pytest.mark.parametrize("seed", sorted(OLDER))
def test_a_file_the_team_deleted_stays_deleted_and_is_said_to_be_left_out(repo, runner, seed):
    seeded_by_an_older_plugin(repo, runner, seed)
    place = WHERE[seed]
    (repo.work / place).unlink()

    ran = run_seed(runner, repo.work)

    assert ran.status == 0, ran.err
    assert not (repo.work / place).exists()
    assert (repo.work / BASES / seed).read_text(encoding="utf-8") == OLDER[seed]
    assert "left out {}, which you deleted\n".format(place) in ran.out
    assert "wrote {}\n".format(place) not in ran.out


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

    ran = run_seed_choosing(runner, repo.work, "docs/agents/domain.md:1=yours")

    assert ran.status == 1
    assert "docs/agents/domain.md:1" in ran.err
    assert on_disk(repo.work) == before


@pytest.mark.parametrize("choice", ["docs/agents/domain.md:1", "docs/agents/domain.md=yours",
                                    "docs/agents/domain.md:x=yours", "docs/agents/domain.md:1=both"])
def test_a_choice_written_wrong_prints_the_usage(repo, runner, choice):
    ran = run_seed_choosing(runner, repo.work, choice)

    assert ran.status == 64
    assert ran.err == seed_steering.USAGE


def test_the_issue_tracker_seed_holds_the_two_conventions():
    tracker = seeded("issue-tracker.md")

    assert "### Two conventions the loop leans on" in tracker
    assert "`Ticket: #<n>`" in tracker
    assert "gh issue close <n> --comment" in tracker


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


def test_the_smell_baseline_seed_holds_the_smells_list():
    smells = seeded("smell-baseline.md")

    assert "## The twelve" in smells
    assert "- **Feature Envy** — a method that reaches into another object's data more than its own." in smells
    assert "## The four" in smells
    assert "- **Stub Echo** — a stub is handed a value" in smells
    assert len(re.findall(r"^- \*\*[A-Z][^*]+\*\* — ", smells, re.MULTILINE)) == 16


def test_the_review_skills_read_the_smells_list_from_the_smell_baseline():
    for skill in ["code-review", "review-standards"]:
        text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")

        assert "`docs/agents/smell-baseline.md`" in text, skill
        assert "Feature Envy" not in text, skill
        assert "twelve" not in text.lower(), skill


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
    ours = (ROOT / "docs" / "agents" / "issue-tracker.md").read_text(encoding="utf-8")

    assert ticket_shape(ours) == ticket_shape(seeded("issue-tracker.md"))


def test_to_tickets_reads_the_ticket_shape_from_the_tracker_docs():
    to_tickets = (SKILLS / "to-tickets" / "SKILL.md").read_text(encoding="utf-8")

    assert "The ticket shape" in to_tickets
    assert "context window" not in to_tickets
    assert "TICKET:" not in to_tickets
    assert "## Acceptance criteria" not in to_tickets
    assert "-template>" not in to_tickets


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


def test_the_review_skills_stop_when_the_smell_baseline_is_missing():
    for skill in ["code-review", "review-standards"]:
        assert stops(skill, "`docs/agents/smell-baseline.md`"), skill


def test_to_tickets_stops_when_the_tracker_docs_or_the_ticket_shape_is_missing():
    assert stops("to-tickets", "`docs/agents/issue-tracker.md`", '"The ticket shape"')


def test_a_missing_lever_that_only_sends_the_user_to_setup_is_caught():
    tells = "If `docs/agents/issue-tracker.md` is missing, tell the user to run `/skillworks:skillworks-setup`."

    assert not says_stop(tells, "`docs/agents/issue-tracker.md`")


def test_the_issue_tracker_seed_says_how_to_read_a_commits_sessions_back():
    tracker = seeded("issue-tracker.md")

    assert "`Skillworks-Session: <id>`" in tracker
    assert "git log -1 <commit> --format='%(trailers:key=Skillworks-Session,valueonly)'" in tracker
    assert "claude --resume" in tracker


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

    assert len(commands) == 6
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
    assert len(names) == 11
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
    text = "[suite](../../../../docs/agents/suite.json) and [skill](../tdd/SKILL.md)"

    assert links_out_of_the_plugin(page, text) == ["../../../../docs/agents/suite.json"]


def test_no_plugin_skill_names_a_rule_under_the_old_rules_folder():
    pages = sorted(path for path in SKILLS.rglob("*") if path.is_file())
    assert pages

    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert ".claude/rules" not in text, page
        for rule in RULES:
            assert "docs/agents/{}".format(rule) not in text, "{} names {} outside the rules folder".format(page, rule)


STEERING_NAMED = {
    "review-standards": ["smell-baseline.md"],
    "review-architecture": ["placement-checks.md", "arrangement-baseline.md"],
    "code-review": ["smell-baseline.md", "placement-checks.md", "arrangement-baseline.md"],
}


def test_the_review_skills_name_each_steering_file_by_its_path_from_the_repo_root():
    for skill, names in STEERING_NAMED.items():
        text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        for name in names:
            assert "`{}`".format(WHERE[name]) in text, "{} names {}".format(skill, name)
            assert "`{}`](".format(WHERE[name]) not in text, "{} links {}".format(skill, name)


def test_spec_loop_says_why_the_script_picks_the_ticket_and_links_no_research_note():
    text = (SKILLS / "spec-loop" / "SKILL.md").read_text(encoding="utf-8")

    assert "docs/research" not in text
    assert "A script reads the blocking edges and picks the same ticket every time." in text


def setup_section(heading):
    text = (SETUP / "SKILL.md").read_text(encoding="utf-8")
    return re.split(r"\n### \d", text.split(heading, 1)[1], maxsplit=1)[0]


def test_the_claude_md_pointer_imports_each_rule():
    pointer = re.findall(r"```markdown\n(.*?)```", setup_section("### 3. Point CLAUDE.md at the docs"), re.DOTALL)

    assert len(pointer) == 1
    lines = pointer[0].splitlines()
    for rule in RULES:
        assert "@docs/agents/rules/{}".format(rule) in lines, rule


def test_the_report_names_the_folder_each_steering_file_lives_in():
    report = setup_section("### 5. Report")

    assert "`docs/agents/rules/`" in report
    assert "`docs/agents/`" in report
    for seed in WHERE:
        assert "`{}`".format(seed) in report, seed


# Each holds only for this repository, so a skill that says one tells a team about a repo it is not in.
SKILL_HABITS = ["slice rules", "slice whose job it serves", "no branches and no pull requests", "co-authored by",
                "co-author line", "under checks"]


def test_no_plugin_skill_says_a_habit_of_this_repo():
    pages = sorted(path for path in SKILLS.rglob("*.md") if (SETUP / "seeds") not in path.parents)
    assert pages

    for page in pages:
        text = page.read_text(encoding="utf-8").lower()
        for habit in SKILL_HABITS:
            assert habit not in text, "{} says {}".format(page, habit)


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

    for machinery in ("`tdd`", "`codebase-design`", "`unslop`", "output style", "auto-memory"):
        assert machinery in fixed, machinery


def test_the_usage_front_page_lists_the_steering_page():
    assert "(steering.md)" in (ROOT / "docs" / "usage" / "README.md").read_text(encoding="utf-8")


USAGE_FRONT_PAGE = "https://github.com/MalcolmMcNeely/skillworks/blob/main/docs/usage/README.md"


def test_the_report_ends_with_a_link_to_the_usage_front_page():
    last = setup_section("### 5. Report").strip().splitlines()[-1]

    assert "]({})".format(USAGE_FRONT_PAGE) in last
    assert (ROOT / USAGE_FRONT_PAGE.split("/blob/main/", 1)[1]).is_file()


SETUP_PAGE = ROOT / "docs" / "usage" / "setup.md"


OUTCOMES = ["`wrote`", "`updated`", "`kept ..., which you edited`", "`kept ..., the same as the seed`", "`merged`",
            "`asks`", "`left out`", "`kept ..., which differs from the seed`", "`kept ..., as you settled it`"]


def test_the_seed_step_names_each_outcome_the_questions_and_the_review_before_commit():
    step = setup_section("### 1. Seed the Steering")

    for outcome in OUTCOMES:
        assert "| {} |".format(outcome) in step, outcome
    assert "--keep " in step
    assert "--settled " in step
    assert "before you change anything" in step
    assert "before they commit" in step


def test_the_setup_page_explains_each_outcome_of_a_second_run():
    again = SETUP_PAGE.read_text(encoding="utf-8").split("## Run setup again", 1)[1]

    for outcome in OUTCOMES:
        assert "| {} |".format(outcome) in again, outcome
    assert "`docs/agents/.seeds/`" in again
    assert "before you commit" in again


def test_the_usage_front_page_lists_the_setup_page():
    assert "(setup.md)" in (ROOT / "docs" / "usage" / "README.md").read_text(encoding="utf-8")


def test_the_setup_page_names_every_file_setup_writes():
    page = SETUP_PAGE.read_text(encoding="utf-8")

    for place in list(WHERE.values()) + WORKING_FOLDERS + [".gitignore", "CLAUDE.md", ".claude/settings.json"]:
        assert "`{}`".format(place) in page, place


def test_implement_reads_the_suite_from_the_suite_file():
    text = (SKILLS / "implement" / "SKILL.md").read_text(encoding="utf-8")

    assert "README.md" not in text
    assert "`{}`".format(WHERE["suite.json"]) in text


def test_implement_builds_with_skillworks_suite_and_leaves_the_loop_s_suite_to_the_driver():
    text = (SKILLS / "implement" / "SKILL.md").read_text(encoding="utf-8")
    building = text.split("## Building", 1)[1].split("\n## ", 1)[0]

    assert "run `skillworks-suite`" in building
    assert "In a loop the driver runs the Suite" in building
