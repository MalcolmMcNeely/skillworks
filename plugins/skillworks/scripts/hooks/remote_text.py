# The SessionStart hook reads the remote through this script, so the hook and steering-file never read different text.

import json
import sys
from pathlib import Path

from layers.remote import remote_of
from output.streams import speaking_any_character
from runner import Subprocess
from steering.steering_file import top
from stop import Stop, misuse

USAGE = "usage: remote_text <folder> <session> <path>...\n"


def main(argv, runner, out, err, home):
    try:
        if len(argv) < 2:
            raise misuse(USAGE)
        where, session, paths = argv[0], argv[1], argv[2:]
        remote = remote_of(runner, top(runner, where), home, session)
        if remote is None:
            out.write(json.dumps({"remote": None}))
            return 0
        out.write(json.dumps({"remote": {
            "label": remote.label,
            "warning": remote.warning,
            "files": {path: remote.file(runner, path) for path in paths},
        }}))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr, Path.home()))
