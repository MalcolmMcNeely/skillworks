# Hiding writes empty strings and never `false`: Claude Code before v2.1.281 rejects `false` and skips the whole file, allowlist and Plugin with it.

import json
import sys
from pathlib import Path

from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: set-attribution hide|show\n"

SETTINGS_FILE = ".claude/settings.json"

ANSWERS = ("hide", "show")

HIDDEN = {"commit": "", "pr": ""}


def settle(top, answer):
    path = Path(top) / SETTINGS_FILE
    try:
        held = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except json.JSONDecodeError:
        raise refusal("{} is not JSON. Nothing was written.".format(SETTINGS_FILE))
    if "attribution" in held:
        return "kept the attribution block in {}, as your team set it\n".format(SETTINGS_FILE)
    if answer == "show":
        return "wrote no attribution block to {}, so Claude Code's own default applies\n".format(SETTINGS_FILE)
    held["attribution"] = dict(HIDDEN)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(held, indent=2) + "\n", encoding="utf-8", newline="\n")
    return "wrote an attribution block to {}, with empty strings for commit and pr\n".format(SETTINGS_FILE)


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
