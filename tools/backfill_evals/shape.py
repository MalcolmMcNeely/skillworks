# Scored from the Finding alone, because the Answer below it is the harness's own map and would find every context.

import re
from typing import NamedTuple

from context_backfill.context_map import contexts_of

SHAPE_FILE = "shape.md"
FINDING = "## Finding"
HEADING = re.compile(r"^(#{3,})\s+(.*)")
BOLD_LED = re.compile(r"^[-*]\s+\*\*(.+?)\*\*")
TICK_LED = re.compile(r"^[-*]\s+`([^`]+)`")
TICKED = re.compile(r"`([^`]+)`")
POLYSEMY_HEADINGS = ("polysem", "two things", "two meanings")
CALLED_POLYSEMOUS = re.compile(r"`([^`]+)`[^`.]*?\bmeans? two things")
YAML_KEY = re.compile(r"^  ([^\s:][^:]*):\s*$")
LIST_ITEM = re.compile(r"^\s+-\s+(.+?)\s*$")


class Shape(NamedTuple):
    claims: list
    polysemy: set


class RealMap(NamedTuple):
    contexts: dict
    polysemy: set


def folder(token):
    token = token.strip()
    if not token or " " in token:
        return None
    token = token.removeprefix("./")
    for tail in ("/**", "/*", "/"):
        token = token.removesuffix(tail)
    return token.casefold() if token not in ("", ".") else None


def yaml_block(text):
    lines = text.splitlines()
    starts = [at for at, line in enumerate(lines) if line.strip() == "```yaml"]
    if not starts:
        return []
    start = starts[-1] + 1
    end = next((at for at in range(start, len(lines)) if lines[at].strip().startswith("```")), len(lines))
    return lines[start:end]


def map_folders(text):
    named = {name.casefold(): name for name in contexts_of(text)}
    found, context, listing = {}, None, False
    for line in yaml_block(text):
        if line and not line[0].isspace():
            context, listing = None, False
            continue
        key = YAML_KEY.match(line)
        if key:
            context = named.get(key.group(1).strip().casefold(), key.group(1).strip())
            found[context], listing = set(), False
        elif context and line.strip() == "code:":
            listing = True
        elif context and listing and LIST_ITEM.match(line):
            claimed = folder(LIST_ITEM.match(line).group(1).strip("'\""))
            if claimed:
                found[context].add(claimed)
        elif line.strip():
            listing = False
    return {context: folders for context, folders in found.items() if folders}


def real_map(text):
    joined = " ".join((text or "").split())
    return RealMap(map_folders(text or ""), {word.casefold() for word in CALLED_POLYSEMOUS.findall(joined)})


def finding_lines(text):
    lines = (text or "").splitlines()
    if FINDING not in [line.rstrip() for line in lines]:
        return []
    start = [line.rstrip() for line in lines].index(FINDING) + 1
    end = next((at for at in range(start, len(lines)) if lines[at].startswith("## ")), len(lines))
    return lines[start:end]


def read_shape(text):
    claims, polysemy, current, polysemy_level = [], set(), None, None
    for line in finding_lines(text):
        heading = HEADING.match(line)
        if heading:
            level, said = len(heading.group(1)), heading.group(2).strip()
            if polysemy_level is not None and level > polysemy_level:
                polysemy.add(said.strip("`*").casefold())
                continue
            polysemy_level = level if any(mark in said.casefold() for mark in POLYSEMY_HEADINGS) else None
            current = None if polysemy_level is not None else set()
            if current is not None:
                claims.append(current)
            continue
        if polysemy_level is not None:
            named = BOLD_LED.match(line) or TICK_LED.match(line)
            if named:
                polysemy.add(named.group(1).strip().rstrip(":").strip("`").casefold())
            continue
        if BOLD_LED.match(line):
            current = set()
            claims.append(current)
        if current is not None:
            current.update(claimed for claimed in map(folder, TICKED.findall(line)) if claimed)
    return Shape(claims, polysemy)


def claims_folder(claimed, real):
    return any(real == held or real.startswith(held + "/") for held in claimed)


def contexts_found(shape, real):
    return sum(1 for folders in real.contexts.values()
               if any(2 * sum(1 for one in folders if claims_folder(claimed, one)) > len(folders)
                      for claimed in shape.claims))


def polysemy_found(shape, real):
    return len(shape.polysemy & real.polysemy)
