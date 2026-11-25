# A skill reads each Steering file through this script, so a missing file says it is missing in one plain line.

import os
import sys
from pathlib import Path

from layers.layers import LOOP_FILE, STEERING_FOLDER, repo_steering_of
from output.streams import speaking_any_character
from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: steering-file <path>\n"


def sidecar_steering(top):
    sidecar = repo_steering_of(top).sidecar
    return sidecar.root if sidecar else None


def steering_root(top):
    return repo_steering_of(top).steering.root


def top(runner, where):
    found = runner.run(["git", "-C", where, "rev-parse", "--show-toplevel"])
    if found.status != 0:
        raise refusal("{} is not in a git repository.".format(where))
    return found.out.strip()


def folder_files(root, path):
    return sorted(entry.name for entry in Path(root, path).iterdir() if entry.is_file())


def listing(path, names):
    return "".join("{}/{}\n".format(path.rstrip("/"), name) for name in names)


def main(argv, runner, out, err, where=None):
    where = where or os.getcwd()
    try:
        if len(argv) != 1:
            raise misuse(USAGE)
        path = argv[0]
        root = steering_root(top(runner, where))
        on_disk = Path(root, path)
        if on_disk.is_file():
            out.write(on_disk.read_bytes().decode("utf-8"))
        elif on_disk.is_dir():
            out.write(listing(path, folder_files(root, path)))
        else:
            raise refusal("{} is missing.".format(path))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1]))
