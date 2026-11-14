from pathlib import Path

from stop import refusal

SUFFIX = "-skillworks"


# Git lists the main checkout first, so every worktree of one clone finds the same Sidecar.
def main_checkout_of(runner, where):
    listed = runner.run(["git", "-C", Path(where).as_posix(), "worktree", "list", "--porcelain"])
    if listed.status != 0:
        raise refusal("{} is not in a git repository.".format(where))
    return Path(listed.out.splitlines()[0].removeprefix("worktree "))


def sidecar_of(runner, where):
    main = main_checkout_of(runner, where)
    return main.with_name(main.name + SUFFIX)
