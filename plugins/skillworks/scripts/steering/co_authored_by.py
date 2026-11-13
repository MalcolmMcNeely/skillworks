# Empty strings, never `false`: Claude Code before v2.1.281 rejects `false` and skips the whole file, allowlist and Plugin with it.
# Each file is edited in place, member by member, so the team's layout and every other key survive.

import json
import re
import sys
from pathlib import Path

from output.streams import speaking_any_character
from runner import Subprocess
from steering.allowlist import member
from steering.target_branch import LOOP_FILE
from stop import Stop, misuse, refusal

USAGE = "usage: set-co-authored-by hide|show\n"

SETTINGS_FILE = ".claude/settings.json"

KEY = "co-authored-by"

# Claude Code's commit credit is always off, because the Plugin's hook adds the credit line itself.
BLOCKS = {"hide": {"commit": "", "pr": ""}, "show": {"commit": ""}}

FIRST_KEY = re.compile(r'\{(\s*)"(?:[^"\\]|\\.)*"(\s*):(\s*)')


def read_object(path, name, missing):
    if not path.is_file():
        if missing is None:
            raise refusal("{} is missing. Run seed-steering to write it. Nothing was written.".format(name))
        return missing, json.loads(missing)
    text = path.read_bytes().decode("utf-8")
    try:
        held = json.loads(text)
    except json.JSONDecodeError:
        raise refusal("{} is not JSON. Nothing was written.".format(name))
    if not isinstance(held, dict):
        raise refusal("{} does not hold a JSON object. Nothing was written.".format(name))
    return text, held


def settle(top, answer):
    loop_path, settings_path = Path(top) / LOOP_FILE, Path(top) / SETTINGS_FILE
    loop_text, loop = read_object(loop_path, LOOP_FILE, None)
    settings_text, settings = read_object(settings_path, SETTINGS_FILE, "{}")
    loop_path.write_bytes(with_member(loop_text, loop, KEY, answer).encode("utf-8"))
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    block = BLOCKS[answer]
    settings_path.write_bytes(with_member(settings_text, settings, "attribution", block).encode("utf-8"))
    said = "wrote {}: {} to {}\n".format(KEY, answer, LOOP_FILE)
    if answer == "hide":
        return said + "wrote an attribution block to {}, with empty strings for commit and pr\n".format(SETTINGS_FILE)
    return said + ("wrote an attribution block to {}, with an empty string for commit, so the Plugin adds the "
                   "credit line and Claude Code's own pull request credit applies\n").format(SETTINGS_FILE)


def with_member(text, held, key, value):
    if not held:
        return json.dumps({key: value}, indent=2) + "\n"
    first = FIRST_KEY.match(text, text.index("{"))
    before_key, before_colon, after_colon = first.groups()
    colon = before_colon + ":" + after_colon
    one_line = "\n" not in before_key
    newline = "\r\n" if "\r\n" in text else "\n"
    indent = "" if one_line else before_key.rsplit("\n", 1)[1]
    comma = ", " if after_colon else ","
    written = rendered(value, colon, comma, one_line, newline, indent)
    if key in held:
        start, end = member(text, text.index("{"), key)
        return text[:start] + written + text[end:]
    close = text.rindex("}")
    after_last_member = len(text[:close].rstrip())
    if one_line:
        return text[:after_last_member] + comma + json.dumps(key) + colon + written + text[after_last_member:]
    added = indent + json.dumps(key) + colon + written
    return text[:after_last_member] + "," + newline + added + text[after_last_member:]


def rendered(value, colon, comma, one_line, newline, indent):
    if not isinstance(value, dict):
        return json.dumps(value)
    members = ['{}{}{}'.format(json.dumps(name), colon, json.dumps(inner)) for name, inner in value.items()]
    if one_line:
        return "{" + comma.join(members) + "}"
    inner_indent = indent * 2
    body = ("," + newline).join(inner_indent + member for member in members)
    return "{" + newline + body + newline + indent + "}"


def main(argv, runner, out, err):
    try:
        if len(argv) != 2 or argv[1] not in BLOCKS:
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
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr))
