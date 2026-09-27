#
# The whole suite, as the repo's Suite file names it.
#
# Three callers share one stop rule: the landing, the driver and `skillworks-suite`.
#
# The repo owns the list, so nothing here names a command, a folder or a tool of any one repo.
# A machine short of what the checks need is not a red suite, so readiness is proved first.
# Readiness runs one command at a time, because two checks can share one install.
# The checks then run together, so the Suite takes as long as its slowest check.
# A check that passed keeps a Proof of its inputs, so it never runs again on the same ones.
# A check names what it ignores, not what it reads, so a path left off costs a run, never a red pass.
# A command is an argument list and never a shell line, so it reads the same on every machine.
# An `unless` path that exists skips its readiness command, so an install is not done twice.
# Some repos have tests that flake, and only the repo knows, so its file says how often red runs.
# A check can name an image, for tests that start processes an OS is slow to start.
# Fresh mode trusts no Proof and no image, so a Proof gone stale outside the repo is caught.

import hashlib
import json
import os
import posixpath
import re
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: skillworks-suite [--fresh]\n"
SUITE_FILE = "docs/agents/suite.json"
REPO_IN_IMAGE = "/repo"
PROOFS = "skillworks/proofs"
# Only these make a check what it is, so an edit to another check leaves this one's Proofs standing.
KEYED = ("command", "folder", "image", "ignores", "ready")
# The check comes last, and a record made before it was kept still reads as a Proof.
RECORD = re.compile(r"([0-9a-f]{64}) (\d{4}-\d\d-\d\d \d\d:\d\d UTC)(?: ([0-9a-f]{64}))?")
NO_WHEN = ("a check carries `when`, which the Suite no longer reads. Replace it with `ignores`: the "
           "paths, as git pathspecs from the repo root, that the check cannot be changed by. A check "
           "reads every file git does not ignore, less its `ignores`, and runs again only when one "
           "of them changes")


class Outcome(NamedTuple):
    passed: bool
    said: str
    # False when the checks never started, so nothing at all was proved about the work.
    ready: bool = True
    red: tuple = ()


class Ready(NamedTuple):
    command: list
    message: str
    unless: str


class Check(NamedTuple):
    command: list
    folder: Path
    ready: Ready
    image: str = None
    ignores: list = ()
    keyed: str = ""

    # The image holds the check's own program, so the host needs only docker.
    def programs(self):
        command = ["docker"] if self.image else [self.command[0]]
        return command + ([self.ready.command[0]] if self.ready else [])

    # Every Proof of this entry carries it, so a red fresh run can find them all.
    def named(self):
        return hashlib.sha256(self.keyed.encode("utf-8")).hexdigest()


class Proof(NamedTuple):
    key: str
    made: str


class Proofs:
    # One record is one write to a file opened for append, so two loops at once cannot mix records.
    def __init__(self, path):
        self.path = path

    # The last piece has no newline after it, so it is empty or a record torn mid-write.
    def lines(self):
        if self.path is None or not self.path.is_file():
            return []
        return self.path.read_text(encoding="utf-8", errors="replace").split("\n")[:-1]

    def of(self, key):
        for line in self.lines():
            record = RECORD.fullmatch(line)
            if record and record.group(1) == key:
                return Proof(key, record.group(2))
        return None

    def keep(self, key, made, check):
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        written = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(written, "{} {} {}\n".format(key, made, check).encode("utf-8"))
        finally:
            os.close(written)

    # Swapped in whole, so no reader meets a torn store; a racing append lost costs a run, not a pass.
    def forget(self, checks, keys):
        lines = self.lines()
        kept = []
        for line in lines:
            record = RECORD.fullmatch(line)
            if record and (record.group(1) in keys or record.group(3) in checks):
                continue
            kept.append(line)
        if len(kept) == len(lines):
            return
        held, swapped = tempfile.mkstemp(dir=self.path.parent)
        with os.fdopen(held, "w", encoding="utf-8", newline="\n") as file:
            file.write("".join(line + "\n" for line in kept))
        os.replace(swapped, self.path)


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


def ignores_of(entry):
    if "when" in entry:
        raise Unreadable(NO_WHEN)
    if "ignores" not in entry:
        return []
    if not is_list_of_words(entry["ignores"]):
        raise Unreadable("an ignores that is not a list of paths")
    return entry["ignores"]


def keyed_entry(entry):
    return json.dumps({field: entry.get(field) for field in KEYED}, sort_keys=True)


