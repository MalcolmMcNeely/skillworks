import threading
from pathlib import Path

from filelock import FileLock, Timeout

from stop import refusal

SUFFIX = "-skillworks"
LOCK = ".skillworks-lock"
WAIT_SECONDS = 1


# Git lists the main checkout first, so every worktree of one clone finds the same Sidecar.
def main_checkout_of(runner, where):
    listed = runner.run(["git", "-C", Path(where).as_posix(), "worktree", "list", "--porcelain"])
    if listed.status != 0:
        raise refusal("{} is not in a git repository.".format(where))
    return Path(listed.out.splitlines()[0].removeprefix("worktree "))


def sidecar_of(runner, where):
    main = main_checkout_of(runner, where)
    return main.with_name(main.name + SUFFIX)


class Sidecar:
    def __init__(self, runner, folder, main, clock):
        self.runner = runner
        self.folder = Path(folder)
        self.main = main
        self.clock = clock
        # Not held per thread, because the beat that takes it runs on a thread of its own.
        self.lock = FileLock(self.folder / LOCK, thread_local=False)

    @staticmethod
    def of(runner, where, clock):
        main = main_checkout_of(runner, where)
        return Sidecar(runner, main.with_name(main.name + SUFFIX), main, clock)

    def write(self, message, change):
        self.folder.mkdir(parents=True, exist_ok=True)
        self.take()
        try:
            if not (self.folder / ".git").exists():
                self.make()
            change(self.folder)
            self.git("add", "--all")
            # A change can find its work already done, and git refuses a commit that holds nothing.
            if self.git("status", "--porcelain").strip():
                self.git("commit", "--quiet", "--message", message)
        finally:
            self.lock.release()

    # The wait is on the Clock, so a test holds time still while a second writer waits its turn.
    def take(self):
        try:
            self.lock.acquire(blocking=False)
            return
        except Timeout:
            pass
        taken = threading.Event()

        def again():
            if taken.is_set():
                return
            try:
                self.lock.acquire(blocking=False)
                taken.set()
            except Timeout:
                pass

        stop = self.clock.every(WAIT_SECONDS, again)
        taken.wait()
        stop()

    # Commits as the main checkout's author, and no remote verifies a signature.
    def make(self):
        self.git("init", "--quiet")
        (self.folder / ".git" / "info").mkdir(exist_ok=True)
        with (self.folder / ".git" / "info" / "exclude").open("a", encoding="utf-8", newline="\n") as exclude:
            exclude.write("/{}\n".format(LOCK))
        for name in ("user.name", "user.email"):
            said = self.runner.run(["git", "-C", self.main.as_posix(), "config", "--get", name])
            if said.status == 0 and said.out.strip():
                self.git("config", name, said.out.strip())
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args):
        said = self.runner.run(["git", "-C", self.folder.as_posix(), *args])
        if said.status != 0:
            raise refusal("The Sidecar at {} turned down git {}: {}".format(
                self.folder.as_posix(), args[0], (said.err or said.out).strip()))
        return said.out
