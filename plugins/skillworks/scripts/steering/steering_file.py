# A skill reads each Steering file through this script, because an Export branch holds none of them on disk.

import os
import sys
from pathlib import Path

from export.export_branch import STEERING
from output.streams import speaking_any_character
from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: steering-file <path>\n"

# Read as the last fetch left it and never fetched, so a session reads its Steering offline and with no wait.
STEERING_REF = "refs/remotes/origin/" + STEERING


def top(runner, where):
    found = runner.run(["git", "-C", where, "rev-parse", "--show-toplevel"])
    if found.status != 0:
        raise refusal("{} is not in a git repository.".format(where))
    return found.out.strip()


def steering_copy(runner, root, path):
    shown = runner.run(["git", "-C", root, "show", "{}:{}".format(STEERING_REF, path)])
    if shown.status != 0:
        raise refusal("{} is neither on disk nor on origin/skillworks/steering.".format(path))
    return shown.out


def main(argv, runner, out, err, where=None):
    where = where or os.getcwd()
    try:
        if len(argv) != 1:
            raise misuse(USAGE)
        root = top(runner, where)
        on_disk = Path(root, argv[0])
        out.write(on_disk.read_bytes().decode("utf-8") if on_disk.is_file()
                  else steering_copy(runner, root, argv[0]))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1]))
