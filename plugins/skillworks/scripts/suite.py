#
# The whole suite, as the repo's Suite file names it.
#
# Two callers, the landing and the driver, so one implementation keeps their stop rule the same.
#
# The repo owns the list, so nothing here names a command, a folder or a tool of any one repo.
# A machine short of what the checks need is not a red suite, so readiness is proved first.
# Readiness runs one command at a time, because two checks can share one install.
# The checks then run together, so the Suite takes as long as its slowest check.
# A slow check of a rarely changed file names its paths, so it runs only when they change.
# A command is an argument list and never a shell line, so it reads the same on every machine.
# An `unless` path that exists skips its readiness command, so an install is not done twice.
# Some repos have tests that flake, and only the repo knows, so its file says how often red runs.

import json
from concurrent.futures import ThreadPoolExecutor
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
    when: list = None

    def woken_by(self, changed):
        if self.when is None or changed is None:
            return True
        return any(name == path or name.startswith(path + "/")
                   for path in self.when for name in changed)


class Unreadable(Exception):
    pass


def is_list_of_words(value):
    return isinstance(value, list) and bool(value) and all(
        isinstance(word, str) and word for word in value)


def command_of(entry):
    command = entry.get("command") if isinstance(entry, dict) else None
    if not is_list_of_words(command):
        raise Unreadable("a command that is not a list of words")
    return command


def paths_of(entry):
    if "when" not in entry:
        return None
    if not is_list_of_words(entry["when"]):
        raise Unreadable("a when that is not a list of paths")
    return [path.rstrip("/") for path in entry["when"]]


def did_not_run(check):
    return "{} did not run, because the change touches none of the paths it names\n".format(
        " ".join(check.command))


class Suite:
    # An unread change runs every check, because running one not needed is the safe way to be wrong.
    def __init__(self, runner, worktree, base=None):
        self.runner = runner
        self.tree = Path(worktree)
        self.base = base

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
            wanted.append(Check(command_of(entry), self.tree / entry.get("folder", "."), ready,
                                paths_of(entry)))
        return wanted, runs

    # Measured from the base and not from main, so work that landed meanwhile wakes nothing.
    def changed(self):
        if not self.base:
            return None
        tree = self.tree.as_posix()
        differ = self.runner.run(
            ["git", "-C", tree, "diff", "--name-only", "--no-renames", "-z", self.base], tree)
        untracked = self.runner.run(
            ["git", "-C", tree, "ls-files", "--others", "--exclude-standard", "--full-name", "-z"],
            tree)
        if differ.status != 0 or untracked.status != 0:
            return None
        return {name for name in (differ.out + untracked.out).split("\0") if name}

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

        changed = self.changed()
        for at in range(1, runs + 1):
            outcome = self.run_checks(wanted, changed)
            if heard is not None:
                heard(outcome, at)
            if outcome.passed:
                break
        return outcome

    # A red check lets the others finish, so the one fix circuit reads every failure, not the first.
    def run_checks(self, wanted, changed):
        with ThreadPoolExecutor(max_workers=len(wanted)) as pool:
            running = [pool.submit(self.runner.run, check.command, check.folder.as_posix())
                       if check.woken_by(changed) else None for check in wanted]
            ran = [each.result() if each else None for each in running]
        said = "".join(did_not_run(check) if each is None else each.out + each.err
                       for check, each in zip(wanted, ran))
        return Outcome(all(each.status == 0 for each in ran if each), said)
