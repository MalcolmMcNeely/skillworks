# A Session is answered for, because a real run of the backfill takes two hours.

import io
import json
from pathlib import Path

import pytest

import compare
import harness
import score
from harness_test import ALL_YES, FABLE, MAPPED, SHEET, TODAY, Judge, commit, git, given_statements, pinned
from runner import Ran

SKILL = "plugins/skillworks/skills/context-backfill/SKILL.md"
SKILLED = (("Write the skill", {SKILL: "The old skill.\n"}),)
QUESTION = "One glossary, or a map with these contexts? Studio claims `src`, and Loop claims `plugins`."
FINDING = "# Shape\n\n## Finding\n\n### Studio\n\n`src/Studio.Api`, `src/Studio.Web`\n\n### Loop\n\n`.claude`\n"
FIRST_MINUTES, FIRST_DOLLARS = 10, 1.5

PLAN = {
    "old": {"run-1": ("sheet", 50, 3.0), "run-2": ("sheet", 60, 4.0), "run-3": ("sheet", 70, 5.0)},
    "new": {"run-1": ("sheet", 70, 6.0), "run-2": ("no sheet", 30, 2.0), "run-3": ("capped", 0, 0.0)},
}
REPLIES = {arm: {run: ALL_YES for run, (kind, _, _) in kept.items() if kind == "sheet"}
           for arm, kept in PLAN.items()}


def session_output(session, result, minutes, dollars):
    return json.dumps({"session_id": session, "result": result, "duration_ms": minutes * 60000,
                       "total_cost_usd": dollars, "modelUsage": {FABLE: {"outputTokens": 9000}}})


class Backfill(Judge):
    def __init__(self, replies, plan=PLAN):
        super().__init__(replies)
        self.plan = plan
        self.sessions = []
        self.skills = {}

    def capped(self, args, where, env, seconds):
        args = [str(a) for a in args]
        self.sessions.append((where, args, seconds))
        clone = Path(where)
        arm, _, run = clone.parent.name.partition("-")
        kind, minutes, dollars = self.plan[arm][run]
        scratch = clone / ".context-backfill"
        scratch.mkdir(exist_ok=True)
        if "--resume" not in args:
            self.skills[(arm, run)] = (clone / SKILL).read_text(encoding="utf-8")
            (scratch / "fit.md").write_text("Commits: 9\n", encoding="utf-8")
            (scratch / "shape.md").write_text(FINDING, encoding="utf-8")
            return Ran(0, session_output(arm + run, QUESTION, FIRST_MINUTES, FIRST_DOLLARS), "")
        if kind == "capped":
            return Ran(compare.TIMED_OUT, "Reading the history", "")
        if kind == "no sheet":
            return Ran(1, session_output(arm + run, "The words pass stopped: its subagent ran out of room.",
                                         minutes, dollars), "")
        (scratch / score.SHEET_FILE).write_text(SHEET.format(arm + " " + run), encoding="utf-8")
        (scratch / "decisions.md").write_text("# Decisions\n\n## Failed a test\n", encoding="utf-8")
        return Ran(0, session_output(arm + run, "The sheet is written.", minutes, dollars), "")


def resumes(runner):
    return [args[args.index("-p") + 1] for _, args, _ in runner.sessions if "--resume" in args]


@pytest.fixture(scope="module")
def compare_source(tmp_path_factory):
    root = tmp_path_factory.mktemp("compare")
    top, pin, records, pin_file = pinned(root, *(MAPPED + SKILLED))
    origin = root / "origin.git"
    git(root, "init", "--quiet", "--bare", "--initial-branch=main", origin.as_posix())
    git(top, "remote", "add", "origin", origin.as_posix())
    git(top, "push", "--quiet", "-u", "origin", "main")
    commit(top, "Change the skill, and push nothing", {SKILL: "A skill committed and never pushed.\n"})
    (top / SKILL).write_text("The new skill, in the working tree.\n", encoding="utf-8")
    return top, pin, records, pin_file


def compared_in(source, root, runner):
    top, _, records, pin_file = source
    folder = root / "statements"
    if not folder.is_dir():
        given_statements(folder, records)
    out, err = io.StringIO(), io.StringIO()
    status = harness.main(["compare"], runner, out, err, top.as_posix(), TODAY,
                          runs=root / "runs", pin_file=pin_file, statements_folder=folder)
    return status, out.getvalue(), err.getvalue()


