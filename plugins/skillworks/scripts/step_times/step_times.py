# The driver writes it and the pane reads it, so these fields are the contract between the two.

import json
from pathlib import Path

from position.position import position_time

STEP_TIMES = "step-times.jsonl"


# Added to and never written over, so a spec that stops and starts again keeps every start's pieces.
def kept(folder, name, ticket, run, started, ended):
    entry = {"name": name, "ticket": ticket, "run": run,
             "started": position_time(started), "ended": position_time(ended)}
    with (Path(folder) / STEP_TIMES).open("a", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(entry) + "\n")
