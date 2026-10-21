import datetime
import json
import os
import sys
from pathlib import Path

import blind_clone
import compare
import score
import statements
from stop import Stop, misuse, refusal

USAGE = "usage: harness.py compare [<old ref> [<new ref>]]\n       harness.py score <comparison>\n"

# Git ignores it, because a sheet is 300 KB and a comparison keeps six.
RUNS = blind_clone.HERE / "runs"
TOOLS = ("claude", "uv", "git")


def need_tools(runner):
    for tool in TOOLS:
        if not runner.found(tool):
            raise refusal("The scorer needs Claude Code, uv and git, and {} is missing. Install it, then run this "
                          "again. Nothing was scored.".format(blind_clone.TOOL_NAMES.get(tool, tool)))


def main(argv, runner, out, err, where, today, runs=RUNS, pin_file=blind_clone.PIN_FILE,
         statements_folder=statements.FOLDER):
    try:
        argv = [str(a) for a in argv]
        verb = argv[0] if argv else None
        if not (verb == "score" and len(argv) == 2 or verb == "compare" and len(argv) <= 3):
            raise misuse(USAGE)
        if verb == "compare":
            blind_clone.need_tools(runner)
        else:
            need_tools(runner)
        source = blind_clone.must(blind_clone.git(runner, where, "rev-parse", "--show-toplevel"),
                                  "find the repo").strip()
        pin = json.loads(Path(pin_file).read_text(encoding="utf-8"))
        if verb == "compare":
            out.write(compare.compare(runner, source, argv[1:], runs, pin, statements_folder, today, err))
        else:
            out.write(score.score(runner, source, Path(runs) / argv[1], pin, statements_folder, today))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], compare.Capped(), sys.stdout, sys.stderr, os.getcwd(),
                  datetime.date.today().isoformat()))
