# Only git names the default branch, so every Tracker refuses the same branches.

from stop import refusal


def default_branch(runner, where, nothing):
    named = runner.run(["git", "-C", where, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"])
    if named.status == 0 and named.out.strip():
        return named.out.strip().removeprefix("origin/")
    # A clone that never fetched origin/HEAD, such as one made with git remote add, can still ask origin.
    asked = runner.run(["git", "-C", where, "ls-remote", "--symref", "origin", "HEAD"])
    for line in asked.out.splitlines():
        if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
            return line[len("ref: refs/heads/"):-len("\tHEAD")]
    raise refusal("origin names no default branch, so this checkout cannot be told apart from it. Name it, "
                  "then start again:\n  git remote set-head origin --auto\n" + nothing)
