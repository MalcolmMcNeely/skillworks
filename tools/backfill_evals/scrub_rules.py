# git-filter-repo imports this file in its own Python, so it reads only the standard library.
# The banned words come in through the environment, because they are read from the repo at the pin.

import json
import os
import re

BANNED_VARIABLE = "BLIND_CLONE_BANNED_WORDS"

GLOSSARY = "CONTEXT.md"
MAP = "CONTEXT-MAP.md"
ADR_FOLDER = "docs/adr/"
FILLED_STEERING = ("docs/agents/rules/words.md", "docs/agents/domain.md")

# The Statement files say what each record says, so a pin after the harness landed would hand them to the clone.
HARNESS_FOLDER = "tools/backfill_evals/"

PATHS = (GLOSSARY, MAP, ADR_FOLDER, HARNESS_FOLDER) + FILLED_STEERING
PATH_GLOBS = ("*/" + GLOSSARY,)


def is_record(path):
    return path in (GLOSSARY, MAP) or path.startswith(ADR_FOLDER) or path.endswith("/" + GLOSSARY)


RECORD = b"A record\n"
RECORD_LINE = "A line about the records"
RECORD_SUBJECT = re.compile(r"^(ADR|Glossary):")

NAMES_A_RECORD = (
    r"\bglossar(?:y|ies)\b",
    r"\bCONTEXT(?:-MAP)?\.md\b",
    r"\bcontext map\b",
    r"\bADRs?\b",
    r"\badr/",
)

ADR_LINK = re.compile(r"\]\([^)\s]*adr/[0-9]+[^)\s]*\)", re.IGNORECASE)
MISSING_RECORD_LINK = "](records/a-record.md)"
ADR_PATH = re.compile(r"[\w./-]*adr/[0-9]+[\w.-]*", re.IGNORECASE)
ADR_NUMBER = re.compile(r"\bADR[- ]?[0-9]+\b", re.IGNORECASE)
A_RECORD = "a record"

STEERING_FILE = "CLAUDE.md"
MULTI_CONTEXT = re.compile(r"^Multi-context:.*$", re.MULTILINE)
SINGLE_CONTEXT = "Single-context: `CONTEXT.md` and `docs/adr/` at the repo root."


# Matched as the words rule matches a name, so the clone loses every name the check would flag.
def banned_pattern(word):
    joined = r"[ _-]?".join(re.escape(part) for part in word.split())
    return r"(?<![A-Za-z0-9])(?i:" + joined + r")(?![a-z0-9])"


NAMING = re.compile("|".join(NAMES_A_RECORD + tuple(
    banned_pattern(word) for word in json.loads(os.environ.get(BANNED_VARIABLE, "[]")))), re.IGNORECASE)


def message(raw):
    said = raw.decode("utf-8", "replace")
    if RECORD_SUBJECT.match(said):
        return RECORD
    lines = [RECORD_LINE if NAMING.search(line) else line for line in said.split("\n")]
    return "\n".join(lines).encode("utf-8")


def is_steering_file(path):
    return path.rsplit("/", 1)[-1] == STEERING_FILE


def text(path, said):
    said = ADR_LINK.sub(MISSING_RECORD_LINK, said)
    said = ADR_PATH.sub(A_RECORD, said)
    said = ADR_NUMBER.sub(A_RECORD, said)
    if is_steering_file(path):
        said = MULTI_CONTEXT.sub(SINGLE_CONTEXT, said)
    return said


# A blob many commits hold is rewritten once, so every commit that holds it gets the same new id.
rewritten = {}


def file_info(filename, mode, blob_id, value):
    path = filename.decode("utf-8", "replace")
    key = (is_steering_file(path), blob_id)
    if key not in rewritten:
        contents = value.get_contents_by_identifier(blob_id)
        if value.is_binary(contents):
            rewritten[key] = blob_id
        else:
            said = contents.decode("utf-8", "surrogateescape")
            changed = text(path, said)
            rewritten[key] = blob_id if changed == said else value.insert_file_with_contents(
                changed.encode("utf-8", "surrogateescape"))
    return filename, mode, rewritten[key]
