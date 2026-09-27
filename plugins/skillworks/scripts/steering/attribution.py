# Hiding writes empty strings and never `false`: Claude Code before v2.1.281 rejects `false` and skips the whole file, allowlist and Plugin with it.

import json
import re
import sys
from pathlib import Path

from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: set-attribution hide|show\n"

SETTINGS_FILE = ".claude/settings.json"

ANSWERS = ("hide", "show")

HIDDEN = {"commit": "", "pr": ""}

FIRST_KEY = re.compile(r'\{(\s*)"(?:[^"\\]|\\.)*"(\s*):(\s*)')


def settle(top, answer):
    path = Path(top) / SETTINGS_FILE
    text = path.read_bytes().decode("utf-8") if path.is_file() else "{}"
    try:
        held = json.loads(text)
    except json.JSONDecodeError:
        raise refusal("{} is not JSON. Nothing was written.".format(SETTINGS_FILE))
    if not isinstance(held, dict):
        raise refusal("{} does not hold a JSON object. Nothing was written.".format(SETTINGS_FILE))
    if "attribution" in held:
        return "kept the attribution block in {}, as your team set it\n".format(SETTINGS_FILE)
    if answer == "show":
        return "wrote no attribution block to {}, so Claude Code's own default applies\n".format(SETTINGS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(with_block(text, held).encode("utf-8"))
    return "wrote an attribution block to {}, with empty strings for commit and pr\n".format(SETTINGS_FILE)


def with_block(text, held):
    if not held:
        return json.dumps({"attribution": HIDDEN}, indent=2) + "\n"
    first = FIRST_KEY.match(text, text.index("{"))
    before_key, before_colon, after_colon = first.groups()
    colon = before_colon + ":" + after_colon
    close = text.rindex("}")
    after_last_member = len(text[:close].rstrip())
    if "\n" not in before_key:
        comma = ", " if after_colon else ","
        members = comma.join('"{}"{}""'.format(key, colon) for key in HIDDEN)
        block = '"attribution"{}{{{}}}'.format(colon, members)
        return text[:after_last_member] + comma + block + text[after_last_member:]
    newline = "\r\n" if "\r\n" in text else "\n"
    indent = before_key.rsplit("\n", 1)[1]
    members = ("," + newline).join('{}"{}"{}""'.format(indent * 2, key, colon) for key in HIDDEN)
    block = '{0}"attribution"{1}{{{2}{3}{2}{0}}}'.format(indent, colon, newline, members)
    return text[:after_last_member] + "," + newline + block + text[after_last_member:]


def main(argv, runner, out, err):
    try:
        if len(argv) != 2 or argv[1] not in ANSWERS:
            raise misuse(USAGE)
        found = runner.run(["git", "-C", argv[0], "rev-parse", "--show-toplevel"])
        if found.status != 0:
            raise refusal("{} is not in a git repository. Nothing was written.".format(argv[0]))
        out.write(settle(found.out.strip(), argv[1]))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    sys.stdout.reconfigure(newline="\n")
    sys.stderr.reconfigure(newline="\n")
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr))
