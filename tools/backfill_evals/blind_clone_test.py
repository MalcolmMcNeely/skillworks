# Only Claude Code is answered for, because no build starts it and the image the tests run in does not hold it.

import io
import json
import re
import subprocess
from pathlib import Path

import pytest

import blind_clone
from runner import NOT_FOUND, Ran, Subprocess

SEEDS = "plugins/skillworks/skills/skillworks-setup/seeds"
WORDS_SEED = "# Words\n\nThe seed's own words rule.\n"
DOMAIN_SEED = "# Domain docs\n\nThe seed's own domain docs.\n"
SKILL = "plugins/skillworks/skills/context-backfill/SKILL.md"
SCRIPT = "plugins/skillworks/scripts/context_backfill/backfill.py"
BIN = "plugins/skillworks/bin/context-backfill"

RECORD_PATHS = ("CONTEXT.md", "CONTEXT-MAP.md", "docs/adr/")
NAMES_A_RECORD = re.compile(r"glossar|CONTEXT(-MAP)?\.md|\bADR|docs/adr|stint", re.IGNORECASE)
ADR_NUMBER = re.compile(r"\badr[- ]?[0-9]|adr/[0-9]", re.IGNORECASE)


def git(where, *args, env=None):
    done = subprocess.run(["git", "-C", Path(where).as_posix()] + [str(a) for a in args],
                          capture_output=True, encoding="utf-8", errors="replace", env=env)
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


def write(top, path, text):
    file = Path(top) / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8", newline="\n")


def commit(top, message, files):
    for path, text in files.items():
        write(top, path, text)
    git(top, "add", "-A")
    git(top, "commit", "--quiet", "-m", message)


def planted(top):
    git(top.parent, "init", "--quiet", "--initial-branch=main", top.as_posix())
    for name, value in (("user.name", "Test"), ("user.email", "test@example.invalid"),
                        ("commit.gpgsign", "false"), ("tag.gpgsign", "false"),
                        ("core.autocrlf", "false")):
        git(top, "config", name, value)
    commit(top, "Base", {
        "CLAUDE.md": "# Repo\n\n### Domain docs\n\nMulti-context: the map and one glossary per context.\n"
                     "See `docs/agents/domain.md`.\n",
        "docs/agents/loop.json": json.dumps({"tracker": "github", "target-branch": "main"}, indent=2) + "\n",
        "docs/agents/rules/words.md": "# Words\n\n```yaml\nbanned-words:\n  studio:\n    - Stint\n"
                                      "skip-folders: []\n```\n",
        "docs/agents/domain.md": "# Domain docs\n\nThis repo is multi-context.\n",
        SEEDS + "/words.md": WORDS_SEED,
        SEEDS + "/domain.md": DOMAIN_SEED,
        SKILL: "The skill before the arm.\n",
        SCRIPT: "BEFORE = True\n",
        BIN: "#!/bin/sh\necho before\n",
        "src/app.py": "x = 1\n",
    })
    commit(top, "Glossary: Studio's words", {"docs/studio/CONTEXT.md": "**Stretch**:\nA span.\n"})
    commit(top, "ADR: Keep one Clock", {"docs/adr/0001-keep-one-clock.md": "# Keep one Clock\n"})
    commit(top, "Name the contexts\n\nThe map in CONTEXT-MAP.md names Studio.\n"
                "It follows docs/adr/0001-keep-one-clock.md.\nNo Stint survives.\nThe code reads the same.",
           {"CONTEXT-MAP.md": "# Context Map\n", ".claude/CONTEXT.md": "**Loop**:\nThe loop.\n"})
    commit(top, "Point the code at its reason", {
        "src/app.py": "# See ADR 0001, ADR-0001 and [why](docs/adr/0001-keep-one-clock.md).\nx = 1\n"})
    commit(top, "Split the records into Statements", {
        "tools/backfill_evals/statements/0001-keep-one-clock.json": '{"title": "Keep one Clock"}\n'})
    pin = git(top, "rev-parse", "HEAD").strip()
    commit(top, "The arm's skill", {SKILL: "The skill under test.\n", SCRIPT: "UNDER_TEST = True\n",
                                    BIN: "#!/bin/sh\necho under test\n"})
    git(top, "tag", "arm")
    return pin


class Machine(Subprocess):
    def __init__(self, missing=None):
        self.missing = missing

    def found(self, name):
        if self.missing == name:
            return False
        return name == "claude" or super().found(name)

    def run(self, args, where=None, env=None):
        assert args[0] != "claude", "no build starts Claude Code"
        if self.missing == blind_clone.FILTER_REPO and any(blind_clone.FILTER_REPO in str(a) for a in args):
            return Ran(1, "", "No solution found when resolving tool dependencies.\n")
        if self.missing == args[0]:
            return Ran(NOT_FOUND, "", args[0] + ": not found\n")
        return super().run(args, where, env)


def built(argv, source, pin_file, machine=None):
    out, err = io.StringIO(), io.StringIO()
    status = blind_clone.main(argv, machine or Machine(), out, err, source.as_posix(), pin_file)
    return status, out.getvalue(), err.getvalue()


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    root = tmp_path_factory.mktemp("blind")
    source = root / "source"
    pin = planted(source)
    pin_file = root / "pin.json"
    first = built(["pin", pin, root / "first", "--arm", "arm"], source, pin_file)
    assert first[0] == 0, first[2]
    second = built(["build", root / "second", "--arm", "arm"], source, pin_file)
    return root, source, pin, pin_file, second


