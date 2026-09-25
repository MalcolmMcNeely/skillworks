#
# The one way a driver reaches another program.
#
#   ran = Subprocess().run(["git", "-C", checkout, "status", "--porcelain"])
#   ran.status, ran.out, ran.err
#
# A Runner is handed to a driver rather than reached for, the way a Clock is, so a
# test can supply one that records the command a driver built and answers for it
# without starting anything. The mechanism it replaces wrote an extensionless shell
# file onto PATH, which a native Windows host ignores: Windows reads PATHEXT and
# pays no attention to a shebang.
#
# Only an entry point names the real one. Anything further in is handed the Runner
# it uses, or the seam a test needs is already past.
#
# `where` is the folder the program runs in. `env` changes the environment it gets:
# a name set to None is taken away, and any other value is put in.

import os
import shutil
import subprocess
from typing import NamedTuple


class Ran(NamedTuple):
    status: int
    out: str
    err: str


# What a shell answers for a name it could not find, so a caller reads one number either way.
NOT_FOUND = 127

PARENT_KEY = "skillworks.parent.session.id"

# Under `claude -p` a background command dies with the Session, so the slowest check must fit in the foreground.
BASH_LIMIT_MS = str(45 * 60 * 1000)


# Here and not in the driver, because the driver imports the landing script and it starts a Session too.
# Only a Session sets this ID and a Child inherits the attribute, so all below name the first Parent.
def session_changes():
    # Claude Code sets this, and the session must not read as nested in this one.
    changes = {
        "CLAUDECODE": None,
        "BASH_DEFAULT_TIMEOUT_MS": BASH_LIMIT_MS,
        "BASH_MAX_TIMEOUT_MS": BASH_LIMIT_MS,
    }
    parent = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not parent:
        return changes
    # Appended, because the attributes a developer set still have to arrive.
    held = os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "")
    named = "{}={}".format(PARENT_KEY, parent)
    changes["OTEL_RESOURCE_ATTRIBUTES"] = held + "," + named if held else named
    return changes


class Subprocess:
    # Finding a program is the first half of reaching one, so a test answers for this too.
    def found(self, name):
        return shutil.which(name) is not None

    def run(self, args, where=None, env=None):
        args = [str(a) for a in args]
        # Windows reads PATHEXT and CreateProcess does not, so npm, which is npm.CMD, is lost.
        found = shutil.which(args[0])
        if found is None:
            return Ran(NOT_FOUND, "", args[0] + ": not found\n")

        # A wait short enough to catch a wedged session is short enough to kill an honest hour-long one.
        done = subprocess.run(
            [found] + args[1:],
            cwd=where,
            env=self.environment(env),
            capture_output=True,
            # Named rather than taken from the machine, so the same bytes read the same way anywhere.
            encoding="utf-8",
            errors="replace",
        )
        return Ran(done.returncode, done.stdout, done.stderr)

    def environment(self, env):
        if not env:
            return None
        changed = dict(os.environ)
        for name, value in env.items():
            if value is None:
                changed.pop(name, None)
            else:
                changed[name] = value
        return changed
