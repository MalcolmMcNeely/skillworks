# A map goes in with the Steering edits that keep the Suite green, and with no other: a banned word is the team's call.

import re
from pathlib import PurePosixPath

from steering.adr_folder import DOMAIN_FILE, adr_folder
from steering.rule_imports import RULES_FOLDER
from steering.steering_file import steering_root
from steering.yaml_block import last_yaml_span
from stop import refusal

MAP_FILE = "CONTEXT-MAP.md"
WORDS_RULE = RULES_FOLDER + "/words.md"
STEERING_FILES = ("CLAUDE.md", "AGENTS.md")
DOMAIN_DOCS = "### Domain docs"
MULTI_CONTEXT = ("Multi-context: `CONTEXT-MAP.md` and `{}/` at the repo root, and one `CONTEXT.md` per "
                 "context. See `" + DOMAIN_FILE + "`.")
CONTEXT_LINE = re.compile(r"^\s*[-*]\s*\[([^\]]+)\]\(([^)\s]+)\)")
LIST_KEY = re.compile(r"^(\s+)([^\s:][^:]*):")


def contexts_of(text):
    found, inside = {}, False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## Contexts"
        elif inside and CONTEXT_LINE.match(line):
            name, path = CONTEXT_LINE.match(line).groups()
            found[name.strip()] = PurePosixPath(path).as_posix().removeprefix("./")
    return found


# Billing on the map and a billing list are one context.
def list_key(name):
    return name.casefold()


def with_empty_lists(rule, names):
    lines = rule.rstrip("\n").split("\n")
    span = last_yaml_span(lines)
    if span is None:
        return None
    start, end = span
    at = next((at for at in range(start, end) if lines[at].startswith("banned-words:")), None)
    if at is None:
        return None
    value = lines[at][len("banned-words:"):].strip()
    if value == "{}":
        lines[at] = "banned-words:"
    elif value:
        return None
    last, indent, held = at, "  ", set()
    for below in range(at + 1, end):
        if lines[below].strip() and not lines[below][0].isspace():
            break
        found = LIST_KEY.match(lines[below])
        if found:
            indent = found.group(1)
            held.add(list_key(found.group(2).strip()))
        if lines[below].strip():
            last = below
    added = ["{}{}: []".format(indent, list_key(name)) for name in names if list_key(name) not in held]
    return "\n".join(lines[:last + 1] + added + lines[last + 1:]) + "\n"


def with_multi_context(steering, folder):
    lines = steering.rstrip("\n").split("\n")
    if DOMAIN_DOCS not in lines:
        return None
    line = MULTI_CONTEXT.format(folder.rstrip("/"))
    heading = lines.index(DOMAIN_DOCS)
    at = next((at for at in range(heading + 1, len(lines)) if lines[at].strip()), None)
    if at is None or lines[at].startswith("#"):
        lines[heading + 1:heading + 1] = ["", line]
    else:
        # A hand-wrapped line runs on below, and a switch of its first line alone would strand the rest.
        end = next((below for below in range(at, len(lines))
                    if not lines[below].strip() or lines[below].startswith("#")), len(lines))
        lines[at:end] = [line]
    return "\n".join(lines) + "\n"


def steering_file(root):
    held = [name for name in STEERING_FILES if (root / name).is_file()]
    return held[0] if held else STEERING_FILES[0]


# Every edit is worked out before any file is written, so a map that cannot be applied leaves the tree as it was.
# The map is a domain doc and goes to the repo, while its Steering edits go wherever the Steering sits.
def map_edits(top, entry):
    contexts = contexts_of(entry.text)
    if not contexts:
        raise refusal("{} names no context under ## Contexts, so it cannot be applied. Mend it on the sheet, then run "
                      "this again. Nothing was written.".format(entry.name))
    root = steering_root(top)
    rule_path = root / WORDS_RULE
    rule = with_empty_lists(rule_path.read_text(encoding="utf-8"), contexts) if rule_path.is_file() else None
    if rule is None:
        raise refusal("The map needs an empty banned-words list for each context, and {} holds no banned-words "
                      "setting this can add to. Run /skillworks:skillworks-setup, then run this again. Nothing "
                      "was written.".format(WORDS_RULE))
    folder = adr_folder(top)
    name = steering_file(root)
    steering_path = root / name
    steering = (with_multi_context(steering_path.read_text(encoding="utf-8"), folder)
                if steering_path.is_file() else None)
    if steering is None:
        raise refusal("The map needs the Domain docs line in {} to say multi-context, and {} has no {} section. "
                      "Run /skillworks:skillworks-setup, then run this again. Nothing was written.".format(
                          name, name, DOMAIN_DOCS))
    return {top / MAP_FILE: entry.text.strip("\n") + "\n", rule_path: rule, steering_path: steering}
