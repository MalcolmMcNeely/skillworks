# Both arms are judged in one pass by one judge, so the judge's drift can never read as a change in the skill.

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

import blind_clone
import citations
import judge
import shape
import statements
import words
from context_backfill.answer_sheet import DECISIONS, SHEET_FILE, read_sheet
from context_backfill.context_map import MAP_FILE
from stop import refusal

COMPARISON_FILE = "comparison.json"
OUTPUT_FILE = "output.json"
QUESTION_FILE = "map-question.json"
CAPPED_FILE = "capped.txt"
CLONE_FOLDER = "blind-clone"
ARMS = ("old", "new")
JUDGED_SECTIONS = (DECISIONS, "## Questions")
NONE = "—"
# A judge call takes about 100 seconds, so six sheets of 51 records asked one at a time take most of a night.
JUDGES_AT_ONCE = 8


class Run(NamedTuple):
    arm: str
    name: str
    folder: Path
    sheet: str
    output: str
    capped: str

    @property
    def label(self):
        return "{} {}".format(self.arm, self.name)

    @property
    def scored(self):
        return self.sheet is not None and self.capped is None

    # Both Sessions of a run, the one that stopped at the map question and the one resumed with the answer.
    def spent(self, key):
        said = [judge.result_of(read_or_none(self.folder / name) or "") or {} for name in (QUESTION_FILE, OUTPUT_FILE)]
        values = [held[key] for held in said if isinstance(held.get(key), (int, float))]
        return sum(values) if values else None


def read_or_none(path):
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None


def kept_runs(comparison):
    runs = []
    for arm in ARMS:
        folder = comparison / arm
        for run in sorted(path for path in folder.iterdir() if path.is_dir()) if folder.is_dir() else []:
            runs.append(Run(arm, run.name, run, read_or_none(run / SHEET_FILE), read_or_none(run / OUTPUT_FILE),
                            read_or_none(run / CAPPED_FILE)))
    return runs


def what_it_says(run):
    if run.output is None:
        return "nothing, because it left no output"
    held = judge.result_of(run.output)
    said = held["result"] if held and isinstance(held.get("result"), str) else run.output
    return " ".join(said.split()) or "nothing"


def writer_of(scored):
    writers = {}
    for run in scored:
        writers.setdefault(judge.main_model(run.output or "") or "no model named", []).append(run.label)
    if len(writers) > 1:
        raise refusal("The sheets were written by more than one model, and a comparison holds one writer, so the "
                      "difference would be the model's and not the skill's: {}. Nothing was scored.".format(
                          "; ".join("{} by {}".format(", ".join(labels), model)
                                    for model, labels in sorted(writers.items()))))
    return next(iter(writers), None)


def held_out(runner, source, pin, folder):
    found = statements.problems(runner, source, pin["commit"], folder)
    if found:
        raise refusal("The Statement files do not fit the records at the pin:\n  {}\nNothing was scored.".format(
            "\n  ".join(found)))
    records = blind_clone.records_hash(runner, source, pin["commit"])
    held = {}
    for record in statements.held_out(runner, source, pin["commit"]):
        said = json.loads((Path(folder) / statements.file_for(record)).read_text(encoding="utf-8"))
        if said["split-on"] != records:
            raise refusal("The held-out records at the pin hash to {}, and {} was split on {}, so its Statements "
                          "are not the records' any more. Split the Statements again. Nothing was scored.".format(
                              records, statements.file_for(record), said["split-on"]))
        held[Path(record).stem] = said
    return held


def judged_part(sheet):
    lines = []
    for section in read_sheet(sheet).sections:
        if section.lines[0].rstrip() in JUDGED_SECTIONS:
            lines += section.lines + [line for entry in section.entries for line in entry.lines]
    return "\n".join(lines).strip("\n") + "\n"


class Judged(NamedTuple):
    run: Run
    record: str
    statements: list
    verdicts: list

    def counted(self, kind):
        return sum(1 for statement, verdict in zip(self.statements, self.verdicts)
                   if statement["kind"] == kind and verdict.counts_for(kind))

    @property
    def found(self):
        return all(verdict.counts_for(statement["kind"]) for statement, verdict in zip(self.statements, self.verdicts)
                   if statement["kind"] == "decision")


