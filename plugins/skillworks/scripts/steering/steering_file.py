# A skill reads each Steering file through this script, so a missing file says it is missing in one plain line.

import os
import sys
from pathlib import Path

from output.streams import speaking_any_character
from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: steering-file <path>\n"

# Every script builds its Steering paths from this one name, so the folder moves in one line.
STEERING_FOLDER = "docs/skillworks"


def top(runner, where):
    found = runner.run(["git", "-C", where, "rev-parse", "--show-toplevel"])
    if found.status != 0:
        raise refusal("{} is not in a git repository.".format(where))
    return found.out.strip()


def disk_folder(root, path):
    names = (entry.name for entry in Path(root, path).iterdir() if entry.is_file())
    return "".join("{}/{}\n".format(path.rstrip("/"), name) for name in sorted(names))


def main(argv, runner, out, err, where=None):
    where = where or os.getcwd()
    try:
        if len(argv) != 1:
            raise misuse(USAGE)
        root = top(runner, where)
        on_disk = Path(root, argv[0])
        if on_disk.is_file():
            out.write(on_disk.read_bytes().decode("utf-8"))
        elif on_disk.is_dir():
            out.write(disk_folder(root, argv[0]))
        else:
            raise refusal("{} is missing.".format(argv[0]))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1]))
