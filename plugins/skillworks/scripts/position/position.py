# The driver writes it and the pane reads it, so these fields are the contract between the two.

import json
from datetime import timedelta
from pathlib import Path

POSITION = "position.json"

BASELINE = "baseline"
CUTTING = "cutting"
BUILDING = "building tickets"
FULL_RUN = "full run"
DRIFT_CHECK = "drift check"
NAME_CHECK = "Name check"
FINISHED = "finished"
STOPPED = "stopped"

# Read by the pane in a language of its own, so the form is one any date parser takes.
TIME_FORM = "%Y-%m-%dT%H:%M:%SZ"

# Often enough that a pane reading a heartbeat older than two minutes as gone never misreads a live loop.
HEARTBEAT_SECONDS = 30


def position_time(moment):
    return moment.strftime(TIME_FORM)


# Short, because the write holds the lock both writers share, so a step change waits this long at most.
PATIENCE = timedelta(seconds=1)
TRY_EVERY_SECONDS = 0.05


# Renamed into place, so a reader that opens the file between two writes never reads half of one.
# A failure is handed back and never raised, because a display file must not end a heartbeat or a run.
def written_whole(path, position, replace, clock):
    path = Path(path)
    beside = path.with_name(path.name + ".tmp")
    try:
        beside.write_text(json.dumps(position, indent=2) + "\n", encoding="utf-8", newline="\n")
    except OSError as failed:
        return failed
    began = clock.now()
    while True:
        try:
            replace(beside, path)
            return None
        # Windows refuses a replace while the pane reads the file, and that clears by itself.
        except PermissionError as held:
            if clock.now() - began >= PATIENCE:
                return held
            clock.wait(TRY_EVERY_SECONDS)
        except OSError as failed:
            return failed
