# A model recognises its own text and prefers it, so the judge is always the other model from the writer.

import json
import re
from typing import NamedTuple

from runner import session_changes
from stop import refusal

YES, NO, UNKNOWN = "yes", "no", "unknown"
OTHER = {"opus": "fable", "fable": "opus"}

# The judge reasons before it answers, so the last line it gives for a Statement is its answer.
ANSWER = re.compile(r"^\W*S(\d+)\W*:\s*(yes|no|unknown)\b[ \t,.:;-]*(.*)$", re.IGNORECASE | re.MULTILINE)
QUESTION = re.compile(r"\bQuestion\b", re.IGNORECASE)

PROMPT = """You judge whether an Answer sheet holds what one decision record says.

The record is "{title}". It is split into Statements, each tagged with its kind:

{statements}

The sheet below holds Drafts of decision records and Questions. A Question is a decision the sheet
found and could not explain, so a Question holds the decision it names, and never a reason for it.

{sheet}

For each Statement, first reason about whether one Draft or Question says the same thing, in any
words. A Draft or Question that says something near it but not the same does not hold it. Then end
your answer with one line per Statement, and nothing after them, in this form:

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


def result_of(said):
    try:
        held = json.loads(said)
    except ValueError:
        return None
    return held if isinstance(held, dict) else None


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


def prompt_for(title, statements, sheet):
    listed = "\n".join("S{} ({}): {}".format(at, statement["kind"], statement["says"])
                       for at, statement in enumerate(statements, start=1))
    return PROMPT.format(title=title, statements=listed, sheet=sheet)


def ask(runner, alias, where, title, statements, sheet):
    ran = runner.run(["claude", "-p", prompt_for(title, statements, sheet), "--model", alias,
                      "--output-format", "json", "--tools", "", "--no-session-persistence"],
                     where, session_changes())
    held = result_of(ran.out)
    if ran.status != 0 or held is None or not isinstance(held.get("result"), str):
        raise refusal("The judge gave no answer for \"{}\" in {}. It said:\n{}".format(
            title, where, (ran.out + ran.err).rstrip("\n")))
    return main_model(ran.out), verdicts(held["result"], len(statements))
