# Read from what a run already wrote, so a count never pins a model or starts a Session.

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from output.streams import speaking_any_character
from stop import Stop, is_a_number, misuse, refusal

USAGE = "usage: spec-loop-counts [<spec-issue-number>]\n"

RECORDS = ".spec-loop"
JOURNAL = "journal.jsonl"
LOG = "loop.log"

STAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} ")
STOP_WORDS = ("FAIL", "STOP", "RED", "ABORT")


def clone_root(where):
    found = subprocess.run(["git", "-C", str(where), "rev-parse", "--show-toplevel"],
                           capture_output=True, encoding="utf-8", errors="replace")
    if found.returncode != 0:
        raise refusal("{} is not a git worktree.".format(Path(where).as_posix()))
    return Path(found.stdout.strip())


# A folder with no Journal holds a run from before the Journal, which has nothing to count.
def spec_folders(root, spec):
    records = root / RECORDS
    if spec:
        folder = records / spec
        if not (folder / JOURNAL).is_file():
            raise refusal("spec {} has no Journal at {}.".format(spec, (folder / JOURNAL).as_posix()))
        return [folder]
    found = sorted((folder for folder in records.glob("*") if (folder / JOURNAL).is_file()),
                   key=lambda folder: (len(folder.name), folder.name))
    if not found:
        raise refusal("no spec folder under {} holds a Journal.".format(records.as_posix()))
    return found


def entries(folder):
    text = (folder / JOURNAL).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.split("\n") if line.strip()]


def stop_words(folder):
    held = folder / LOG
    lines = held.read_text(encoding="utf-8").split("\n") if held.is_file() else []
    counted = dict.fromkeys(STOP_WORDS, 0)
    for line in lines:
        words = STAMP.sub("", line).split(" ", 1)
        if words[0] in counted:
            counted[words[0]] += 1
    return counted


class Step:
    def __init__(self):
        self.results = 0
        self.nudges = {}
        self.blocked = 0
        self.choices = 0
        self.hand_checks = 0


# A run of a step is its first result and the answers to its Nudges, and a rerun starts another.
def step_runs(journal):
    runs = []
    open_runs = {}
    for entry in journal:
        key = (entry.get("ticket"), entry.get("spec_step"), entry["step"])
        if entry["attempt"] == 0 or key not in open_runs:
            open_runs[key] = []
            runs.append(open_runs[key])
        open_runs[key].append(entry)
    return runs


def how_steps_ended(journal):
    steps = {}
    for run in step_runs(journal):
        step = steps.setdefault(run[0]["step"], Step())
        # A Nudge is sent for what the result before it failed, so that result names its checks.
        for nudged in run[:-1]:
            for check in nudged.get("failed") or []:
                step.nudges[check] = step.nudges.get(check, 0) + 1
        for entry in run:
            step.results += 1
            step.blocked += 1 if entry.get("blocked") else 0
            step.choices += len(entry.get("choices") or [])
            step.hand_checks += len(entry.get("hand_checks") or [])
    return steps


def markdown(header, rows):
    said = "| " + " | ".join(header) + " |\n"
    said += "|" + "|".join("---" for _ in header) + "|\n"
    return said + "".join("| " + " | ".join(str(cell) for cell in row) + " |\n" for row in rows)


def named_counts(counted):
    return ", ".join("{} {}".format(name, n) for name, n in counted.items()) or "none"


def steps_table(journal, stops):
    rows = [(name, step.results, named_counts(step.nudges), step.blocked, step.choices,
             step.hand_checks) for name, step in how_steps_ended(journal).items()]
    said = "## How steps ended\n\n"
    said += markdown(("Step", "Results", "Nudges", "Blocked", "Choices", "Hand checks"), rows)
    return said + "\nLog lines: " + named_counts(stops) + "\n"


class Nudged:
    def __init__(self):
        self.nudged = 0
        self.passed = 0
        self.blocked = 0
        self.failed = 0


def nudges_table(journal):
    steps = {}
    for run in step_runs(journal):
        if len(run) == 1:
            continue
        entry = run[-1]
        step = steps.setdefault(entry["step"], Nudged())
        step.nudged += 1
        if entry.get("blocked"):
            step.blocked += 1
        elif entry.get("status") == 0 and entry.get("failed") == []:
            step.passed += 1
        else:
            step.failed += 1
    said = "## What a Nudge got\n\n"
    if not steps:
        return said + "No step was Nudged.\n"
    return said + markdown(("Step", "Nudged", "Passed", "Blocked", "Failed"), [
        (name, step.nudged, step.passed, step.blocked, step.failed)
        for name, step in steps.items()])


# A result that is not JSON was kept as raw text, so it holds no field to read.
def result_field(entry, name):
    result = entry.get("result")
    return result.get(name) if isinstance(result, dict) else None


def denials_table(journal):
    held = Counter()
    tools = {}
    for entry in journal:
        denied = [denial for denial in result_field(entry, "permission_denials") or []
                  if isinstance(denial, dict)]
        if not denied:
            continue
        held[entry["step"]] += 1
        tools.setdefault(entry["step"], Counter()).update(
            denial.get("tool_name", "an unnamed tool") for denial in denied)
    said = "## Denials\n\n"
    if not held:
        return said + "No result held a Denial.\n"
    return said + markdown(("Step", "Results with a Denial", "Denied calls"), [
        (step, n, named_counts(dict(sorted(tools[step].items())))) for step, n in held.items()])


NO_MODEL = "none named"


# Named as the result names them, so a run under two models never reads as either one alone.
def models_table(journal):
    models = Counter()
    for entry in journal:
        usage = result_field(entry, "modelUsage")
        models[" + ".join(sorted(usage)) if isinstance(usage, dict) and usage else NO_MODEL] += 1
    return "## Which model ran\n\n" + markdown(("Model", "Results"), sorted(models.items()))


def counts(folders):
    journal = [entry for folder in folders for entry in entries(folder)]
    stops = dict.fromkeys(STOP_WORDS, 0)
    for folder in folders:
        for word, n in stop_words(folder).items():
            stops[word] += n
    said = "Specs counted: {}\n\n".format(", ".join(folder.name for folder in folders))
    return said + "\n".join((steps_table(journal, stops), nudges_table(journal),
                             denials_table(journal), models_table(journal)))


def main(argv, out, err, where):
    try:
        if len(argv) > 1 or (argv and not is_a_number(argv[0])):
            raise misuse(USAGE)
        out.write(counts(spec_folders(clone_root(where), argv[0] if argv else "")))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], sys.stdout, sys.stderr, sys.argv[1]))
