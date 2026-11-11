# A skill reads each Steering file through this script, because an Export branch holds none of them on disk.

import os
import sys
from pathlib import Path

from export.export_branch import STEERING
from output.streams import speaking_any_character
from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: steering-file <path>\n"

# Every script builds its Steering paths from this one name, so the folder moves in one line.
STEERING_FOLDER = "docs/skillworks"

# Read as the last fetch left it and never fetched, so a session reads its Steering offline and with no wait.
STEERING_REF = "refs/remotes/origin/" + STEERING


def top(runner, where):
    found = runner.run(["git", "-C", where, "rev-parse", "--show-toplevel"])
    if found.status != 0:
        raise refusal("{} is not in a git repository.".format(where))
    return found.out.strip()


def at_steering(path):
    return "{}:{}".format(STEERING_REF, path)


def paths_in(folder, names):
    return "".join("{}/{}\n".format(folder.rstrip("/"), name) for name in sorted(names))


def disk_folder(root, path):
    return paths_in(path, (entry.name for entry in Path(root, path).iterdir() if entry.is_file()))


def steering_folder(runner, root, path):
    tree = runner.run(["git", "-C", root, "ls-tree", at_steering(path)])
    entries = (line.split("\t", 1) for line in tree.out.splitlines())
    return paths_in(path, (name for kind, name in entries if kind.split()[1] == "blob"))


def from_steering(runner, root, path):
    kind = runner.run(["git", "-C", root, "cat-file", "-t", at_steering(path)])
    if kind.out.strip() == "tree":
        return steering_folder(runner, root, path)
    shown = runner.run(["git", "-C", root, "show", at_steering(path)])
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
        if on_disk.is_file():
            out.write(on_disk.read_bytes().decode("utf-8"))
        elif on_disk.is_dir():
            out.write(disk_folder(root, argv[0]))
        else:
            out.write(from_steering(runner, root, argv[0]))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1]))
