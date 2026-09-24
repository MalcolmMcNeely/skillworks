#
# The whole suite, as the repo's Suite file names it.
#
# Two callers, the landing and the driver, so one implementation keeps their stop rule the same.
#
# The repo owns the list, so nothing here names a command, a folder or a tool of any one repo.
# A machine short of what the checks need is not a red suite, so readiness is proved first.
# A command is an argument list and never a shell line, so it reads the same on every machine.
# An `unless` path that exists skips its readiness command, so an install is not done twice.
# Some repos have tests that flake, and only the repo knows, so its file says how often red runs.

import json
from pathlib import Path
from typing import NamedTuple

SUITE_FILE = "docs/agents/suite.json"


class Outcome(NamedTuple):
    passed: bool
    said: str
    # False when the checks never started, so nothing at all was proved about the work.
    ready: bool = True


class Ready(NamedTuple):
    command: list
    message: str
    unless: str


class Check(NamedTuple):
    command: list
    folder: Path
    ready: Ready


class Unreadable(Exception):
    pass


def command_of(entry):
    command = entry.get("command") if isinstance(entry, dict) else None
    if not isinstance(command, list) or not command or not all(
            isinstance(word, str) and word for word in command):
        raise Unreadable("a command that is not a list of words")
    return command


class Suite:
    def __init__(self, runner, worktree):
        self.runner = runner
        self.tree = Path(worktree)

    def read(self):
        path = self.tree / SUITE_FILE
        if not path.is_file():
            raise Unreadable("no such file")
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as fault:
            raise Unreadable("it is not JSON: {}".format(fault))
        if not isinstance(parsed, dict):
            raise Unreadable("it names no checks")
        runs = parsed.get("runs", 1)
        # Python counts a JSON true as an int, and a Suite run true times means nothing.
        if not isinstance(runs, int) or isinstance(runs, bool) or runs < 1:
            raise Unreadable("runs is not a count of 1 or more")
        entries = parsed.get("checks")
        if not isinstance(entries, list) or not entries:
            raise Unreadable("it names no checks")

        wanted = []
        for entry in entries:
            ready = entry.get("ready") if isinstance(entry, dict) else None
            if ready is not None:
                ready = Ready(command_of(ready), str(ready.get("message", "")),
                              ready.get("unless"))
            wanted.append(Check(command_of(entry), self.tree / entry.get("folder", "."), ready))
        return wanted, runs

    # Read as facts, never out of a runner's output, which is reworded with every version.
    def short_of(self, wanted):
        for check in wanted:
            for command in [check.command] + ([check.ready.command] if check.ready else []):
                if not self.runner.found(command[0]):
                    return ("{} is not on PATH, and the Suite file names it. Install it and run "
                            "this again.\n").format(command[0])

        for check in wanted:
            ready = check.ready
            if ready is None or (ready.unless and (self.tree / ready.unless).exists()):
                continue
            asked = self.runner.run(ready.command, check.folder.as_posix())
            if asked.status != 0:
                return "{}\n{} said:\n{}".format(
                    ready.message.rstrip("\n"), " ".join(ready.command), asked.out + asked.err)
        return ""

    def run(self, heard=None):
        try:
            wanted, runs = self.read()
        # A suite that ran nothing cannot pass, so a file that names nothing is never green.
        except Unreadable as fault:
            return Outcome(False, "the Suite file {} cannot be run, because {}\n".format(
                SUITE_FILE, fault), ready=False)

        short = self.short_of(wanted)
        if short:
            return Outcome(False, short, ready=False)

        for at in range(1, runs + 1):
            outcome = self.run_checks(wanted)
            if heard is not None:
                heard(outcome, at)
            if outcome.passed:
                break
        return outcome

    def run_checks(self, wanted):
        said = ""
        for check in wanted:
            ran = self.runner.run(check.command, check.folder.as_posix())
            said += ran.out + ran.err
            if ran.status != 0:
                return Outcome(False, said)
        return Outcome(True, said)
