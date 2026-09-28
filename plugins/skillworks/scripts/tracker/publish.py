# A number is pushed the moment it is read, so of two rival specs one push is refused and reads again.

import os
import re
import sys
import time
from pathlib import Path

from runner import Subprocess
from steering.target_branch import SPEC_MODE, target_setting, tracker_setting
from stop import Stop, is_a_number, misuse, refusal
from tracker.files import (CLAIMED_BY, EVERY_BRANCH, FENCE, PUSH_ATTEMPTS, SPEC_FILE, SPECS, STATUS,
                           TICKETS, Files, as_numbers, frontmatter, heading, number_of,
                           with_last_section)
from tracker.reading import DRIFT_REPORT, NAME_REPORT, listed

USAGE = (
    "usage: tracker-publish spec <slug> <body-file> [<branch>]\n"
    "       tracker-publish tickets <spec> <ticket-file>...\n"
    "       tracker-publish drift <spec> <report-file>\n"
    "       tracker-publish names <spec> <report-file>\n"
)

REPORTS = {"drift": (DRIFT_REPORT, "drift report"), "names": (NAME_REPORT, "Name report")}

SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")

# Outside refs/heads and refs/tags, so no clone or fetch brings the reservations down.
RESERVED = "refs/skillworks/specs/"


def opened(runner, where, spec, wait):
    found = runner.run(["git", "-C", where, "rev-parse", "--show-toplevel"])
    if found.status != 0:
        raise refusal("{} is not inside a git repo.".format(where))
    top = found.out.strip()
    if tracker_setting(top) != "files":
        raise refusal("tracker in docs/agents/loop.json is not files, and tracker-publish writes "
                      "the files Tracker alone. Publish as docs/agents/issue-tracker.md says.")
    named = target_setting(top)
    tracker = Files(runner, top, None if named == SPEC_MODE else named, spec, wait)
    problem = tracker.connect()
    if problem:
        raise refusal(problem[0].upper() + problem[1:] + ".")
    return tracker


def read(where, path):
    try:
        return (Path(where) / path).read_text(encoding="utf-8")
    except OSError as error:
        raise refusal("{} could not be read: {}".format(path, error))


def highest(tracker, refs):
    numbers = [int(number_of(path.rsplit("/", 1)[-1]) or 0)
               for ref in refs
               for path in listed(tracker.git("ls-tree", "--name-only", ref, SPECS + "/").out)]
    return max(numbers, default=0)


def tip(tracker, branch):
    commit = tracker.git("rev-parse", "--verify", "--quiet", "origin/" + branch).out.strip()
    if not commit:
        raise refusal("origin has no branch {}, so nothing was written to it. Push the branch "
                      "first.".format(branch))
    return commit


def every_branch(tracker):
    refs = listed(tracker.git("for-each-ref", "--format=%(refname:strip=2)", "refs/remotes/origin").out)
    return [ref for ref in refs if ref != "origin/HEAD"]


def highest_reserved(tracker):
    said = tracker.git("ls-remote", "origin", RESERVED + "*").out
    names = [line.split("\t", 1)[-1][len(RESERVED):] for line in listed(said)]
    return max([int(name) for name in names if is_a_number(name)], default=0)


def publish_spec(tracker, slug, body, branch, out):
    in_spec_mode = tracker.target is None
    if not SLUG.fullmatch(slug):
        raise refusal("The slug {} is not kebab case, such as local-tracker.".format(slug))
    if in_spec_mode and not branch:
        raise refusal("docs/agents/loop.json says spec, so the spec goes on a branch of its own. "
                      "Name it after the body file.")
    if not in_spec_mode and branch:
        raise refusal("docs/agents/loop.json names the Target branch {}, so the spec goes there, "
                      "and no branch is named.".format(tracker.target))
    if body.lstrip().startswith(FENCE):
        raise refusal("The body already opens with frontmatter. tracker-publish writes it, so "
                      "leave it out.")
    branch = branch or tracker.target
    fields = [STATUS + ": open"] + (["branch: " + branch] if in_spec_mode else [])
    text = "\n".join([FENCE] + fields + [FENCE, "", ""]) + body
    for _ in range(PUSH_ATTEMPTS):
        tracker.fetched(EVERY_BRANCH if in_spec_mode else branch)
        parent = tip(tracker, branch)
        if in_spec_mode:
            number = max(highest(tracker, every_branch(tracker)), highest_reserved(tracker)) + 1
        else:
            number = highest(tracker, [parent]) + 1
        folder = "{}/{:04d}-{}".format(SPECS, number, slug)
        # In spec mode two specs push to two branches and neither is refused, so the number is held on one ref too.
        reserved = [RESERVED + str(number)] if in_spec_mode else []
        if tracker.pushed(branch, parent, {folder + "/" + SPEC_FILE: text},
                          "Write spec {}: {}".format(number, heading(body, slug)),
                          "Spec {}".format(number), reserved):
            out.write("{}\t{}\n".format(number, folder))
            return
    raise refusal("The spec lost the race for a number {} times in a row. Run tracker-publish "
                  "again.".format(PUSH_ATTEMPTS))


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
    for number, (name, text) in named.items():
        held, _ = frontmatter(text)
        if held.get(STATUS) != "open":
            raise refusal("{} needs status: open in its frontmatter.".format(name))
        if held.get(CLAIMED_BY):
            raise refusal("{} names claimed-by, which the loop sets as it takes the ticket. Leave "
                          "it empty.".format(name))
        for blocker in as_numbers(held.get("blocked-by", [])):
            if blocker not in named or int(blocker) >= int(number):
                raise refusal("{} is blocked by {}, which is not a ticket before it. Number the "
                              "tickets in dependency order, blockers first.".format(name, blocker))
    return named.values()


