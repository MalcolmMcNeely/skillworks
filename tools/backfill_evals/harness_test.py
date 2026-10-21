# Only Claude Code is answered for, because a real judge costs a model call and can answer each Statement differently.

import io
import json
import subprocess
from pathlib import Path

import pytest

import blind_clone
import harness
import score
from runner import Ran, Subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

KEEP = "0001-keep-one-clock"
SPLIT = "0002-split-the-stores"
FABLE = "claude-fable-5-1"
OPUS = "claude-opus-5-5"
TODAY = "2026-10-21"
VERSION = "2.1.5 (Claude Code)"

STATEMENTS = {
    KEEP: ("Keep one Clock", [("decision", "Studio reads one Clock."), ("reason", "A test holds it still.")]),
    SPLIT: ("Split the stores", [("decision", "Events and spans go to two stores."),
                                 ("decision", "Spans go to a trace store."),
                                 ("rejected", "One store for both was turned down.")]),
}

SHEET = ("# Answer sheet\n\n## Words\n\n### Draft W1: Clock\nAnswer:\n\n## Decisions\n\n"
         "### Draft D1: {}\nAnswer:\nStudio reads one Clock.\nEvidence:\n- commit abc1234\n\n"
         "## Questions\n\n### Question D2: Why two stores?\nReason:\n\n## Thin\n")


def git(where, *args):
    done = subprocess.run(["git", "-C", Path(where).as_posix()] + [str(a) for a in args],
                          capture_output=True, encoding="utf-8", errors="replace")
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


def commit(top, message, files):
    for path, text in files.items():
        file = Path(top) / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8", newline="\n")
    git(top, "add", "-A")
    git(top, "commit", "--quiet", "-m", message)


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    top = tmp_path_factory.mktemp("harness") / "source"
    git(top.parent, "init", "--quiet", "--initial-branch=main", top.as_posix())
    for name, value in (("user.name", "Test"), ("user.email", "test@example.invalid"),
                        ("commit.gpgsign", "false"), ("core.autocrlf", "false")):
        git(top, "config", name, value)
    commit(top, "Read one Clock", {"src/clock.py": "CLOCK = 1\n"})
    commit(top, "ADR: Keep one Clock", {"docs/adr/{}.md".format(KEEP): "# Keep one Clock\n"})
    commit(top, "ADR: Split the stores", {"docs/adr/{}.md".format(SPLIT): "# Split the stores\n"})
    pin = git(top, "rev-parse", "HEAD").strip()
    records = blind_clone.records_hash(Subprocess(), top, pin)
    pin_file = top.parent / "pin.json"
    pin_file.write_text(json.dumps({"commit": pin, "tree": "a tree", "records": records}), encoding="utf-8")
    return top, pin, records, pin_file


def given_statements(folder, split_on):
    folder.mkdir(parents=True)
    for stem, (title, said) in STATEMENTS.items():
        (folder / (stem + ".json")).write_text(json.dumps({
            "split-on": split_on, "title": title, "commits": [],
            "statements": [{"kind": kind, "says": says} for kind, says in said]}), encoding="utf-8")
    return folder


def output_of(writer, result="The sheet is written."):
    return json.dumps({"result": result, "modelUsage": {
        writer: {"outputTokens": 9000}, "claude-haiku-5-5": {"outputTokens": 400}}})


def given_runs(runs, arms, writers=None):
    folder = runs / "comparison"
    folder.mkdir(parents=True)
    (folder / score.COMPARISON_FILE).write_text(json.dumps(
        {"old": "origin/main", "new": "the working tree", "claude-code": "2.1.4 (Claude Code)",
         "started": "2026-10-20"}), encoding="utf-8")
    for arm, kept in arms.items():
        for run, replies in kept.items():
            held = folder / arm / run
            held.mkdir(parents=True)
            writer = (writers or {}).get(arm, FABLE)
            if replies is None:
                (held / score.OUTPUT_FILE).write_text(
                    output_of(writer, "The Session stopped at its time cap."), encoding="utf-8")
                continue
            (held / score.OUTPUT_FILE).write_text(output_of(writer), encoding="utf-8")
            (held / score.SHEET_FILE).write_text(SHEET.format(arm + " " + run), encoding="utf-8")
    return folder


