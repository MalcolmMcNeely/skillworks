# A skill writes the allowlist through this script, because Claude Code can turn down a skill's own write to .claude/settings.json.

import json
import sys
from json.decoder import scanstring
from pathlib import Path

from output.streams import speaking_any_character
from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: allow-commands <entry>...\n"

SETTINGS_FILE = ".claude/settings.json"

WHITESPACE = " \t\r\n"

DECODER = json.JSONDecoder()


def settle(top, entries):
    path = Path(top) / SETTINGS_FILE
    text = path.read_bytes().decode("utf-8") if path.is_file() else None
    held = parsed(text)
    allowed = held.get("permissions", {}).get("allow", [])
    asked = list(dict.fromkeys(entries))
    new = [entry for entry in asked if entry not in allowed]
    said = "".join(
        "added {} to permissions.allow in {}\n".format(entry, SETTINGS_FILE) if entry in new
        else "{} is already in permissions.allow in {}\n".format(entry, SETTINGS_FILE)
        for entry in asked)
    if not new:
        return said
    written = with_entries(text, new) if allowed else rewritten(text, held, new)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(written.encode("utf-8"))
    return said


def parsed(text):
    try:
        held = json.loads(text or "{}")
    except json.JSONDecodeError:
        raise refusal("{} is not JSON. Nothing was written.".format(SETTINGS_FILE))
    if not isinstance(held, dict):
        raise refusal("{} does not hold a JSON object. Nothing was written.".format(SETTINGS_FILE))
    if not isinstance(held.get("permissions", {}), dict):
        raise refusal("permissions in {} is not a JSON object. Nothing was written.".format(SETTINGS_FILE))
    if not isinstance(held.get("permissions", {}).get("allow", []), list):
        raise refusal("permissions.allow in {} is not a list. Nothing was written.".format(SETTINGS_FILE))
    return held


def with_entries(text, new):
    permissions, _ = member(text, skip(text, 0), "permissions")
    start, end = member(text, permissions, "allow")
    separator = text[start + 1:skip(text, start + 1)]
    after_last = len(text[:end - 1].rstrip(WHITESPACE))
    added = "".join("," + separator + json.dumps(entry, ensure_ascii=False) for entry in new)
    return text[:after_last] + added + text[after_last:]


def rewritten(text, held, new):
    held.setdefault("permissions", {})["allow"] = new
    newline = "\r\n" if text and "\r\n" in text else "\n"
    return json.dumps(held, indent=2, ensure_ascii=False).replace("\n", newline) + newline


# json.loads keeps the last of two members with one name, so the span is the last one too.
def member(text, opening, key):
    found = None
    at = skip(text, opening + 1)
    while text[at] == '"':
        name, at = scanstring(text, at + 1)
        at = skip(text, skip(text, at) + 1)
        _, end = DECODER.raw_decode(text, at)
        if name == key:
            found = (at, end)
        at = skip(text, end)
        if text[at] == ",":
            at = skip(text, at + 1)
    return found


def skip(text, at):
    while at < len(text) and text[at] in WHITESPACE:
        at += 1
    return at


def main(argv, runner, out, err):
    try:
        if len(argv) < 2:
            raise misuse(USAGE)
        found = runner.run(["git", "-C", argv[0], "rev-parse", "--show-toplevel"])
        if found.status != 0:
            raise refusal("{} is not in a git repository. Nothing was written.".format(argv[0]))
        out.write(settle(found.out.strip(), argv[1:]))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr))
