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
    def advance_origin(self, name):
        other = self.other_checkout()
        self.write_commit(other, name + ".txt", name, "Somebody else's " + name)
        git(other, "push", "--quiet", "origin", "main")

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


class RecordingRunner:
    # Real git runs unless a case turns it down, because branch behaviour is what may be wrong.
    def __init__(self):
        self.real = Subprocess()
        self.calls = []
        self.refusals = []

    # A mark is matched against the whole command, temporary path and all, as one line.
    def refuse(self, mark, says, times=None):
        self.refusals.append([mark, says, times])

    def run(self, args):
        args = [str(a) for a in args]
        self.calls.append(args)
        line = " ".join(args)
        for refusal in self.refusals:
            mark, says, times = refusal
            if times == 0 or mark not in line:
                continue
            if times is not None:
                refusal[2] = times - 1
            return Ran(1, "", says + "\n")
        return self.real.run(args)

    def built(self, mark):
        return [call for call in self.calls if mark in " ".join(call)]


@pytest.fixture
def repo(tmp_path):
    return Repo(tmp_path)


@pytest.fixture
def runner():
    return RecordingRunner()