class Judge(Subprocess):
    def __init__(self, replies, resolved=OPUS):
        self.replies = replies
        self.resolved = resolved
        self.asked = []
        self.read = []

    def found(self, name):
        return name == "claude" or super().found(name)

    def run(self, args, where=None, env=None):
        args = [str(a) for a in args]
        if args[0] != "claude":
            return super().run(args, where, env)
        if "--version" in args:
            return Ran(0, VERSION + "\n", "")
        self.asked.append(args)
        prompt = args[args.index("-p") + 1]
        run = Path(where)
        record = next(stem for stem, (title, _) in STATEMENTS.items() if title in prompt)
        self.read.append((where, STATEMENTS[record][0]))
        said = self.replies[run.parent.name][run.name][record]
        return Ran(0, json.dumps({"result": "I read the sheet.\n\n" + said,
                                  "modelUsage": {self.resolved: {"outputTokens": 300}}}), "")


def scored(source, tmp_path, arms, writers=None, split_on=None, resolved=OPUS):
    top, _, records, pin_file = source
    runs = tmp_path / "runs"
    given_runs(runs, {arm: {run: (None if replies is None else True) for run, replies in kept.items()}
                      for arm, kept in arms.items()}, writers)
    folder = given_statements(tmp_path / "statements", split_on or records)
    judge = Judge(arms, resolved)
    out, err = io.StringIO(), io.StringIO()
    status = harness.main(["score", "comparison"], judge, out, err, top.as_posix(), TODAY,
                          runs=runs, pin_file=pin_file, statements_folder=folder)
    return status, out.getvalue(), err.getvalue(), judge


ALL_YES = {KEEP: "S1: yes Draft D1\nS2: yes Draft D1",
           SPLIT: "S1: yes Draft D1\nS2: yes Draft D1\nS3: yes Draft D1"}

TWO_ARMS = {
    "old": {
        "run-1": {KEEP: "S1: yes Draft D1\nS2: no", SPLIT: "S1: yes Draft D1\nS2: no\nS3: no"},
        "run-2": {KEEP: "S1: yes Draft D1\nS2: yes Draft D1", SPLIT: "S1: yes Draft D1\nS2: yes Draft D1\nS3: no"},
    },
    "new": {
        "run-1": ALL_YES,
        "run-2": {KEEP: "S1: yes Draft D1\nS2: unknown", SPLIT: ALL_YES[SPLIT]},
        "run-3": None,
    },
}


@pytest.fixture(scope="module")
def two_arms(source, tmp_path_factory):
    return scored(source, tmp_path_factory.mktemp("two-arms"), TWO_ARMS)


@pytest.mark.parametrize("row", [
    "| Statement recall, decision | 83.3% | 66.7% to 100.0% | 100.0% | 100.0% to 100.0% | +16.7 |",
    "| Statement recall, reason | 50.0% | 0.0% to 100.0% | 50.0% | 0.0% to 100.0% | +0.0 |",
    "| Statement recall, rejected | 0.0% | 0.0% to 0.0% | 100.0% | 100.0% to 100.0% | +100.0 |",
    "| Records found, of 2 | 1.5 | 1 to 2 | 2.0 | 2 to 2 | +0.5 |",
])
def test_score_prints_each_measure_old_against_new_with_its_spread(two_arms, row):
    status, out, err, _ = two_arms

    assert (status, row in out.splitlines()) == (0, True), err + out


def one_run_each(old, new=ALL_YES):
    return {"old": {"run-1": old}, "new": {"run-1": new}}


def test_a_question_that_holds_a_decision_statement_makes_it_found(source, tmp_path):
    asked = {KEEP: "S1: yes Question D2\nS2: no", SPLIT: "S1: no\nS2: no\nS3: no"}

    _, out, _, _ = scored(source, tmp_path, one_run_each(asked))

    assert "| Records found, of 2 | 1.0 | 1 to 1 | 2.0 | 2 to 2 | +1.0 |" in out.splitlines()


def test_a_question_holds_no_reason_statement(source, tmp_path):
    asked = {KEEP: "S1: yes Draft D1\nS2: yes Question D2", SPLIT: ALL_YES[SPLIT]}

    _, out, _, _ = scored(source, tmp_path, one_run_each(asked))

    assert "| Statement recall, reason | 0.0% | 0.0% to 0.0% | 100.0% | 100.0% to 100.0% | +100.0 |" in out


def test_an_unknown_answer_is_listed_with_its_run_record_and_statement(two_arms):
    _, out, _, _ = two_arms

    assert "- new run-2, {}, S2 reason: A test holds it still.".format(KEEP) in out.splitlines()


