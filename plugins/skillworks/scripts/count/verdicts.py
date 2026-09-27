# Pure, so each way a report can write a Verdict is proved on a string and never on a run.

from typing import NamedTuple

from count.items import BULLETED, listed_in, text_of

VERDICTS = "### Verdicts"
UNREQUESTED = "### Unrequested"

DONE = "Done"
PARTIAL = "Partial"
MISSING = "Missing"
CONTRADICTS = "Contradicts"
IN_STEP = "In step"
OUT_OF_STEP = "Out of step"

# The longest first, so "Out of step" is never read as a shorter word that opens it.
WORDS = (OUT_OF_STEP, CONTRADICTS, IN_STEP, PARTIAL, MISSING, DONE)

SEPARATOR = ": "

REASON_MARKS = " .:;,-–—"

# A model writes an item in bold or as code as often as bare, and the name is the same item.
NAME_MARKS = " *`"


class Verdict(NamedTuple):
    item: str
    word: str
    reason: str


class Report(NamedTuple):
    # None when the report holds no Verdicts list, which is a different fault from an empty one.
    verdicts: list
    unrequested: list


def subsections_of(report):
    held = {}
    named = None
    for line in report.replace("\r\n", "\n").split("\n"):
        if line.startswith("#"):
            named = line.strip()
            held.setdefault(named, [])
            continue
        if named is not None:
            held[named].append(line)
    return held


def word_opening(said):
    for word in WORDS:
        if said.startswith(word) and not said[len(word):len(word) + 1].isalpha():
            return word
    return ""


# The first colon that a Verdict word follows, so a Surface name may hold a colon of its own.
def verdict_in(line):
    at = line.find(SEPARATOR)
    while at != -1:
        rest = line[at + len(SEPARATOR):]
        word = word_opening(rest)
        if word:
            return Verdict(line[:at].strip(NAME_MARKS), word, rest[len(word):].lstrip(REASON_MARKS))
        at = line.find(SEPARATOR, at + 1)
    return None


def bullets(lines):
    return [text_of(held, 2).strip() for _, held in listed_in(lines, BULLETED)]


def read_verdicts(report):
    held = subsections_of(report)
    verdicts = None
    if VERDICTS in held:
        verdicts = [verdict for verdict in map(verdict_in, bullets(held[VERDICTS])) if verdict]
    unrequested = [said for said in bullets(held.get(UNREQUESTED, []))
                   if said.rstrip(".") != "None"]
    return Report(verdicts, unrequested)
