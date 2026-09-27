# One reader, so no script keeps its own idea of the Target branch.

import json
from pathlib import Path

from stop import refusal

LOOP_FILE = "docs/agents/loop.json"


def target_branch(top):
    path = Path(top) / LOOP_FILE
    if not path.is_file():
        raise refusal("{} is missing. Run seed-steering to write it.".format(LOOP_FILE))
    settings = json.loads(path.read_text(encoding="utf-8"))
    if "target-branch" not in settings:
        raise refusal("{} names no target-branch. Add one, such as \"target-branch\": \"main\".".format(LOOP_FILE))
    return settings["target-branch"]
