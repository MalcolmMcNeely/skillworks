# One reader, so the scripts can never disagree on where a new ADR goes.

from pathlib import Path

from steering.yaml_block import last_yaml_span
from stop import refusal

DOMAIN_FILE = "docs/agents/domain.md"

KEY = "adr-folder"

FIX = "Run /skillworks:skillworks-setup to choose the folder new ADRs go to."

QUOTES = "\"'"


def last_yaml_block(text):
    lines = text.replace("\r\n", "\n").split("\n")
    span = last_yaml_span(lines)
    return None if span is None else lines[span[0]:span[1]]


def folder_or_refusal(top):
    path = Path(top) / DOMAIN_FILE
    if not path.is_file():
        return None, "{} is missing, so no folder is named for new ADRs. {}".format(DOMAIN_FILE, FIX)
    block = last_yaml_block(path.read_text(encoding="utf-8"))
    if block is None:
        return None, "{} has no YAML block at its end, so it names no {}. {}".format(DOMAIN_FILE, KEY, FIX)
    held = next((line for line in block if line.startswith(KEY + ":")), None)
    if held is None:
        return None, "{} names no {}. {}".format(DOMAIN_FILE, KEY, FIX)
    value = held[len(KEY) + 1:].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in QUOTES:
        value = value[1:-1].strip()
    if not value:
        return None, "{} names an empty {}. {}".format(DOMAIN_FILE, KEY, FIX)
    return value, None


def adr_folder(top):
    value, missing = folder_or_refusal(top)
    if missing:
        raise refusal(missing)
    return value


def missing_adr_folder(top):
    return folder_or_refusal(top)[1]
