# The block is built here and not by the agent, so two runs on one repo give the same block.

import os
import sys
from pathlib import Path

from context_backfill.context_map import MULTI_CONTEXT, steering_file
from output.streams import speaking_any_character
from runner import Subprocess
from seeds import merge
from seeds.answers import took_an_answer
from seeds.outcome import ASKS, BASES, Outcome, report
from steering.adr_folder import DOMAIN_FILE
from steering.rule_imports import RULES_FOLDER
from steering.steering_file import STEERING_FOLDER, sidecar_steering
from steering.target_branch import LOOP_FILE
from stop import Stop, misuse, refusal

USAGE = ("usage: seed-agent-skills --tracker github|files --adr-folder <folder> --contexts single|multi "
         "[--keep <file>:<overlap>=yours|seed]... [--blend <file>:<overlap>=<blend file>]... [--settled <file>]\n")

HEADING = "## Agent skills"

BASE_NAME = "agent-skills.md"

TRACKERS = {
    "github": ("GitHub Issues, driven by the `gh` CLI. A spec is a parent issue; its tickets are its sub-issues. "
               "See `{}/issue-tracker.md`.".format(STEERING_FOLDER)),
    "files": ("Files in `.specs/` in the Sidecar, one folder per spec and one file per ticket. "
              "See `{}/issue-tracker.md`, under The files Tracker.".format(STEERING_FOLDER)),
}

SINGLE_CONTEXT = "Single-context: `CONTEXT.md` and `{}/` at the repo root. See `" + DOMAIN_FILE + "`."

DOMAIN_DOCS = {"single": SINGLE_CONTEXT, "multi": MULTI_CONTEXT}

BLOCK = """{heading}

### Issue tracker

{tracker}

### Domain docs

{domain}

### Steering

The rules in `{rules}/`, the review files in `{steering}/`, and the Suite in `{steering}/suite.json`. The team owns them.

### Rules

The rules load into every session through these imports. Each one lives in `{rules}/`.

{imports}"""


def built(top, tracker, folder, contexts):
    rules = sorted(path.name for path in (top / RULES_FOLDER).glob("*.md") if path.is_file())
    return BLOCK.format(heading=HEADING, tracker=TRACKERS[tracker], rules=RULES_FOLDER, steering=STEERING_FOLDER,
                        domain=DOMAIN_DOCS[contexts].format(folder.rstrip("/")),
                        imports="".join("@{}/{}\n".format(RULES_FOLDER, rule) for rule in rules))


class Split:
    def __init__(self, before, block, gap, after):
        self.before = before
        self.block = block
        self.gap = gap
        self.after = after

    def with_block(self, block):
        if self.block is not None:
            return self.before + block + self.gap + self.after
        if not self.before:
            return block
        return self.before.rstrip("\n") + "\n\n" + block


def split_at_block(text):
    lines = text.splitlines(keepends=True)
    start = next((at for at, line in enumerate(lines) if line.rstrip() == HEADING), None)
    if start is None:
        return Split(text, None, "", "")
    end = next((at for at in range(start + 1, len(lines)) if lines[at].startswith("## ")), len(lines))
    last = end
    while last > start + 1 and not lines[last - 1].strip():
        last -= 1
    block = "".join(lines[start:last])
    if not block.endswith("\n"):
        block += "\n"
    return Split("".join(lines[:start]), block, "".join(lines[last:end]), "".join(lines[end:]))


def weigh(top, wanted, choices, settled):
    place = steering_file(top)
    target = top / place
    base = top / BASES / BASE_NAME
    text = target.read_text(encoding="utf-8") if target.is_file() else ""
    split = split_at_block(text)
    was = base.read_text(encoding="utf-8") if base.is_file() else None
    chosen = {number: choice for (where, number), choice in choices.items() if where == place}
    weighed = merge.weigh(place, was, split.block, wanted, chosen, place in settled)
    unused = sorted(choice for choice in choices if choice[0] != place or choice[1] not in weighed.used)
    if unused:
        raise refusal("{}:{} names no overlap. Nothing was written.".format(*unused[0]))
    if settled and not (weighed.allows_settled and settled == {place}):
        raise refusal("{} is not a file whose block differs from its seed with no base copy. Nothing was written."
                      .format(sorted(settled)[0]))
    writes = []
    if weighed.text is not None:
        writes.append((target, split.with_block(weighed.text)))
    if weighed.base is not None:
        writes.append((base, weighed.base))
    return Outcome(weighed.done, weighed.would, shown=weighed.shown, writes=writes, asks=ASKS.get(weighed.asks))


def parsed(argv):
    answers, choices, settled = {}, {}, set()
    rest = iter(argv)
    for arg in rest:
        if arg in ("--tracker", "--adr-folder", "--contexts") and arg not in answers:
            answers[arg] = next(rest, "")
        elif not took_an_answer(arg, rest, choices, settled, USAGE):
            raise misuse(USAGE)
    tracker, folder, contexts = (answers.get(key, "") for key in ("--tracker", "--adr-folder", "--contexts"))
    if tracker not in TRACKERS or contexts not in DOMAIN_DOCS or not folder.strip() or folder.startswith("--"):
        raise misuse(USAGE)
    return tracker, folder.strip(), contexts, choices, settled


def main(argv, runner, out, err, where=None):
    where = where or os.getcwd()
    try:
        tracker, folder, contexts, choices, settled = parsed(argv)
        found = runner.run(["git", "-C", where, "rev-parse", "--show-toplevel"])
        if found.status != 0:
            raise refusal("{} is not in a git repository. Nothing was written.".format(where))
        sidecar = sidecar_steering(found.out.strip())
        root = sidecar or Path(found.out.strip())
        if not (root / LOOP_FILE).is_file():
            raise refusal("{} is missing. Run seed-steering to write it. Nothing was written.".format(LOOP_FILE))
        if sidecar and tracker != "files":
            raise refusal("the Sidecar holds {}, so Sidecar Steering is on, and no issue on the other team's GitHub "
                          "may show Skillworks. Give --tracker files. Nothing was written.".format(LOOP_FILE))
        report([weigh(root, built(root, tracker, folder, contexts), choices, settled)], "", out)
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1]))
