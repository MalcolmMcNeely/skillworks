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

import subprocess
from typing import NamedTuple


class Ran(NamedTuple):
    status: int
    out: str
    err: str


class Subprocess:
    def run(self, args):
        # Named rather than taken from the machine, so the same bytes read the same way anywhere.
        done = subprocess.run(
            list(args),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        return Ran(done.returncode, done.stdout, done.stderr)
