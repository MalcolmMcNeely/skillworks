import json
from pathlib import Path

from runner import PAST_LIMIT

PULL_SECONDS_KEY = "steering-pull-seconds"

DEFAULT_PULL_SECONDS = 30

# The Plugin's hooks file gives the SessionStart hook 300 seconds, and the pull must stop well inside it.
MOST_PULL_SECONDS = 240

# git asks for a password on the terminal, and a run has nobody there to answer it.
NO_PROMPT = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}


# Read from the copy on disk before the pull, because the pull may never come back.
def pull_seconds(loop_file):
    try:
        held = json.loads(Path(loop_file).read_text(encoding="utf-8")).get(PULL_SECONDS_KEY)
    except (OSError, ValueError, AttributeError):
        return DEFAULT_PULL_SECONDS
    return held if is_pull_limit(held) else DEFAULT_PULL_SECONDS


def is_pull_limit(held):
    return not isinstance(held, bool) and isinstance(held, int) and 1 <= held <= MOST_PULL_SECONDS


def has_remote(runner, sidecar):
    listed = runner.run(["git", "-C", Path(sidecar).as_posix(), "remote"])
    return listed.status == 0 and listed.out.strip() != ""


def reason_in(said):
    lines = [line.strip() for line in said.split("\n") if line.strip()]
    for line in lines:
        if line.startswith(("fatal:", "error:")):
            return line
    return lines[-1] if lines else "git gave no reason"


# One warning and never a stop, because a network fault must not keep a run from its work.
def pull_steering(runner, sidecar, loop_file):
    if not has_remote(runner, sidecar):
        return None
    seconds = pull_seconds(loop_file)
    pulled = runner.run(["git", "-C", Path(sidecar).as_posix(), "pull", "--ff-only", "--quiet"],
                        env=NO_PROMPT, limit=seconds)
    if pulled.status == 0:
        return None
    if pulled.status == PAST_LIMIT:
        reason = "ran past its limit of {} {}".format(seconds, "second" if seconds == 1 else "seconds")
    else:
        reason = "failed: " + reason_in(pulled.out + pulled.err)
    return "the pull of the Steering repo into the Sidecar {}. The Steering files on disk are read.".format(reason)


def sidecar_commit(runner, sidecar):
    found = runner.run(["git", "-C", Path(sidecar).as_posix(), "rev-parse", "HEAD"])
    return found.out.strip() if found.status == 0 else None