def publish_tickets(tracker, spec, tickets, out):
    branch = tracker.branch_of(spec)
    for _ in range(PUSH_ATTEMPTS):
        tracker.fetched(branch)
        parent = tip(tracker, branch)
        folder = tracker.folder_on(parent, spec)
        if not folder:
            raise refusal("Spec {} has no folder on origin/{}. Write it with tracker-publish spec "
                          "first.".format(spec, branch))
        if listed(tracker.git("ls-tree", "--name-only", parent, folder + "/" + TICKETS + "/").out):
            raise refusal("Spec {} already has tickets on origin/{}, so none were "
                          "written.".format(spec, branch))
        written = {"{}/{}/{}".format(folder, TICKETS, name): text for name, text in tickets}
        if tracker.pushed(branch, parent, written, "Write the tickets of spec {}".format(spec),
                          "The tickets of spec {}".format(spec)):
            out.write("".join(path + "\n" for path in written))
            return
    raise refusal("The tickets of spec {} lost to another push {} times in a row. Run "
                  "tracker-publish again.".format(spec, PUSH_ATTEMPTS))


# Each report replaces its heading to the end of the file, so a drift report takes the Name report after it too.
def publish_report(tracker, spec, report, heading, what, out):
    if report.replace("\r\n", "\n").split("\n", 1)[0].strip() != heading:
        raise refusal("The {} does not open with {}. Its first line is that heading, as it is on a "
                      "GitHub comment.".format(what, heading))
    branch = tracker.branch_of(spec)
    for _ in range(PUSH_ATTEMPTS):
        tracker.fetched(branch)
        parent = tip(tracker, branch)
        folder = tracker.folder_on(parent, spec)
        if not folder:
            raise refusal("Spec {} has no folder on origin/{}, so its {} has nowhere to "
                          "go.".format(spec, branch, what))
        path = folder + "/" + SPEC_FILE
        written = with_last_section(tracker.shown(parent, path), heading, report)
        if tracker.pushed(branch, parent, {path: written},
                          "Record the {} of spec {}".format(what, spec),
                          "The {} of spec {}".format(what, spec)):
            out.write(path + "\n")
            return
    raise refusal("The {} of spec {} lost to another push {} times in a row. Run "
                  "tracker-publish again.".format(what, spec, PUSH_ATTEMPTS))


def main(argv, runner, out, err, wait, where=None):
    where = where or os.getcwd()
    try:
        command = argv[0] if argv else ""
        if command == "spec" and len(argv) in (3, 4):
            tracker = opened(runner, where, None, wait)
            publish_spec(tracker, argv[1], read(where, argv[2]), argv[3] if len(argv) == 4 else "",
                         out)
            return 0
        if command == "tickets" and len(argv) > 2 and is_a_number(argv[1]):
            spec = str(int(argv[1]))
            tickets = checked_tickets(where, argv[2:])
            publish_tickets(opened(runner, where, spec, wait), spec, tickets, out)
            return 0
        if command in REPORTS and len(argv) == 3 and is_a_number(argv[1]):
            spec = str(int(argv[1]))
            heading, what = REPORTS[command]
            publish_report(opened(runner, where, spec, wait), spec, read(where, argv[2]), heading,
                           what, out)
            return 0
        raise misuse(USAGE)
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    # Windows adds a carriage return, which goes with the path a caller reads off stdout.
    sys.stdout.reconfigure(newline="\n")
    sys.stderr.reconfigure(newline="\n")
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, time.sleep, sys.argv[1]))