def test_a_statement_the_judge_does_not_answer_is_unknown(source, tmp_path):
    asked = {KEEP: "S1: yes Draft D1", SPLIT: ALL_YES[SPLIT]}

    _, out, _, _ = scored(source, tmp_path, one_run_each(asked))

    assert "- old run-1, {}, S2 reason: A test holds it still.".format(KEEP) in out.splitlines()


def test_the_judge_reads_every_sheet_once_per_held_out_record(two_arms):
    _, _, _, judge = two_arms

    assert sorted((Path(where).parent.name, Path(where).name, title) for where, title in judge.read) == [
        (arm, run, title) for arm, run in (("new", "run-1"), ("new", "run-2"), ("old", "run-1"), ("old", "run-2"))
        for title in ("Keep one Clock", "Split the stores")]


def test_the_judge_is_given_the_decisions_and_questions_of_the_sheet_and_no_other_section(two_arms):
    _, _, _, judge = two_arms
    prompt = judge.asked[0][judge.asked[0].index("-p") + 1]

    assert [part in prompt for part in ("### Draft D1:", "### Question D2:", "### Draft W1:")] == [True, True, False]


def test_the_judge_is_given_the_statements_of_its_record(two_arms):
    _, _, _, judge = two_arms
    prompts = [args[args.index("-p") + 1] for args in judge.asked]

    assert any("S2 (reason): A test holds it still." in prompt and "Spans go to a trace store." not in prompt
               for prompt in prompts)


@pytest.mark.parametrize("writer, alias",[(FABLE, "opus"), (OPUS, "fable")])
def test_the_judge_asked_for_is_the_other_model_from_the_writer(source, tmp_path, writer, alias):
    _, _, _, judge = scored(source, tmp_path, one_run_each(ALL_YES), writers={"old": writer, "new": writer})

    assert {args[args.index("--model") + 1] for args in judge.asked} == {alias}


@pytest.mark.parametrize("line", [
    "- Judge: claude-opus-5-5, asked for as opus",
    "- Writer: claude-fable-5-1",
    "- Old arm: origin/main",
    "- New arm: the working tree",
    "- Claude Code: 2.1.4 (Claude Code) for the runs, 2.1.5 (Claude Code) for the judge",
    "- Dates: runs started 2026-10-20, judged 2026-10-21",
])
def test_the_header_names_what_the_numbers_were_measured_on(two_arms, line):
    _, out, _, _ = two_arms

    assert line in out.splitlines()


def test_the_header_names_the_pin(source, two_arms):
    _, pin, _, _ = source
    _, out, _, _ = two_arms

    assert "- Pin: " + pin in out.splitlines()


def test_two_arms_written_by_different_models_are_refused(source, tmp_path):
    status, out, err, judge = scored(source, tmp_path, one_run_each(ALL_YES), writers={"old": FABLE, "new": OPUS})

    assert (status, out, judge.asked, "old run-1 by " + FABLE in err, "new run-1 by " + OPUS in err) == (
        1, "", [], True, True)


def test_statements_split_on_records_that_no_longer_hash_the_same_are_refused(source, tmp_path):
    _, _, records, _ = source

    status, out, err, judge = scored(source, tmp_path, one_run_each(ALL_YES), split_on="0" * 64)

    assert (status, out, judge.asked, records in err, "0" * 64 in err) == (1, "", [], True, True)


def test_a_run_with_no_sheet_is_listed_as_failed_with_what_its_output_says(two_arms):
    _, out, _, _ = two_arms

    assert "- new run-3 left no Answer sheet. Its output says: The Session stopped at its time cap." in out.splitlines()


def test_a_failed_run_is_never_judged(two_arms):
    _, _, _, judge = two_arms

    assert sorted({Path(where).name for where, _ in judge.read}) == ["run-1", "run-2"]


def test_the_runs_scored_leave_out_the_failed_run(two_arms):
    _, out, _, _ = two_arms

    assert "- Runs scored: old 2, new 2" in out.splitlines()


@pytest.mark.this_repo
def test_git_ignores_the_runs_folder():
    kept = (harness.RUNS / "a-comparison" / "old" / "run-1" / score.SHEET_FILE).relative_to(ROOT).as_posix()

    assert git(ROOT, "check-ignore", kept).strip() == kept
