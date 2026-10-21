import datetime
import json
import os
import sys
from pathlib import Path

import blind_clone
import score
import statements
from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: harness.py score <comparison>\n"

# Git ignores it, because a sheet is 300 KB and a comparison keeps six.
RUNS = blind_clone.HERE / "runs"
TOOLS = ("claude", "git")


def need_tools(runner):
    for tool in TOOLS:
        if not runner.found(tool):
            raise refusal("The scorer needs Claude Code and git, and {} is missing. Install it, then run this "
                          "again. Nothing was scored.".format(blind_clone.TOOL_NAMES.get(tool, tool)))


def main(argv, runner, out, err, where, today, runs=RUNS, pin_file=blind_clone.PIN_FILE,
         statements_folder=statements.FOLDER):
    try:
        argv = [str(a) for a in argv]
        if len(argv) != 2 or argv[0] != "score":
            raise misuse(USAGE)
        need_tools(runner)
        source = blind_clone.must(blind_clone.git(runner, where, "rev-parse", "--show-toplevel"),
                                  "find the repo").strip()
        pin = json.loads(Path(pin_file).read_text(encoding="utf-8"))
        out.write(score.score(runner, source, Path(runs) / argv[1], pin, statements_folder, today))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr, os.getcwd(), datetime.date.today().isoformat()))
