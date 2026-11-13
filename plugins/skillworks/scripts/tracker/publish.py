import os
import re
import sys
from pathlib import Path

from clock.clock import Clock
from output.streams import speaking_any_character
from runner import Subprocess
from steering.target_branch import LOOP_FILE, tracker_for
from stop import Stop, is_a_number, misuse, refusal
from tracker.files import FENCE, STATUS, as_numbers, frontmatter, number_of
from tracker.github import BRANCH_HEADING, GitHub, NewTicket
from tracker.reading import DRIFT_REPORT, NAME_REPORT

USAGE = (
    "usage: tracker-publish spec <slug> <body-file> [<branch>]\n"
    "       tracker-publish tickets <spec> <ticket-file>...\n"
    "       tracker-publish drift <spec> <report-file>\n"
    "       tracker-publish names <spec> <report-file>\n"
)

REPORTS = {"drift": (DRIFT_REPORT, "drift report"), "names": (NAME_REPORT, "Name report")}

SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")

SPEC_HEADING = "# SPEC: "


def opened(runner, where, spec, clock=None):
    found = runner.run(["git", "-C", where, "rev-parse", "--show-toplevel"])
    if found.status != 0:
        raise refusal("{} is not inside a git repo.".format(where))
    tracker = tracker_for(runner, found.out.strip(), spec, clock)
    problem = tracker.connect()
    if problem:
        raise refusal(problem[0].upper() + problem[1:] + ".")
    return tracker


def read(where, path):
    try:
        return (Path(where) / path).read_text(encoding="utf-8")
    except OSError as error:
        raise refusal("{} could not be read: {}".format(path, error))


# The title is the heading and the body what is below it, as the loop reads a spec issue back.
def github_spec(body, branch):
    first, _, below = body.replace("\r\n", "\n").lstrip("\n").partition("\n")
    if not first.startswith(SPEC_HEADING):
        raise refusal("The spec file does not open with {}<title>, which names the "
                      "issue.".format(SPEC_HEADING))
    text = below.strip("\n") + "\n"
    if branch:
        if BRANCH_HEADING in [line.strip() for line in text.split("\n")]:
            raise refusal("The spec file already holds a {} section. tracker-publish writes it "
                          "from the branch named, so leave it out.".format(BRANCH_HEADING))
        text = "{}\n\n{}\n\n{}".format(BRANCH_HEADING, branch, text)
    return first[2:].strip(), text


def publish_spec(tracker, slug, body, branch, out, err):
    in_pr_mode = tracker.target is None
    if not SLUG.fullmatch(slug):
        raise refusal("The slug {} is not kebab case, such as local-tracker.".format(slug))
    if in_pr_mode and not branch:
        raise refusal("{} says pr, so the spec goes on a branch of its own. "
                      "Name it after the body file.".format(LOOP_FILE))
    if not in_pr_mode and branch:
        raise refusal("{} names the Target branch {}, so the spec goes there, "
                      "and no branch is named.".format(LOOP_FILE, tracker.target))
    if isinstance(tracker, GitHub):
        out.write("{}\t{}\n".format(*tracker.file_spec(*github_spec(body, branch), err)))
        return
    if body.lstrip().startswith(FENCE):
        raise refusal("The body already opens with frontmatter. tracker-publish writes it, so "
                      "leave it out.")
    number, folder, written = tracker.write_spec(slug, body, branch if in_pr_mode else "")
    out.write("{}\t{}\n".format(number, folder))
    if not written:
        err.write("Spec {} in the Sidecar already holds this spec, so nothing was written.\n".format(
            number))


def checked_tickets(where, paths):
    named = {}
    for path in paths:
        name = Path(path).name
        number = number_of(name)
        if not number or not name.endswith(".md"):
            raise refusal("{} does not start with a ticket number, such as "
                          "01-read-loop-json.md.".format(name))
        if number in named:
            raise refusal("{} and {} share the number {}.".format(named[number][0], name, number))
        named[number] = (name, read(where, path))
    titles = {}
    for number, (name, text) in named.items():
        title = titled(name, text)[0]
        if title in titles:
            raise refusal("{} and {} share the title {}, so a second run could not tell them "
                          "apart.".format(titles[title], name, title))
        titles[title] = name
        held, _ = frontmatter(text)
        if held.get(STATUS) != "open":
            raise refusal("{} needs status: open in its frontmatter.".format(name))
        for blocker in as_numbers(held.get("blocked-by", [])):
            if blocker not in named or int(blocker) >= int(number):
                raise refusal("{} is blocked by {}, which is not a ticket before it. Number the "
                              "tickets in dependency order, blockers first.".format(name, blocker))
    return [named[number] for number in sorted(named, key=int)]


# Falls back to the file name as the files Tracker does, so one file names one ticket on both.
def titled(name, text):
    lines = frontmatter(text)[1].split("\n")
    at = next((at for at, line in enumerate(lines) if line.startswith("# ")), None)
    if at is None:
        return name[:-3], "\n".join(lines).strip("\n") + "\n"
    return lines[at][2:].strip(), "\n".join(lines[at + 1:]).strip("\n") + "\n"


def github_tickets(tickets):
    titles = {number_of(name): titled(name, text)[0] for name, text in tickets}
    return [NewTicket(*titled(name, text),
                      tuple(titles[blocker] for blocker in
                            as_numbers(frontmatter(text)[0].get("blocked-by", []))))
            for name, text in tickets]


def publish_tickets(tracker, spec, tickets, out, err):
    if isinstance(tracker, GitHub):
        filing = tracker.file_tickets(spec, github_tickets(tickets))
        out.write("".join(number + "\n" for number in filing.numbers))
        if not filing.changed:
            err.write("Every ticket of spec #{} was already filed and linked, so nothing "
                      "changed.\n".format(spec))
        return
    out.write("".join(path + "\n" for path in tracker.write_tickets(spec, tickets)))


def publish_report(tracker, spec, report_file, report, heading, what, out):
    if report.replace("\r\n", "\n").split("\n", 1)[0].strip() != heading:
        raise refusal("The {} does not open with {}. Its first line is that heading, as it is on a "
                      "GitHub comment.".format(what, heading))
    if isinstance(tracker, GitHub):
        out.write(tracker.post_report(spec, report_file, what) + "\n")
        return
    out.write(tracker.record_report(spec, heading, report, what) + "\n")


def main(argv, runner, out, err, clock=None, where=None):
    where = where or os.getcwd()
    try:
        command = argv[0] if argv else ""
        if command == "spec" and len(argv) in (3, 4):
            tracker = opened(runner, where, None, clock)
            publish_spec(tracker, argv[1], read(where, argv[2]), argv[3] if len(argv) == 4 else "",
                         out, err)
            return 0
        if command == "tickets" and len(argv) > 2 and is_a_number(argv[1]):
            spec = str(int(argv[1]))
            tickets = checked_tickets(where, argv[2:])
            publish_tickets(opened(runner, where, spec, clock), spec, tickets, out, err)
            return 0
        if command in REPORTS and len(argv) == 3 and is_a_number(argv[1]):
            spec = str(int(argv[1]))
            heading, what = REPORTS[command]
            report_file = (Path(where) / argv[2]).as_posix()
            publish_report(opened(runner, where, spec, clock), spec, report_file,
                           read(where, argv[2]), heading, what, out)
            return 0
        raise misuse(USAGE)
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, Clock(), sys.argv[1]))
