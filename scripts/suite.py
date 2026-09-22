#
# The whole suite, as the README names it.
#
#   passed, said = Suite(runner, worktree).run()
#
# Two callers, the landing and the driver, so one implementation is what keeps the
# command list and the rule that stops the run from coming to differ between them.

from pathlib import Path


class Suite:
    def __init__(self, runner, worktree):
        self.runner = runner
        self.tree = Path(worktree)

    # The README's checks, skipped where there is none, so a throwaway repository runs this.
    def checks(self):
        web = self.tree / "src" / "Skillworks.Studio.Web"
        wanted = []
        if (self.tree / "Skillworks.slnx").is_file():
            wanted.append((["dotnet", "test", "Skillworks.slnx"], self.tree))
        # pytest is asked for on the command line, because the scripts carry no project file.
        if (self.tree / "tests" / "scripts").is_dir():
            wanted.append((["uv", "run", "--with", "pytest", "pytest", "tests/scripts"], self.tree))
        if (web / "package.json").is_file():
            # A fresh worktree has nothing installed unless the ticket touched the front end.
            if not (web / "node_modules").is_dir():
                wanted.append((["npm", "ci"], web))
            wanted.append((["npm", "run", "typecheck"], web))
            wanted.append((["npm", "run", "lint"], web))
            wanted.append((["npm", "test"], web))
        return wanted

    def run(self):
        wanted = self.checks()
        # A checkout holding none of them is broken, and a suite that ran nothing cannot pass.
        if not wanted:
            return False, "this checkout holds none of the checks the README names\n"

        said = ""
        for args, where in wanted:
            ran = self.runner.run(args, where.as_posix())
            said += ran.out + ran.err
            if ran.status != 0:
                return False, said
        return True, said
