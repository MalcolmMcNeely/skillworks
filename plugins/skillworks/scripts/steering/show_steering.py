import json
import os
import sys
from pathlib import Path

from output.streams import speaking_any_character
from runner import Subprocess
from steering.steering_file import top
from stop import Stop

STEPS_FILE = Path(__file__).with_name("steps.json")

HOW_TO = "Name a step to see the Steering it reads: show-steering <step>\n"

STEP_MAP = "https://github.com/MalcolmMcNeely/skillworks/blob/main/docs/usage/the-loop/step-map.md"


def steps():
    return json.loads(STEPS_FILE.read_text(encoding="utf-8"))["steps"]


def step_list(all_steps):
    width = max(len(step["name"]) for step in all_steps) + 2
    lines = [HOW_TO]
    stage = None
    for step in all_steps:
        if step["stage"] != stage:
            stage = step["stage"]
            lines.append("\n{}\n".format(stage[0].upper() + stage[1:]))
        lines.append("  {}{}\n".format(step["name"].ljust(width), step["description"]))
    lines.append("\nThe step map: {}\n".format(STEP_MAP))
    return "".join(lines)


def main(argv, runner, out, err, where=None):
    where = where or os.getcwd()
    try:
        top(runner, where)
        all_steps = steps()
        if argv and argv[0] not in {step["name"] for step in all_steps}:
            out.write("{} is not a step.\n\n".format(argv[0]) + step_list(all_steps))
            return 1
        out.write(step_list(all_steps))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1]))
