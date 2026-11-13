import os
import sys

from output.streams import speaking_any_character
from runner import Subprocess
from steering.target_branch import LOOP_FILE, tracker_setting
from stop import Stop, is_a_number, misuse, refusal
from tracker.github import GitHub

USAGE = "usage: tracker-show <spec-or-ticket>\n"


def github_tracker(runner, where, command):
    found = runner.run(["git", "-C", where, "rev-parse", "--show-toplevel"])
    if found.status != 0:
        raise refusal("{} is not inside a git repo.".format(where))
    top = found.out.strip()
    if tracker_setting(top) != "github":
        raise refusal("{} names the files Tracker, and {} serves the GitHub Tracker alone so far. "
                      "Read the ticket file as docs/skillworks/issue-tracker.md says.".format(
                          LOOP_FILE, command))
    tracker = GitHub(runner, top)
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
        if len(argv) != 1 or not is_a_number(argv[0]):
            raise misuse(USAGE)
        tracker = github_tracker(runner, where, "tracker-show")
        out.write(printed(tracker.issue(str(int(argv[0])))))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1]))
