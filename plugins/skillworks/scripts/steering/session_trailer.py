# Read as the hook reads it, so the Keep and the hook never disagree on one repo: anything but hide is show.

import json

from steering.steering_file import LOOP_FILE, steering_root

KEY = "session-trailer"


def session_trailer(top):
    try:
        held = json.loads((steering_root(top) / LOOP_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "show"
    return "hide" if isinstance(held, dict) and held.get(KEY) == "hide" else "show"
