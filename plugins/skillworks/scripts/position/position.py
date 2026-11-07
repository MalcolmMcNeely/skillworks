# The driver writes it and the pane reads it, so these fields are the contract between the two.

import json
import os
from pathlib import Path

POSITION = "position.json"

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


# Renamed into place, so a reader that opens the file between two writes never reads half of one.
def written_whole(path, position):
    path = Path(path)
    beside = path.with_name(path.name + ".tmp")
    beside.write_text(json.dumps(position, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(beside, path)