def image_of(entry, tree):
    if "image" not in entry:
        return None
    image = entry["image"]
    if not isinstance(image, str) or not image or not (tree / image).is_file():
        raise Unreadable("an image that is not a Dockerfile in the repo")
    return image


def did_not_run(check, proof):
    return "{} did not run, because Proof {}, made {}, holds its inputs\n".format(
        " ".join(check.command), proof.key[:12], proof.made)


def said_by(check, held, each):
    if each is not None:
        return each.out + each.err
    if isinstance(held, Proof):
        return did_not_run(check, held)
    return held.out + held.err


def utc_now():
    return datetime.now(timezone.utc)


class Suite:
    def __init__(self, runner, worktree, now=utc_now, fresh=False):
        self.runner = runner
        self.tree = Path(worktree)
        self.now = now
        self.fresh = fresh

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
            # Read in fresh mode too, so a Suite file that names a missing image is never green.
            image = image_of(entry, self.tree)
            wanted.append(Check(command_of(entry), self.tree / entry.get("folder", "."), ready,
                                None if self.fresh else image, ignores_of(entry),
                                keyed_entry(entry)))
        return wanted, runs

    # In the common git directory, so every worktree of the clone shares them and nothing pushes them.
    def proofs(self):
        tree = self.tree.as_posix()
        asked = self.runner.run(
            ["git", "-C", tree, "rev-parse", "--path-format=absolute", "--git-common-dir"], tree)
        common = asked.out.strip()
        return Proofs(Path(common) / PROOFS if asked.status == 0 and common else None)

    # Read from the worktree as it is, so uncommitted work is proved as well as committed work.
    def listed_inputs(self, check):
        tree = self.tree.as_posix()
        return self.runner.run(
            ["git", "-C", tree, "ls-files", "--cached", "--others", "--exclude-standard", "-z",
             "--", ":(top)", *(":(top,exclude)" + path for path in check.ignores)], tree)

    def key_of(self, check, digests):
        listed = self.listed_inputs(check)
        if listed.status != 0:
            return None
        key = hashlib.sha256(check.keyed.encode("utf-8"))
        for name in sorted({name for name in listed.out.split("\0") if name}):
            path = self.tree / name
            # A tracked file the worktree deleted is still listed, and it is no input.
            if not path.is_file():
                continue
            if name not in digests:
                digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            key.update("\0{}\0{}".format(name, digests[name]).encode("utf-8"))
        return key.hexdigest()

    def keys_of(self, wanted, proofs):
        if proofs.path is None:
            return [None] * len(wanted)
        digests = {}
        return [self.key_of(check, digests) for check in wanted]

    # Fresh mode still reads the keys, because a red check's Proof on these inputs is the stale one.
    def proved(self, wanted, proofs):
        keys = self.keys_of(wanted, proofs)
        if self.fresh:
            return keys, [None] * len(wanted)
        return keys, [proofs.of(key) if key else None for key in keys]

    # Read as facts, never out of a runner's output, which is reworded with every version.
    def short_of(self, wanted):
        for check in wanted:
            for program in check.programs():
                if not self.runner.found(program):
                    return ("{} is not on PATH, and the Suite file names it. Install it and run "
                            "this again.\n").format(program)

        for check in wanted:
            ready = check.ready
            if ready is None or (ready.unless and (self.tree / ready.unless).exists()):
                continue
            asked = self.runner.run(ready.command, check.folder.as_posix())
            if asked.status != 0:
                return "{}\n{} said:\n{}".format(
                    ready.message.rstrip("\n"), " ".join(ready.command), asked.out + asked.err)

        imaged = [check for check in wanted if check.image]
        if imaged:
            asked = self.runner.run(["docker", "info"], self.tree.as_posix())
            if asked.status != 0:
                return ("Docker does not answer, and {} runs in the image {}. Start Docker and run "
                        "this again.\ndocker info said:\n{}").format(
                    " ".join(imaged[0].command), imaged[0].image, asked.out + asked.err)
        return ""

    def run(self, heard=None):
        try:
            wanted, runs = self.read()
        # A suite that ran nothing cannot pass, so a file that names nothing is never green.
        except Unreadable as fault:
            return Outcome(False, "the Suite file {} cannot be run, because {}\n".format(
                SUITE_FILE, fault), ready=False)

        proofs = self.proofs()
        keys, found = self.proved(wanted, proofs)
        short = self.short_of([check for check, proof in zip(wanted, found) if proof is None])
        if short:
            return Outcome(False, short, ready=False)

        for at in range(1, runs + 1):
            # A check that went green in the run before is proved now, so only red runs again.
            # Fresh mode keeps no Proof, so it carries the earlier pass itself.
            if at > 1 and not self.fresh:
                keys, found = self.proved(wanted, proofs)
            outcome, found = self.run_checks(wanted, proofs, keys, found)
            if heard is not None:
                heard(outcome, at)
            if outcome.passed:
                break
        return outcome

    # A red check lets the others finish, so the one fix circuit reads every failure, not the first.
    # A Proof is a real pass on the same inputs, so a Suite whose every check is proved passes.
    def run_checks(self, wanted, proofs, keys, found):
        with ThreadPoolExecutor(max_workers=len(wanted)) as pool:
            running = [pool.submit(self.run_check, check) if held is None else None
                       for check, held in zip(wanted, found)]
            ran = [each.result() if each else None for each in running]
        went_red = [(check, key) for check, key, each in zip(wanted, keys, ran)
                    if each and each.status != 0]
        if self.fresh:
            proofs.forget({check.named() for check, _ in went_red},
                          {key for _, key in went_red if key})
        else:
            made = self.now().strftime("%Y-%m-%d %H:%M UTC")
            for check, key, each in zip(wanted, keys, ran):
                if key and each and each.status == 0:
                    proofs.keep(key, made, check.named())
        said = "".join(said_by(check, held, each) for check, held, each in zip(wanted, found, ran))
        passed = [held if each is None else each if each.status == 0 else None
                  for held, each in zip(found, ran)]
        red = tuple(" ".join(check.command) for check, _ in went_red)
        return Outcome(not red, said, red=red), passed

    def run_check(self, check):
        if check.image is None:
            return self.runner.run(check.command, check.folder.as_posix())
        return self.run_in_image(check)

    def run_in_image(self, check):
        tree = self.tree.as_posix()
        dockerfile = self.tree / check.image
        built = self.runner.run(["docker", "build", "--quiet", "--file", dockerfile.as_posix(),
                                 dockerfile.parent.as_posix()], tree)
        if built.status != 0:
            return built
        # The copy is the Proof's inputs and no more, so what was proved is what was tested.
        listed = self.listed_inputs(check)
        if listed.status != 0:
            return listed

        workdir = posixpath.normpath(posixpath.join(
            REPO_IN_IMAGE, check.folder.relative_to(self.tree).as_posix()))
        with tempfile.TemporaryDirectory() as stage:
            # A tracked file the worktree deleted is still listed, and the check must not see it.
            for name in {name for name in listed.out.split("\0") if name}:
                if (self.tree / name).is_file():
                    (Path(stage) / name).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(self.tree / name, Path(stage) / name)
            created = self.runner.run(["docker", "create", "--workdir", workdir,
                                       built.out.split()[-1], *check.command], tree)
            if created.status != 0:
                return created
            container = created.out.split()[-1]
            try:
                # Run from the copy itself, because docker reads a drive letter's colon as a container.
                copied = self.runner.run(["docker", "cp", "./.", container + ":" + REPO_IN_IMAGE], stage)
                if copied.status != 0:
                    return copied
                return self.runner.run(["docker", "start", "--attach", container], tree)
            finally:
                self.runner.run(["docker", "rm", "--force", container], tree)


def printed(out):
    def heard(outcome, at):
        out.write("--- suite run {}\n{}".format(at, outcome.said))
        out.flush()
    return heard


# The driver reads the Proofs this keeps, so its Suite step never repeats a Session's own run.
def main(argv, runner, out, err):
    try:
        if argv not in ([], ["--fresh"]):
            raise misuse(USAGE)
        found = runner.run(["git", "rev-parse", "--show-toplevel"])
        if found.status != 0:
            raise refusal("{} is not in a git repository, so it has no Suite file.".format(
                Path.cwd().as_posix()))
        outcome = Suite(runner, found.out.strip(), fresh=argv == ["--fresh"]).run(printed(out))
        if not outcome.ready:
            raise refusal(outcome.said.rstrip("\n"))
        if not outcome.passed:
            raise refusal("the Suite went red. What each check said is above.")
        out.write("ok    the Suite passed\n")
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


# A check can print any character, and a Windows pipe would otherwise take the locale's code page.
def speaking_any_character(stream):
    stream.reconfigure(newline="\n", encoding="utf-8")


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr))