@pytest.fixture(scope="module")
def compared(compare_source, tmp_path_factory):
    root = tmp_path_factory.mktemp("compared")
    runner = Backfill(REPLIES)
    status, out, err = compared_in(compare_source, root, runner)
    return status, out, err, runner, root


def test_compare_resumes_every_run_with_one_answer_that_names_the_real_maps_contexts_and_folders(compared):
    status, _, err, runner, _ = compared
    named = ("Studio", "Loop", "`src/Studio.Api`", "`src/Studio.Web`", "`tests/Studio.Tests`", "`.claude`",
             "`plugins/loop`")

    answers = set(resumes(runner))

    assert (status, len(resumes(runner)), len(answers), all(name in answer for answer in answers for name in named)) \
        == (0, 6, 1, True), err


@pytest.mark.parametrize("name", [score.OUTPUT_FILE, score.QUESTION_FILE, score.SHEET_FILE, "shape.md",
                                  "decisions.md", "fit.md"])
def test_each_run_keeps_its_output_sheet_and_pass_files_in_a_folder_of_its_own(compared, name):
    _, _, _, _, root = compared

    assert sorted(run for run in ("run-1", "run-2", "run-3")
                  if (root / "runs" / TODAY / "old" / run / name).is_file()) == ["run-1", "run-2", "run-3"]


def test_score_over_the_kept_comparison_prints_the_same_table_and_starts_no_session(compare_source, compared):
    top, _, _, pin_file = compare_source
    _, table, _, _, root = compared
    runner = Backfill(REPLIES)
    out, err = io.StringIO(), io.StringIO()

    status = harness.main(["score", TODAY], runner, out, err, top.as_posix(), TODAY, runs=root / "runs",
                          pin_file=pin_file, statements_folder=root / "statements")

    assert (status, out.getvalue() == table, runner.sessions) == (0, True, []), err.getvalue()


@pytest.mark.parametrize("line", [
    "- new run-2 left no Answer sheet. Its output says: The words pass stopped: its subagent ran out of room.",
    "- new run-3 hit its time cap of 180 minutes. Its output says: Reading the history",
])
def test_a_run_with_no_sheet_or_that_hits_the_time_cap_is_listed_as_failed_with_what_its_output_says(compared, line):
    _, out, _, _, _ = compared

    assert line in out.splitlines()


def test_every_session_of_a_run_loads_the_plugin_from_its_own_clone(compared):
    _, _, _, runner, _ = compared

    named = {args[args.index("--plugin-dir") + 1] == where + "/plugins/skillworks"
             for where, args, _ in runner.sessions}

    assert (len(runner.sessions), named) == (12, {True})


def test_a_run_is_stopped_at_the_time_cap_less_what_its_first_session_spent(compared):
    _, _, _, runner, _ = compared

    assert {seconds for _, args, seconds in runner.sessions if "--resume" in args} == {
        (compare.CAP_MINUTES - FIRST_MINUTES) * 60}


@pytest.mark.parametrize("row", [
    "| Run time, minutes | 70.0 | 60 to 80 | 80.0 | 80 to 80 | +10.0 |",
    "| Cost at list price, US dollars | 5.50 | 4.50 to 6.50 | 7.50 | 7.50 to 7.50 | +2.00 |",
])
def test_run_time_and_list_price_cost_are_printed_old_against_new_with_their_spread(compared, row):
    _, out, err, _, _ = compared

    assert row in out.splitlines(), err + out


def test_with_no_refs_the_old_arm_is_the_target_branch_on_origin_and_the_new_arm_the_working_tree(compared):
    _, _, _, runner, _ = compared

    assert {arm: {text for (held, _), text in runner.skills.items() if held == arm} for arm in ("old", "new")} == {
        "old": {"The old skill.\n"}, "new": {"The new skill, in the working tree.\n"}}


def test_the_header_names_each_arm_by_its_ref_and_commit(compare_source, compared):
    top, pin, _, _ = compare_source
    _, out, _, _, _ = compared
    head = git(top, "rev-parse", "HEAD").strip()

    assert [line for line in out.splitlines() if line.startswith(("- Old arm:", "- New arm:"))] == [
        "- Old arm: origin/main at " + pin, "- New arm: the working tree, on " + head]
