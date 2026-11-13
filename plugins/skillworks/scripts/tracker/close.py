import os
import sys
from pathlib import Path

from output.streams import speaking_any_character
from runner import Subprocess
from stop import Stop, is_a_number, misuse, refusal
from tracker.show import github_tracker

USAGE = "usage: tracker-close <ticket> <note-file>\n"


def read(where, path):
    try:
        return (Path(where) / path).read_text(encoding="utf-8")
    except OSError as error:
        raise refusal("{} could not be read: {}".format(path, error))


def main(argv, runner, out, err, where=None):
    where = where or os.getcwd()
    try:
        if len(argv) != 2 or not is_a_number(argv[0]):
            raise misuse(USAGE)
        ticket = str(int(argv[0]))
        note = read(where, argv[1])
        tracker = github_tracker(runner, where, "tracker-close")
        if tracker.state(ticket) == "closed":
            err.write("Ticket #{} is already closed, so nothing changed.\n".format(ticket))
            return 0
        # One call, so a guardrail cannot leave the ticket closed with no note.
        done = tracker.gh("issue", "close", ticket, "--comment", note, "--reason", "completed")
        if done.status != 0:
            raise refusal("GitHub would not close ticket #{}, so it is still open. Run tracker-close "
                          "again. gh said:\n{}".format(ticket, (done.out + done.err).rstrip("\n")))
        out.write("Closed #{}.\n".format(ticket))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1]))
