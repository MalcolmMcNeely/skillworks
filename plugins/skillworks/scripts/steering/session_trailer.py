# Read as the hook reads it, so the Keep and the hook never disagree on one repo: anything but hide is show.

import json
from pathlib import Path

from steering.target_branch import LOOP_FILE

KEY = "session-trailer"


def session_trailer(top):
    try:
        held = json.loads((Path(top) / LOOP_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "show"
    return "hide" if isinstance(held, dict) and held.get(KEY) == "hide" else "show"