def judged_all(runner, alias, scored, records):
    briefs = [(run, judge.write_brief(run.folder, judged_part(run.sheet))) for run in scored]
    asked = [(run, briefed, record, said) for run, briefed in briefs for record, said in records.items()]

    def one(question):
        run, briefed, record, said = question
        model, verdicts = judge.ask(runner, alias, run.folder.as_posix(), briefed, said["title"], said["statements"])
        return model, Judged(run, record, said["statements"], verdicts)

    with ThreadPoolExecutor(max_workers=JUDGES_AT_ONCE) as pool:
        answered = list(pool.map(one, asked))
    return {model or "no model named" for model, _ in answered}, [item for _, item in answered]


def per_run(judged, arm, measure):
    labels = sorted({item.run.name for item in judged if item.run.arm == arm})
    return [measure([item for item in judged if item.run.arm == arm and item.run.name == label]) for label in labels]


def recall(kind, total):
    return lambda items: 100.0 * sum(item.counted(kind) for item in items) / total


def records_found(items):
    return sum(1 for item in items if item.found)


def mean(values):
    return sum(values) / len(values)


def row(name, old, new, shown, spread, change="{:+.1f}"):
    cells = [name]
    for values in (old, new):
        cells += [shown(mean(values)), "{} to {}".format(spread(min(values)), spread(max(values)))] if values \
            else [NONE, NONE]
    cells.append(change.format(mean(new) - mean(old)) if old and new else NONE)
    return "| " + " | ".join(cells) + " |"


def percent(value):
    return "{:.1f}%".format(value)


def run_row(name, kept, measure, shown, spread, change="{:+.1f}"):
    old, new = ([value for value in (measure(held) for run, held in kept if run.arm == arm) if value is not None]
                for arm in ARMS)
    return row(name, old, new, shown, spread, change)


def spent_rows(scored):
    kept = [(run, run) for run in scored]
    return [
        run_row("Run time, minutes", kept, lambda run: None if run.spent("duration_ms") is None
                else run.spent("duration_ms") / 60000, "{:.1f}".format, "{:.0f}".format),
        run_row("Cost at list price, US dollars", kept,lambda run: run.spent("total_cost_usd"),
                "{:.2f}".format, "{:.2f}".format, "{:+.2f}"),
    ]


def clone_of(runner, source, comparison, pin):
    folder = comparison / CLONE_FOLDER
    if not (folder / "repo").is_dir():
        blind_clone.need_tools(runner)
        made = blind_clone.build(runner, source, pin["commit"], folder, pin["commit"])
        if made["tree"] != pin["tree"]:
            raise refusal("The Blind clone's tree hash is {}, and the pin stores {}, so its history is not the one "
                          "the Statements were split on. Mend the scrub rules, or move the pin. Delete {}, then run "
                          "this again. Nothing was scored.".format(made["tree"], pin["tree"], folder.as_posix()))
    return folder / "repo"


# A losing word the clone's history never shows was scrubbed with the records, so no run could have found it.
def evidence_of(runner, clone, glossaries):
    return {glossary.context: words.evidenced(runner, clone, glossary) for glossary in glossaries}


def word_rows(worded, glossaries, evidence):
    rows = []
    for glossary in glossaries:
        total = len(glossary.headwords)
        if total:
            rows.append(run_row("Headword recall, {}, of {}".format(glossary.context, total), worded,
                                lambda drafts: 100.0 * len(words.found(drafts, glossary)) / total, percent, percent))
    for glossary in glossaries:
        if glossary.losing:
            rows.append(run_row("Found under a losing name, " + glossary.context, worded,
                                lambda drafts: len(words.under_losing_names(drafts, glossary)),
                                "{:.1f}".format, "{:.0f}".format))
    for glossary in glossaries:
        held = evidence.get(glossary.context, set())
        if held:
            rows.append(run_row("_Avoid_ recall, {}, of {} with evidence".format(glossary.context, len(held)), worded,
                                lambda drafts: 100.0 * words.avoids_found(drafts, glossary, held) / len(held),
                                percent, percent))
    rows.append(run_row("General words drafted", worded, lambda drafts: len(words.general(drafts)),
                        "{:.1f}".format, "{:.0f}".format))
    return rows