@pytest.fixture(scope="module")
def clone(made):
    return made[0] / "first" / "repo"


def every_commit(clone):
    return git(clone, "rev-list", "--all").split()


def test_no_record_path_is_in_any_commit(clone):
    paths = set(git(clone, "log", "--all", "--name-only", "--format=").split())

    assert [p for p in paths if p.endswith(RECORD_PATHS) or p.startswith("docs/adr/")] == []


def test_a_pin_after_the_harness_landed_hands_the_clone_no_statement_file(clone):
    paths = set(git(clone, "log", "--all", "--name-only", "--format=").split())

    assert [p for p in paths if p.startswith("tools/backfill_evals/")] == []


def test_no_commit_line_names_a_record(clone):
    lines = git(clone, "log", "--all", "--format=%B").splitlines()

    assert [line for line in lines if NAMES_A_RECORD.search(line)] == []


def test_no_file_in_any_commit_carries_an_adr_number(clone):
    carried = []
    for sha in every_commit(clone):
        for path in git(clone, "ls-tree", "-r", "--name-only", sha).split():
            if ADR_NUMBER.search(git(clone, "show", "{}:{}".format(sha, path))):
                carried.append((sha, path))

    assert carried == []


def test_the_steering_a_backfill_fills_is_its_seed(clone):
    steering = [(clone / "docs/agents/rules/words.md").read_text(encoding="utf-8"),
                (clone / "docs/agents/domain.md").read_text(encoding="utf-8")]

    assert steering == [WORDS_SEED, DOMAIN_SEED]


def test_the_tracker_is_files(clone):
    loop = json.loads((clone / "docs/agents/loop.json").read_text(encoding="utf-8"))

    assert loop == {"tracker": "files", "target-branch": "main"}


def test_git_ignores_the_scratch_folder(clone):
    write(clone, ".context-backfill/sheet.md", "a sheet\n")

    assert git(clone, "status", "--porcelain", "--", ".context-backfill") == ""


def test_claude_md_says_single_context(clone):
    steering = (clone / "CLAUDE.md").read_text(encoding="utf-8")

    assert "Single-context: `CONTEXT.md` and `docs/adr/` at the repo root.\n" in steering


def test_the_reset_commit_is_the_only_new_commit(made, clone):
    _, source, pin, _, _ = made
    subjects = git(clone, "log", "--format=%s").splitlines()
    rewritten = [s if not s.startswith(("ADR:", "Glossary:")) else "A record"
                 for s in git(source, "log", "--format=%s", pin).splitlines()]

    assert subjects[1:] == rewritten


def test_the_pin_stores_the_tree_the_build_made(made):
    root, _, _, pin_file, _ = made
    stored = json.loads(pin_file.read_text(encoding="utf-8"))
    tree = git(root / "first" / "repo", "rev-parse", "HEAD^{tree}").strip()

    assert stored["tree"] == tree


def test_a_second_build_gives_the_same_hashes(made):
    _, _, _, pin_file, second = made
    stored = json.loads(pin_file.read_text(encoding="utf-8"))
    status, out, _ = second

    assert (status, out.count(stored["tree"]), out.count(stored["records"])) == (0, 1, 1)


def test_a_build_whose_tree_differs_from_the_pin_is_refused_with_both_hashes(made, tmp_path):
    root, source, _, pin_file, _ = made
    stored = json.loads(pin_file.read_text(encoding="utf-8"))
    wrong = dict(stored, tree="0" * 40)
    other_pin = tmp_path / "pin.json"
    other_pin.write_text(json.dumps(wrong), encoding="utf-8")

    status, _, err = built(["build", tmp_path / "clone", "--arm", "arm"], source, other_pin)

    assert (status, "0" * 40 in err, stored["tree"] in err) == (1, True, True)


@pytest.mark.parametrize("missing, named", [("claude", "Claude Code"), ("uv", "uv"), ("git", "git"),
                                            ("git-filter-repo", "git-filter-repo")])
def test_a_build_with_a_tool_missing_stops_and_names_it(made, tmp_path, missing, named):
    _, source, _, pin_file, _ = made

    status, _, err = built(["build", tmp_path / "clone", "--arm", "arm"], source, pin_file, Machine(missing))

    assert (status, "{} is missing".format(named) in err) == (1, True)


def test_the_plugin_holds_the_skill_scripts_and_bin_of_the_arm(clone):
    held = [(clone / path).read_text(encoding="utf-8") for path in (SKILL, SCRIPT, BIN)]

    assert held == ["The skill under test.\n", "UNDER_TEST = True\n", "#!/bin/sh\necho under test\n"]


def test_a_fetch_of_the_target_branch_from_origin_succeeds(clone):
    done = subprocess.run(["git", "-C", clone.as_posix(), "fetch", "origin", "main"],
                          capture_output=True, encoding="utf-8", errors="replace")

    assert done.returncode == 0, done.stderr
