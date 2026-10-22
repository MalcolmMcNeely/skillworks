# A model recognises its own text and prefers it, so the judge is always the other model from the writer.

import json
import re
from pathlib import Path
from typing import NamedTuple

from runner import session_changes
from stop import refusal

YES, NO, UNKNOWN = "yes", "no", "unknown"
OTHER = {"opus": "fable", "fable": "opus"}

# The judge reasons before it answers, so the last line it gives for a Statement is its answer.
ANSWER = re.compile(r"^\W*S(\d+)\W*:\s*(yes|no|unknown)\b[ \t,.:;-]*(.*)$", re.IGNORECASE | re.MULTILINE)
QUESTION = re.compile(r"\bQuestion\b", re.IGNORECASE)

# A sheet is longer than Windows allows a command line, so it reaches the judge in a file.
BRIEF_FILE = "judge-brief.md"

BRIEF = """You judge whether an Answer sheet holds what one decision record says.

The sheet below holds Drafts of decision records and Questions. A Question is a decision the sheet
found and could not explain, so a Question holds the decision it names, and never a reason for it.

{sheet}"""

PROMPT = """The record is "{title}". It is split into Statements, each tagged with its kind:

{statements}

First name the record's core choice: the one or two decision Statements its title states. Find the
Drafts and Questions that make that choice, if any do. They make the core choice only when, alone or
together, they hold each of those Statements themselves, and a Draft about the same part of the code
that makes some other choice does not. Then reason about each Statement in turn.

A decision Statement is held when a Draft or Question makes the same choice, in any words and with
less detail. A number, a name, a file, an example or a step the Statement adds need not be on the
sheet when the choice it belongs to is.

The record's other decision Statements are parts of its core choice: what the choice leaves as it
was, what else changes to fit it, how it is carried out or checked, and what would change it later.
When the sheet makes the core choice, the Draft or Question that makes it holds each of these parts
too, unless the sheet makes another choice for that part. A record is a choice at one time, and the
sheet tells the history to now: a change the sheet tells as made later, in place of a part, is that
part's later history and not another choice, so the part is still held. The record's status
Statements tell what changed after it, so a part the sheet chooses otherwise is later history too
when a status Statement tells that change.

A decision Statement is not held when the sheet makes another choice, or makes no Draft or Question
of the record's core choice.

A reason, rejected or status Statement is held only when a Draft says the same thing, in any words.
A Draft that says something near it but not the same does not hold it, and a Question holds none.

Then end your answer with one line per Statement, and nothing after them, in this form:

S1: yes Draft D3
S2: no
S3: unknown

Answer yes and name the Draft or Question that holds the Statement, no when nothing on the sheet holds
it, and unknown when you cannot tell.
"""


class Verdict(NamedTuple):
    answer: str
    holder: str

    def counts_for(self, kind):
        return self.answer == YES and (kind == "decision" or not QUESTION.search(self.holder))


# Claude Code writes its JSON on stdout and a warning, such as one about a folder nobody has trusted, on
# stderr, and a run keeps both in one file, so the JSON is read from where it starts and what follows it is
# left alone.
def result_of(said):
    decoder = json.JSONDecoder()
    for start in (found.start() for found in re.finditer(r"^\{", said, re.MULTILINE)):
        try:
            held, _ = decoder.raw_decode(said, start)
        except ValueError:
            continue
        if isinstance(held, dict):
            return held
    return None


# Subagents run on smaller models, so the model that wrote the most is the one that answered.
def main_model(said):
    usage = (result_of(said) or {}).get("modelUsage")
    if not isinstance(usage, dict) or not usage:
        return None
    return max(usage, key=lambda model: (usage[model] or {}).get("outputTokens", 0))


def family(model):
    return next((name for name in OTHER if name in model.lower()), None)


def alias_against(writer):
    named = family(writer)
    if named is None:
        raise refusal("The sheets were written by {}, and a judge is the other of Opus and Fable, so no judge "
                      "can read them. Nothing was scored.".format(writer))
    return OTHER[named]


def verdicts(said, count):
    found = {int(number): Verdict(answer.lower(), holder.strip()) for number, answer, holder in ANSWER.findall(said)}
    return [found.get(number, Verdict(UNKNOWN, "")) for number in range(1, count + 1)]


def write_brief(folder, sheet):
    path = Path(folder) / BRIEF_FILE
    path.write_text(BRIEF.format(sheet=sheet), encoding="utf-8")
    return path


def prompt_for(title, statements):
    listed = "\n".join("S{} ({}): {}".format(at, statement["kind"], statement["says"])
                       for at, statement in enumerate(statements, start=1))
    return PROMPT.format(title=title, statements=listed)


def ask(runner, alias, where, briefed, title, statements):
    ran = runner.run(["claude", "-p", prompt_for(title, statements), "--model", alias,
                      "--system-prompt-file", Path(briefed).as_posix(),
                      "--output-format", "json", "--tools", "", "--no-session-persistence"],
                     where, session_changes())
    held = result_of(ran.out)
    if ran.status != 0 or held is None or not isinstance(held.get("result"), str):
        raise refusal("The judge gave no answer for \"{}\" in {}. It said:\n{}".format(
            title, where, (ran.out + ran.err).rstrip("\n")))
    return main_model(ran.out), verdicts(held["result"], len(statements))
