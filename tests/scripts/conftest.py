#
# Support for the python tests. Every case gets a repository of its own under the
# temporary folder pytest hands it, so no case can see what another one left behind,
# and none can touch this one.
#
# The scripts folder goes on the import path here, because a test imports the program
# it reads rather than starting it, which is what lets it hand the program a Runner.

import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from runner import Ran, Subprocess


def git(where, *args):
    done = subprocess.run(
        ["git", "-C", Path(where).as_posix()] + [str(a) for a in args],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


class Repo:
    # Enough settings that a commit works and nothing warns, on any machine.
    SETTINGS = (
        ("user.name", "Test"),
        ("user.email", "test@example.invalid"),
        ("commit.gpgsign", "false"),
        ("core.autocrlf", "false"),
        # A developer who records resolutions would otherwise have them replayed here.
        ("rerere.enabled", "false"),
        # A developer who prefers diff3 would otherwise change what a conflict measures.
        ("merge.conflictStyle", "merge"),
    )

    def __init__(self, root):
        self.root = root
        self.origin = root / "origin.git"
        self.work = root / "work"
        self.tries = root / "push-tries"
        self.checkouts = 0

        run(["git", "init", "--quiet", "--bare", "--initial-branch=main", self.origin.as_posix()])
        run(["git", "init", "--quiet", "--initial-branch=main", self.work.as_posix()])
        # Git can spell a temporary folder differently from the way pytest handed it out.
        self.work = Path(git(self.work, "rev-parse", "--show-toplevel").strip())
        self.configure(self.work)
        self.write_commit(self.work, "base.txt", "base", "Base")
        git(self.work, "remote", "add", "origin", self.origin.as_posix())
        git(self.work, "push", "--quiet", "origin", "main")

    def configure(self, where):
        for name, value in self.SETTINGS:
            git(where, "config", name, value)

    def write_commit(self, where, name, text, message):
        with (Path(where) / name).open("a", encoding="utf-8", newline="\n") as file:
            file.write(text + "\n")
        git(where, "add", "-A")
        git(where, "commit", "--quiet", "-m", message)

    # Each one is new, because on Windows a read-only object in .git turns a removal down.
    def other_checkout(self):
        self.checkouts += 1
        other = self.root / "other-{}".format(self.checkouts)
        # A clone checks out before it can be configured, so the setting goes in on the command.
        run(["git", "clone", "--quiet", "-c", "core.autocrlf=false",
             self.origin.as_posix(), other.as_posix()])
        self.configure(other)
        return other

    # A commit somebody else pushed, so only a fetch can find it.
    def push_from_elsewhere(self, name, text, message):
        other = self.other_checkout()
        self.write_commit(other, name, text, message)
        git(other, "push", "--quiet", "origin", "main")

    def advance_origin(self, name):
        self.push_from_elsewhere(name + ".txt", name, "Somebody else's " + name)

    # Counting the tries is how a bounded retry is measured and not guessed at.
    def refuse_pushes(self):
        hook = self.origin / "hooks" / "pre-receive"
        hook.write_text(
            '#!/bin/sh\necho try >> "{}"\nexit 1\n'.format(self.tries.as_posix()),
            encoding="utf-8", newline="\n")
        hook.chmod(0o755)

    def push_tries(self):
        if not self.tries.exists():
            return 0
        return len(self.tries.read_text(encoding="utf-8").splitlines())

    def group(self, spec):
        return self.work / ".claude" / "worktrees" / "spec-{}".format(spec)

    def tree(self, spec, job):
        return self.group(spec) / job

    def has_branch(self, spec, leaf):
        return self.head_of(spec, leaf) != ""

    def head_of(self, spec, leaf):
        done = subprocess.run(
            ["git", "-C", self.work.as_posix(), "rev-parse", "--verify", "--quiet",
             "spec-loop/{}/{}".format(spec, leaf)],
            capture_output=True, encoding="utf-8", errors="replace")
        return done.stdout.strip()


def run(args):
    done = subprocess.run(args, capture_output=True, encoding="utf-8", errors="replace")
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


# No test may start these for real: they reach the network, a model, a build, or this suite again.
NEVER_REAL = ("gh", "claude", "npm", "dotnet", "uv")


class Call(NamedTuple):
    args: list
    where: str
    env: dict


class RecordingRunner:
    # Real git runs unless a case turns it down, because branch behaviour is what may be wrong.
    def __init__(self):
        self.real = Subprocess()
        self.made = []
        self.refusals = []
        self.stubs = {}

    # Most cases read the words alone, and the whole call is there for the few that do not.
    @property
    def calls(self):
        return [call.args for call in self.made]

    # A stub that writes a file needs the folder its call runs in.
    @property
    def where(self):
        return self.made[-1].where if self.made else None

    def found(self, name):
        return name in self.stubs or self.real.found(name)

    # A mark is matched against the whole command, temporary path and all, as one line.
    def refuse(self, mark, says, times=None):
        self.refusals.append([mark, says, times])

    def stub(self, name, says="", status=0, does=None):
        self.stubs[name] = (says, status, does)

    def run(self, args, where=None, env=None):
        args = [str(a) for a in args]
        self.made.append(Call(args, where, env))
        line = " ".join(args)
        for refusal in self.refusals:
            mark, says, times = refusal
            if times == 0 or mark not in line:
                continue
            if times is not None:
                refusal[2] = times - 1
            return Ran(1, "", says + "\n")
        if args[0] in self.stubs:
            says, status, does = self.stubs[args[0]]
            if does is not None:
                # An answer of its own is how a stub varies with the call it was given.
                answered = does()
                if answered is not None:
                    return answered
            return Ran(status, says, "")
        assert args[0] not in NEVER_REAL, "this case would have started " + args[0] + " for real"
        return self.real.run(args, where, env)

    def built(self, mark):
        return [call for call in self.calls if mark in " ".join(call)]

    def started(self, name):
        return [call for call in self.calls if call[0] == name]


@pytest.fixture
def repo(tmp_path):
    return Repo(tmp_path)


@pytest.fixture
def runner():
    return RecordingRunner()


# The fast set is the default, so a landing is never gated on a login or on an install.
# The real set works out its lines on import, so the whole file is kept out, not its cases.
REAL_BINARIES = "real_binaries"


def pytest_addoption(parser):
    parser.addoption("--real-binaries", action="store_true",
                     help="run only the tests that start the real gh and the real claude")


def pytest_ignore_collect(collection_path, config):
    if not collection_path.name.endswith("_test.py"):
        return None
    real = collection_path.name.startswith(REAL_BINARIES)
    return real != config.getoption("--real-binaries")