def general_words(worded, glossaries):
    named = {glossary.context.casefold(): glossary.context for glossary in glossaries}
    listed = ["- {}, {}, in {}".format(run.label, draft.name,
                                       named.get(draft.context.casefold(), draft.context or NONE))
              for run, drafts in worded for draft in words.general(drafts)]
    return "## General words\n\nA headword on the harness's list of general programming words.\n\n" + (
        "\n".join(listed) if listed else "No headword is a general word.") + "\n"


def losing_names(worded, glossaries):
    listed = ["- {}, {}, in {}, is a losing name of {}".format(run.label, draft.name, glossary.context, winner)
              for run, drafts in worded for glossary in glossaries
              for draft, winner in words.under_losing_names(drafts, glossary)]
    return "## Found under a losing name\n\nA Draft headed by a losing name is not found.\n\n" + (
        "\n".join(listed) if listed else "No Draft was headed by a losing name.") + "\n"


def shape_rows(shaped, real):
    rows = []
    if real.contexts:
        rows.append(run_row("Contexts found, of {}".format(len(real.contexts)), shaped,
                            lambda found: shape.contexts_found(found, real), "{:.1f}".format, "{:.0f}".format))
    if real.polysemy:
        rows.append(run_row("Polysemy words found, of {}".format(len(real.polysemy)), shaped,
                            lambda found: shape.polysemy_found(found, real), "{:.1f}".format, "{:.0f}".format))
    return rows


def missing_of(history, judged, records):
    held, failed = {}, {}
    for item in judged:
        held.setdefault(item.run, [])
        if item.found:
            continue
        if item.run not in failed:
            failed[item.run] = citations.failed_commits(
                history, read_or_none(item.run.folder / citations.DECISIONS_FILE))
        held[item.run].append((item.record, citations.seen_in(history, records[item.record]["commits"],
                                                              failed[item.run])))
    return list(held.items())


def counted(name, kept, measure):
    return run_row(name, kept, measure, "{:.1f}".format, "{:.0f}".format)


def citation_rows(checked, missing):
    return [
        counted("Cited commits not in the Blind clone", checked, lambda held: len(held.absent)),
        counted("Quotes not in their commit", checked, lambda held: len(held.unquoted)),
        counted("Whys with no citation", checked, lambda held: len(held.uncited)),
        counted("Missing records, seen and dropped", missing, lambda held: sum(1 for _, seen in held if seen)),
        counted("Missing records, never seen", missing, lambda held: sum(1 for _, seen in held if not seen)),
    ]


def listing(title, about, listed, none):
    return "## {}\n\n{}\n\n".format(title, about) + ("\n".join(listed) if listed else none) + "\n"


def citation_lists(checked, missing):
    return "\n".join([
        listing("Cited commits not in the Blind clone", "A commit the history does not hold was invented.",
                ["- {}, {}, cites commit {}, which the Blind clone does not hold".format(run.label, entry.name, short)
                 for run, held in checked for entry, short in held.absent], "Every cited commit is in the clone."),
        listing("Quotes not in their commit", "A quote is searched for in its commit's message and diff, with "
                "line breaks joined.",
                ['- {}, {}, quotes "{}", which commit {} does not hold'.format(run.label, entry.name, quote, short)
                 for run, held in checked for entry, quote, short in held.unquoted],
                "Every quote is in its commit."),
        listing("Whys with no citation", "A decision Draft whose why cites no commit, ticket, spec or code line.",
                ["- {}, {}".format(run.label, entry.name) for run, held in checked for entry in held.uncited],
                "Every why cites its source."),
        listing("Missing records", "A missing record is seen and dropped when a commit it rests on failed a test "
                "in the skill's own list, and never seen otherwise.",
                ["- {}, {}, {}".format(run.label, record, "seen and dropped: commit {} failed a test".format(seen)
                                       if seen else "never seen")
                 for run, held in missing for record, seen in held], "No record is missing."),
    ])


