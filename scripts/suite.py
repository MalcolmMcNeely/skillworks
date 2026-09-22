#
# The whole suite, as the README names it.
#
# Two callers, the landing and the driver, so one implementation is what keeps the
# command list and the rule that stops the run from coming to differ between them.
#
# A machine short of what the checks need is not a red suite, so readiness is proved first.

from pathlib import Path
from typing import NamedTuple


class Outcome(NamedTuple):
    passed: bool
    said: str
    # False when the checks never started, so nothing at all was proved about the work.
    ready: bool = True


# A docker client with nothing behind it exits non-zero, so only the daemon's answer proves it.
DOCKER = ["docker", "info"]


class Suite:
    def __init__(self, runner, worktree):
        self.runner = runner
        self.tree = Path(worktree)
        self.web = self.tree / "src" / "Skillworks.Studio.Web"

    def has_solution(self):
        return (self.tree / "Skillworks.slnx").is_file()

    def has_script_tests(self):
        return (self.tree / "tests" / "scripts").is_dir()

    def has_front_end(self):
        return (self.web / "package.json").is_file()

    # The README's checks, skipped where there is none, so a throwaway repository runs this.
    def checks(self):
        wanted = []
        if self.has_solution():
            wanted.append((["dotnet", "test", "Skillworks.slnx"], self.tree))
        # pytest is asked for on the command line, because the scripts carry no project file.
        if self.has_script_tests():
            wanted.append((["uv", "run", "--with", "pytest", "pytest", "tests/scripts"], self.tree))
        if self.has_front_end():
            wanted.append((["npm", "run", "typecheck"], self.web))
            wanted.append((["npm", "run", "lint"], self.web))
            wanted.append((["npm", "test"], self.web))
        return wanted

    # Read as facts, never out of a runner's output, which is reworded with every version.
    def short_of(self):
        if self.has_solution():
            asked = self.runner.run(DOCKER, self.tree.as_posix())
            if asked.status != 0:
                return ("Docker does not answer, and the API tests start Loki in a container. "
                        "Start Docker and run this again. Docker said:\n"
                        + (asked.out + asked.err))
        if self.has_script_tests() and not self.runner.found("uv"):
            return ("uv is not on PATH, and the script tests are Python carrying no project file, "
                    "so uv is what runs them. Install uv and run this again.\n")
        # A fresh worktree has nothing installed unless the work touched the front end.
        if self.has_front_end() and not (self.web / "node_modules").is_dir():
            installed = self.runner.run(["npm", "ci"], self.web.as_posix())
            if installed.status != 0:
                return ("the front end has nothing installed and npm ci would not install it. "
                        "npm said:\n" + (installed.out + installed.err))
        return ""

    def run(self):
        wanted = self.checks()
        # A checkout holding none of them is broken, and a suite that ran nothing cannot pass.
        if not wanted:
            return Outcome(
                False, "this checkout holds none of the checks the README names\n", ready=False)

        short = self.short_of()
        if short:
            return Outcome(False, short, ready=False)

        said = ""
        for args, where in wanted:
            ran = self.runner.run(args, where.as_posix())
            said += ran.out + ran.err
            if ran.status != 0:
                return Outcome(False, said)
        return Outcome(True, said)
