# Each command that writes Steering asks here first, so a Steering change never lands on the developer's own branch.

from pathlib import Path

from export.export_branch import STEERING
from steering.target_branch import LOOP_FILE
from stop import refusal


def refuse_on_an_export_branch(top):
    if not (Path(top) / LOOP_FILE).is_file():
        raise refusal("{} is missing on disk, so this branch holds no Steering. With the Export, a Steering "
                      "change is made on {}: switch to it, run this there, and push. Without the Export, run "
                      "seed-steering to write it. Nothing was written.".format(LOOP_FILE, STEERING))
