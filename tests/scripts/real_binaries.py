# The lines are built by the driver, not written out, so a flag it changes arrives on its own.
# gh prints its help only once every flag has parsed, and turns an unknown flag down even then.
# An unknown subcommand is not turned down: gh falls back to group help, whose USAGE says <command>.
# claude parses the whole line before the session lookup, so an unknown option is turned down first.

import io
import tempfile
from pathlib import Path
from typing import NamedTuple

import land_ticket
import spec_loop
from conftest import ROOT, Ran, RecordingRunner
from runner import Subprocess

SPEC = "200"
TICKET = "206"
SESSION = "11111111-2222-3333-4444-555555555555"
REPO = "owner/repo"

# Shaped like a session id and naming none, so claude stops at the lookup.
NOWHERE = "00000000-0000-0000-0000-000000000000"

# A field gh cannot have, so it answers with the fields it does have.
NO_SUCH_FIELD = "zzznosuchfield"

REAL = Subprocess()


class Line(NamedTuple):
    args: list
    env: dict

    def program(self):
        return self.args[0]

    def whole(self):
        return " ".join(self.args)

    # Two claude lines differ by their flags and not by their prompt, which would not fit an id.
    def flags(self):
        return " ".join(word for word in self.args if word.startswith("-"))

    def asks_for_a_field(self):
        return "--json" in self.args

    def field(self):
        return self.args[self.args.index("--json") + 1]

    def helped(self):
        return self.args + ["--help"]

    def without_the_field(self):
        at = self.args.index("--json")
        return self.args[:at + 1] + [NO_SUCH_FIELD] + self.args[at + 2:]

    def resumed_from_nowhere(self):
        if "--resume" not in self.args:
            return self.args + ["--resume", NOWHERE]
        at = self.args.index("--resume")
        return self.args[:at + 1] + [NOWHERE] + self.args[at + 2:]

    # Where a program runs is not what is proved, so every line runs in this checkout.
    def started(self, asked):
        return REAL.run(asked, ROOT.as_posix(), self.env)


# Only enough for the driver to carry on to the next line it builds.
def answer(args):
    asked = " ".join(args[1:])
    if asked == "repo view --json nameWithOwner --jq .nameWithOwner":
        return Ran(0, REPO + "\n", "")
    if asked == "api user --jq .login":
        return Ran(0, "me\n", "")
    if "sub_issues" in asked:
        return Ran(0, TICKET + "\n", "")
    if asked.endswith("--jq .state"):
        # The spec reads open so preflight goes on, the ticket closed so the driver reopens it.
        return Ran(0, ("open" if "/issues/" + SPEC + " " in asked else "closed") + "\n", "")
    if "blocked_by" in asked:
        return Ran(0, "0\n", "")
    if "assignees" in asked:
        # Somebody else holding it is what makes the driver build the line that lets go.
        return Ran(0, "other\n", "")
    return Ran(0, "", "")


# One of each, because a line built twice is the same line to the program reading it.
def once(calls):
    kept, seen = [], set()
    for call in calls:
        line = Line(call.args, call.env)
        if line.whole() in seen:
            continue
        seen.add(line.whole())
        kept.append(line)
    return kept


def driver_lines():
    runner = RecordingRunner()
    runner.stub("gh", does=lambda: answer(runner.calls[-1]))
    # Nothing is read back off a claude line, so an empty answer is the whole of it.
    runner.stub("claude")

    with tempfile.TemporaryDirectory() as folder:
        loop = spec_loop.Loop(runner, SPEC, io.StringIO(), io.StringIO(), lambda seconds: None)
        # Where the driver logs what it says is not what this proves.
        loop.log = Path(folder) / "loop.log"
        loop.preflight()
        loop.reopen(TICKET)
        loop.next_ticket([TICKET])
        loop.claimed(TICKET)
        loop.claude_p("/implement {} --stop-after-tests".format(TICKET))
        loop.claude_p("/implement {} --fix".format(TICKET), "--resume", SESSION)

        landing = land_ticket.Landing(
            runner, folder, TICKET, SESSION, io.StringIO(), io.StringIO())
        landing.closing_comment(TICKET)
        landing.resolve_call("/resolve-conflict")
    return once(runner.made)


LINES = driver_lines()
GH = [line for line in LINES if line.program() == "gh"]
GH_FIELDS = [line for line in GH if line.asks_for_a_field()]
CLAUDE = [line for line in LINES if line.program() == "claude"]


def listed(lines):
    return "".join("  " + line.whole() + "\n" for line in lines)


def report(asked, ran):
    return " ".join(asked) + "\n" + ran.out + ran.err


def usage_of(said):
    lines = said.split("\n")
    for at, line in enumerate(lines):
        if line.strip() == "USAGE" and at + 1 < len(lines):
            return lines[at + 1].strip()
    return ""
