import os
import re
import sys

from output.streams import speaking_any_character
from runner import Subprocess
from steering.target_branch import tracker_for
from stop import Stop, misuse, refusal
from tracker.github import GitHub

USAGE = ("usage: tracker-show <spec-or-ticket>\n"
         "       With the files Tracker: tracker-show <spec> or tracker-show <spec>/<ticket>\n")

# A files Tracker ticket is named by its spec too, because its number is local to that spec.
NAMED = re.compile(r"([0-9]+)(?:/([0-9]+))?")


class Named:
    def __init__(self, given, usage):
        found = NAMED.fullmatch(given)
        if not found:
            raise misuse(usage)
        self.first = str(int(found.group(1)))
        self.ticket = str(int(found.group(2))) if found.group(2) else None


def opened(runner, where, named):
    found = runner.run(["git", "-C", where, "rev-parse", "--show-toplevel"])
    if found.status != 0:
        raise refusal("{} is not inside a git repo.".format(where))
    tracker = tracker_for(runner, found.out.strip(), named.first)
    if isinstance(tracker, GitHub) and named.ticket is not None:
        raise refusal("The GitHub Tracker names each issue by its number alone, such as 642.")
    problem = tracker.connect()
    if problem:
        raise refusal(problem[0].upper() + problem[1:] + ".")
    return tracker


def printed(issue):
    parts = ["# " + issue["title"], issue["body"]]
    for comment in issue["comments"]:
        parts += ["## Comment by " + comment["author"]["login"], comment["body"]]
    return "\n\n".join(part.strip("\n") for part in parts) + "\n"


def main(argv, runner, out, err, where=None):
    where = where or os.getcwd()
    try:
        if len(argv) != 1:
            raise misuse(USAGE)
        named = Named(argv[0], USAGE)
        tracker = opened(runner, where, named)
        if isinstance(tracker, GitHub):
            out.write(printed(tracker.issue(named.first)))
        else:
            out.write(tracker.text(named.first, named.ticket))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1]))
