import os
import sys
from pathlib import Path

from output.streams import speaking_any_character
from runner import Subprocess
from stop import Stop, misuse, refusal
from tracker.github import GitHub
from tracker.show import Named, opened

USAGE = ("usage: tracker-close <ticket> <note-file>\n"
         "       With the files Tracker: tracker-close <spec>/<ticket> <note-file>\n")


def read(where, path):
    try:
        return (Path(where) / path).read_text(encoding="utf-8")
    except OSError as error:
        raise refusal("{} could not be read: {}".format(path, error))


def closed_on_github(tracker, ticket, note, out, err):
    if tracker.state(ticket) == "closed":
        err.write("Ticket #{} is already closed, so nothing changed.\n".format(ticket))
        return
    # One call, so a guardrail cannot leave the ticket closed with no note.
    done = tracker.gh("issue", "close", ticket, "--comment", note, "--reason", "completed")
    if done.status != 0:
        raise refusal("GitHub would not close ticket #{}, so it is still open. Run tracker-close "
                      "again. gh said:\n{}".format(ticket, (done.out + done.err).rstrip("\n")))
    out.write("Closed #{}.\n".format(ticket))


def closed_in_files(tracker, named, note, out, err):
    reference = tracker.reference(named.ticket)
    if tracker.state(named.ticket) == "closed":
        err.write("Ticket {} is already closed, so nothing changed.\n".format(reference))
        return
    tracker.close(named.ticket, note)
    out.write("Closed {}.\n".format(reference))


def main(argv, runner, out, err, where=None):
    where = where or os.getcwd()
    try:
        if len(argv) != 2:
            raise misuse(USAGE)
        named = Named(argv[0], USAGE)
        note = read(where, argv[1])
        tracker = opened(runner, where, named)
        if isinstance(tracker, GitHub):
            closed_on_github(tracker, named.first, note, out, err)
        elif named.ticket is None:
            raise refusal("The files Tracker names a ticket by its spec and its number, such as "
                          "7/2, and {} names no ticket.".format(argv[0]))
        else:
            closed_in_files(tracker, named, note, out, err)
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1]))