def measures(judged, records, shaped, real, worded, glossaries, evidence, checked, missing, scored):
    kinds = [statement["kind"] for said in records.values() for statement in said["statements"]]
    rows = ["| Measure | Old | Old spread | New | New spread | Difference |", "|---|---|---|---|---|---|"]
    for kind in statements.KINDS:
        total = kinds.count(kind)
        if total:
            measure = recall(kind, total)
            rows.append(row("Statement recall, " + kind, per_run(judged, "old", measure),
                            per_run(judged, "new", measure), percent, percent))
    rows.append(row("Records found, of {}".format(len(records)), per_run(judged, "old", records_found),
                    per_run(judged, "new", records_found), "{:.1f}".format, "{:.0f}".format))
    rows += shape_rows(shaped, real)
    rows += word_rows(worded, glossaries, evidence)
    rows += citation_rows(checked, missing)
    rows += spent_rows(scored)
    return "\n".join(rows) + "\n"


def unknowns(judged):
    listed = ["- {}, {}, S{} {}: {}".format(item.run.label, item.record, at, statement["kind"], statement["says"])
              for item in judged
              for at, (statement, verdict) in enumerate(zip(item.statements, item.verdicts), start=1)
              if verdict.answer == judge.UNKNOWN]
    return "## Unknown answers\n\nAn unknown answer counts as no.\n\n" + (
        "\n".join(listed) if listed else "No answer was unknown.") + "\n"


def failures(failed):
    listed = ["- {} {}. Its output says: {}".format(
        run.label, "left no Answer sheet" if run.capped is None else "hit its time cap of {} minutes".format(
            run.capped.strip()), what_it_says(run)) for run in failed]
    return "## Failed runs\n\nA failed run counts in no score.\n\n" + (
        "\n".join(listed) if listed else "No run failed.") + "\n"


def header(pin, comparison, writer, alias, models, version, today, scored):
    per_arm = ", ".join("{} {}".format(arm, sum(1 for run in scored if run.arm == arm)) for arm in ARMS)
    return "\n".join([
        "# Backfill evals, old against new", "",
        "- Pin: " + pin["commit"],
        "- Old arm: " + str(comparison.get("old", NONE)),
        "- New arm: " + str(comparison.get("new", NONE)),
        "- Writer: " + (writer or NONE),
        "- Judge: {}, asked for as {}".format(" + ".join(sorted(models)) or NONE, alias or NONE),
        "- Claude Code: {} for the runs, {} for the judge".format(comparison.get("claude-code", NONE), version),
        "- Dates: runs started {}, judged {}".format(comparison.get("started", NONE), today),
        "- Runs scored: " + per_arm,
    ]) + "\n"


def score(runner, source, comparison, pin, folder, today):
    if not comparison.is_dir():
        raise refusal("{} holds no kept runs. Name a comparison folder. Nothing was scored.".format(
            comparison.as_posix()))
    noted = json.loads(read_or_none(comparison / COMPARISON_FILE) or "{}")
    records = held_out(runner, source, pin, folder)
    runs = kept_runs(comparison)
    scored = [run for run in runs if run.scored]
    writer = writer_of(scored)
    alias = judge.alias_against(writer) if writer else None
    models, judged = judged_all(runner, alias, scored, records) if alias else (set(), [])
    glossaries = words.glossaries(runner, source, pin["commit"])
    worded = [(run, words.drafted(run.sheet)) for run in scored]
    real = shape.real_map(blind_clone.shown(runner, source, pin["commit"], MAP_FILE))
    shaped = [(run, shape.read_shape(read_or_none(run.folder / shape.SHAPE_FILE))) for run in scored]
    clone = clone_of(runner, source, comparison, pin) if scored else None
    evidence = evidence_of(runner, clone, glossaries) if clone else {}
    history = citations.History(runner, clone)
    checked = [(run, citations.checked(history, run.sheet)) for run in scored]
    missing = missing_of(history, judged, records)
    version = runner.run(["claude", "--version"]).out.strip() or NONE
    return "\n".join([header(pin, noted, writer, alias, models, version, today, scored),
                      measures(judged, records, shaped, real, worded, glossaries, evidence, checked, missing, scored),
                      losing_names(worded, glossaries), general_words(worded, glossaries),
                      citation_lists(checked, missing), unknowns(judged),
                      failures([run for run in runs if not run.scored])])
