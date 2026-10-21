# Both arms are judged in one pass by one judge, so the judge's drift can never read as a change in the skill.

import json
import re
from pathlib import Path
from typing import NamedTuple

import blind_clone
import judge
import statements
import words
from context_backfill.answer_sheet import DECISIONS, SHEET_FILE, read_sheet
from stop import refusal

COMPARISON_FILE = "comparison.json"
OUTPUT_FILE = "output.json"
CLONE_FOLDER = "blind-clone"
ARMS = ("old", "new")
JUDGED_SECTIONS = (DECISIONS, "## Questions")
NONE = "—"


class Run(NamedTuple):
    arm: str
    name: str
    folder: Path
    sheet: str
    output: str

    @property
    def label(self):
        return "{} {}".format(self.arm, self.name)


def read_or_none(path):
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None


def kept_runs(comparison):
    runs = []
    for arm in ARMS:
        folder = comparison / arm
        for run in sorted(path for path in folder.iterdir() if path.is_dir()) if folder.is_dir() else []:
            runs.append(Run(arm, run.name, run, read_or_none(run / SHEET_FILE), read_or_none(run / OUTPUT_FILE)))
    return runs


def what_it_says(run):
    if run.output is None:
        return "nothing, because it left no output"
    held = judge.result_of(run.output)
    said = held["result"] if held and isinstance(held.get("result"), str) else run.output
    return " ".join(said.split()) or "nothing"


def writer_of(sheeted):
    writers = {}
    for run in sheeted:
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


def judged_all(runner, alias, sheeted, records):
    models, judged = set(), []
    for run in sheeted:
        part = judged_part(run.sheet)
        for record, said in records.items():
            model, verdicts = judge.ask(runner, alias, run.folder.as_posix(), said["title"], said["statements"], part)
            models.add(model or "no model named")
            judged.append(Judged(run, record, said["statements"], verdicts))
    return models, judged


def per_run(judged, arm, measure):
    labels = sorted({item.run.name for item in judged if item.run.arm == arm})
    return [measure([item for item in judged if item.run.arm == arm and item.run.name == label]) for label in labels]


def recall(kind, total):
    return lambda items: 100.0 * sum(item.counted(kind) for item in items) / total


def records_found(items):
    return sum(1 for item in items if item.found)


def mean(values):
    return sum(values) / len(values)


def row(name, old, new, shown, spread):
    cells = [name]
    for values in (old, new):
        cells += [shown(mean(values)), "{} to {}".format(spread(min(values)), spread(max(values)))] if values \
            else [NONE, NONE]
    cells.append("{:+.1f}".format(mean(new) - mean(old)) if old and new else NONE)
    return "| " + " | ".join(cells) + " |"


def percent(value):
    return "{:.1f}%".format(value)


def word_row(name, worded, measure, shown, spread):
    old, new = ([measure(drafts) for run, drafts in worded if run.arm == arm] for arm in ARMS)
    return row(name, old, new, shown, spread)


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
def evidence_of(runner, source, comparison, pin, glossaries):
    clone = clone_of(runner, source, comparison, pin)
    return {glossary.context: words.evidenced(runner, clone, glossary) for glossary in glossaries}


def word_rows(worded, glossaries, evidence):
    rows = []
    for glossary in glossaries:
        total = len(glossary.headwords)
        if total:
            rows.append(word_row("Headword recall, {}, of {}".format(glossary.context, total), worded,
                                 lambda drafts: 100.0 * len(words.found(drafts, glossary)) / total, percent, percent))
    for glossary in glossaries:
        if glossary.losing:
            rows.append(word_row("Found under a losing name, " + glossary.context, worded,
                                 lambda drafts: len(words.under_losing_names(drafts, glossary)),
                                 "{:.1f}".format, "{:.0f}".format))
    for glossary in glossaries:
        held = evidence.get(glossary.context, set())
        if held:
            rows.append(word_row("_Avoid_ recall, {}, of {} with evidence".format(glossary.context, len(held)), worded,
                                 lambda drafts: 100.0 * words.avoids_found(drafts, glossary, held) / len(held),
                                 percent, percent))
    rows.append(word_row("General words drafted", worded, lambda drafts: len(words.general(drafts)),
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


def measures(judged, records, worded, glossaries, evidence):
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
    rows += word_rows(worded, glossaries, evidence)
    return "\n".join(rows) + "\n"


def unknowns(judged):
    listed = ["- {}, {}, S{} {}: {}".format(item.run.label, item.record, at, statement["kind"], statement["says"])
              for item in judged
              for at, (statement, verdict) in enumerate(zip(item.statements, item.verdicts), start=1)
              if verdict.answer == judge.UNKNOWN]
    return "## Unknown answers\n\nAn unknown answer counts as no.\n\n" + (
        "\n".join(listed) if listed else "No answer was unknown.") + "\n"


def failures(failed):
    listed = ["- {} left no Answer sheet. Its output says: {}".format(run.label, what_it_says(run))
              for run in failed]
    return "## Failed runs\n\nA failed run counts in no score.\n\n" + (
        "\n".join(listed) if listed else "No run failed.") + "\n"


def header(pin, comparison, writer, alias, models, version, today, sheeted):
    scored = ", ".join("{} {}".format(arm, sum(1 for run in sheeted if run.arm == arm)) for arm in ARMS)
    return "\n".join([
        "# Backfill evals, old against new", "",
        "- Pin: " + pin["commit"],
        "- Old arm: " + str(comparison.get("old", NONE)),
        "- New arm: " + str(comparison.get("new", NONE)),
        "- Writer: " + (writer or NONE),
        "- Judge: {}, asked for as {}".format(" + ".join(sorted(models)) or NONE, alias or NONE),
        "- Claude Code: {} for the runs, {} for the judge".format(comparison.get("claude-code", NONE), version),
        "- Dates: runs started {}, judged {}".format(comparison.get("started", NONE), today),
        "- Runs scored: " + scored,
    ]) + "\n"


def score(runner, source, comparison, pin, folder, today):
    if not comparison.is_dir():
        raise refusal("{} holds no kept runs. Name a comparison folder. Nothing was scored.".format(
            comparison.as_posix()))
    noted = json.loads(read_or_none(comparison / COMPARISON_FILE) or "{}")
    records = held_out(runner, source, pin, folder)
    runs = kept_runs(comparison)
    sheeted = [run for run in runs if run.sheet is not None]
    writer = writer_of(sheeted)
    alias = judge.alias_against(writer) if writer else None
    models, judged = judged_all(runner, alias, sheeted, records) if alias else (set(), [])
    glossaries = words.glossaries(runner, source, pin["commit"])
    worded = [(run, words.drafted(run.sheet)) for run in sheeted]
    evidence = evidence_of(runner, source, comparison, pin, glossaries) \
        if sheeted and any(glossary.losing for glossary in glossaries) else {}
    version = runner.run(["claude", "--version"]).out.strip() or NONE
    return "\n".join([header(pin, noted, writer, alias, models, version, today, sheeted),
                      measures(judged, records, worded, glossaries, evidence), losing_names(worded, glossaries),
                      general_words(worded, glossaries),
                      unknowns(judged), failures([run for run in runs if run.sheet is None])])
