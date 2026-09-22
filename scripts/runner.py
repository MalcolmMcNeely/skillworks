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
