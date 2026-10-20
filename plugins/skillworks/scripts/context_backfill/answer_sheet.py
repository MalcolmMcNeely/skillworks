# The sheet is the source: a person may edit a Draft in place, so every line is read from it and none from a pass.

import re
from typing import NamedTuple

SHEET_FILE = "answer-sheet.md"

ACCEPT = "accept"
REJECT = "reject"
ASK = "?"
ANSWERS = (ACCEPT, REJECT, ASK)

DRAFT = "Draft"
WORD = "W"
DECISION = "D"
MAP = "M"

# Only these four headings start a section, because the map's own text holds ## headings of its own.
SECTIONS = ("## Words", "## Decisions", "## Questions", "## Thin")
HEADING = re.compile(r"^### (Draft|Question) ([A-Z])(\d+):[ \t]*(.*)$")
EVIDENCE = "Evidence:"
REF_WORDS = ("commit", "issue", "ticket", "pull", "pr", "spec")


class Entry(NamedTuple):
    kind: str
    letter: str
    number: str
    title: str
    answer: str
    context: str
    text: str
    evidence: list
    lines: list

    @property
    def name(self):
        return "{} {}{}: {}".format(self.kind, self.letter, self.number, self.title)

    @property
    def is_draft(self):
        return self.kind == DRAFT

    # The first run writes the map's accept from the talk, so it is not an Answer the person marked.
    @property
    def is_marked(self):
        return bool(self.answer) and not (self.is_draft and self.letter == MAP)


class Section(NamedTuple):
    lines: list
    entries: list


class Sheet(NamedTuple):
    preamble: list
    sections: list

    @property
    def entries(self):
        return [entry for section in self.sections for entry in section.entries]


def field(lines, name):
    for line in lines:
        if line.startswith(name + ":"):
            return line[len(name) + 1:].strip()
    return ""


def entry_of(lines):
    kind, letter, number, title = HEADING.match(lines[0]).groups()
    label = "Answer" if kind == DRAFT else "Reason"
    body = lines[1:]
    evidence_at = next((at for at, line in enumerate(body) if line.strip() == EVIDENCE), len(body))
    text = [line for line in body[:evidence_at]
            if not line.startswith((label + ":", "Context:"))]
    evidence = [line.strip()[2:].strip() for line in body[evidence_at + 1:] if line.strip().startswith("- ")]
    answer = field(body, label)
    return Entry(kind, letter, number, title.strip(), answer.lower() if kind == DRAFT else answer,
                 field(body, "Context"), "\n".join(text).strip("\n"), evidence, lines)


def read_sheet(text):
    preamble, sections = [], []
    entry = None
    for line in text.splitlines():
        if line.rstrip() in SECTIONS:
            sections.append(Section([line], []))
            entry = None
        elif HEADING.match(line) and sections:
            entry = [line]
            sections[-1].entries.append(entry)
        elif entry is not None:
            entry.append(line)
        elif sections:
            sections[-1].lines.append(line)
        else:
            preamble.append(line)
    return Sheet(preamble, [Section(section.lines, [entry_of(lines) for lines in section.entries])
                            for section in sections])


def is_left(entry):
    return entry.answer in ("", ASK) if entry.is_draft else True


# What stays is kept as it was written, so a person's edits to a Draft still waiting survive the rewrite.
def what_is_left(sheet):
    parts = list(sheet.preamble)
    for section in sheet.sections:
        parts += section.lines
        for entry in section.entries:
            if is_left(entry):
                parts += entry.lines
    return "\n".join(parts).rstrip("\n") + "\n"


def bold_name(text, fallback):
    found = re.match(r"^\*\*(.+?)\*\*:", text)
    return found.group(1).strip() if found else fallback


def references(evidence):
    refs = []
    for item in evidence:
        ref = item.split('"', 1)[0].strip().rstrip(":").strip()
        first = ref.split(" ", 1)[0].lower()
        if ref and (first in REF_WORDS or "#" in ref or ref.startswith(".specs/")) and ref not in refs:
            refs.append(ref)
    return refs
