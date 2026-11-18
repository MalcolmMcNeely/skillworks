# A skill reads each Steering file through this script, so a missing file says it is missing in one plain line.

import os
import sys
from pathlib import Path

from layers.layers import LOOP_FILE, STEERING_FOLDER, repo_steering_of
from layers.remote import remote_of
from output.streams import speaking_any_character
from runner import RUN_VARIABLE, Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: steering-file <path>\n"

# Claude Code sets this in each Session, so every read in one Session finds the commit that Session holds.
SESSION_VARIABLE = "CLAUDE_CODE_SESSION_ID"


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


# A file both Layers hold is one file, the repo's text and then the remote's, so neither replaces the other.
def joined(local, remote):
    if local is None or remote is None:
        return remote if local is None else local
    return local + remote if local.endswith("\n") or not local else local + "\n" + remote


def listing(path, names):
    return "".join("{}/{}\n".format(path.rstrip("/"), name) for name in sorted(set(names)))


def main(argv, runner, out, err, where=None, home=None, session=None, run_commit=None):
    where = where or os.getcwd()
    try:
        if len(argv) != 1:
            raise misuse(USAGE)
        path = argv[0]
        repo = top(runner, where)
        root = steering_root(repo)
        remote = remote_of(runner, repo, home or Path.home(), session, run_commit)
        on_disk = Path(root, path)
        text = joined(on_disk.read_bytes().decode("utf-8") if on_disk.is_file() else None,
                      remote.file(runner, path) if remote else None)
        local_files = folder_files(root, path) if on_disk.is_dir() else None
        remote_files = remote.folder(runner, path) if remote else None
        if remote and remote.warning:
            err.write("WARN  " + remote.warning + "\n")
        if text is not None:
            out.write(text)
        elif local_files is not None or remote_files is not None:
            out.write(listing(path, (local_files or []) + (remote_files or [])))
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
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1], Path.home(),
                  os.environ.get(SESSION_VARIABLE), os.environ.get(RUN_VARIABLE)))
