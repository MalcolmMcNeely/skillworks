# Pure, so each fault in a spec's shape is proved on a string and never on a run.

import re
from typing import NamedTuple

STORIES = "## User Stories"
DECISIONS = "## Implementation Decisions"
SURFACES = "## Surfaces"

FENCE = "```"

NUMBERED = re.compile(r"(\d+)\. (.*)")
BULLETED = re.compile(r"[-*] (.*)")
BOLD_NAME = re.compile(r"\*\*(.+?)\*\*")


class Item(NamedTuple):
    name: str
    text: str


class Items(NamedTuple):
    stories: list
    decisions: list
    surfaces: list
    faults: list

    def every(self):
        return self.stories + self.decisions + self.surfaces


# A heading inside a fence belongs to an example, so it never opens or ends a section.
def sections_of(spec):
    held = {}
    named = None
    fenced = False
    for line in spec.replace("\r\n", "\n").split("\n"):
        if line.startswith(FENCE):
            fenced = not fenced
        elif line.startswith("## ") and not fenced:
            named = line.strip()
            held.setdefault(named, [])
            continue
        if named is not None:
            held[named].append(line)
    return held


# An indented line carries on the item above it, so a nested list is part of its item.
def listed_in(lines, opener):
    found = []
    carried = None
    fenced = False
    for line in lines:
        if line.lstrip().startswith(FENCE):
            fenced = not fenced
            continue
        if fenced or not line.strip():
            continue
        opened = opener.fullmatch(line.rstrip())
        if opened:
            carried = [line.rstrip()]
            found.append((opened, carried))
        elif line[:1].isspace() and carried is not None:
            carried.append(line.strip())
        else:
            carried = None
    return found


def text_of(lines, dropped):
    return " ".join([lines[0][dropped:]] + lines[1:])


def numbered(heading, lines, mark):
    found = listed_in(lines, NUMBERED)
    if not found:
        return [], "{} holds no numbered list".format(heading)
    items = []
    for at, (opened, held) in enumerate(found, start=1):
        number = int(opened.group(1))
        if number != at:
            return [], number_fault(heading, at, number)
        items.append(Item("{}{}".format(mark, number), text_of(held, len(opened.group(1)) + 2)))
    return items, ""


def number_fault(heading, expected, found):
    if expected == 1:
        return "{} starts at {}, not 1".format(heading, found)
    if found < expected:
        return "{} repeats {}".format(heading, found)
    return "{} skips {}: it goes from {} to {}".format(heading, expected, expected - 1, found)


def surfaced(lines):
    said = " ".join(line.strip() for line in lines if line.strip())
    if said.rstrip(".") == "None":
        return [], ""
    found = listed_in(lines, BULLETED)
    if not found:
        return [], "{} holds no Surface item and does not say None".format(SURFACES)
    items = []
    for opened, held in found:
        text = text_of(held, 2)
        name = BOLD_NAME.match(opened.group(1))
        if name is None:
            return [], "a Surface item under {} opens with no bold name: {}".format(
                SURFACES, held[0])
        if name.group(1) in [item.name for item in items]:
            return [], "{} names {} twice".format(SURFACES, name.group(1))
        items.append(Item(name.group(1), text))
    return items, ""


def read_items(spec):
    held = sections_of(spec)
    faults = []
    read = []
    for heading, reader in ((STORIES, lambda lines: numbered(STORIES, lines, "S")),
                            (DECISIONS, lambda lines: numbered(DECISIONS, lines, "D")),
                            (SURFACES, surfaced)):
        if heading not in held:
            faults.append("the spec has no {} heading".format(heading))
            read.append([])
            continue
        items, fault = reader(held[heading])
        if fault:
            faults.append(fault)
        read.append(items)
    return Items(*read, faults)
