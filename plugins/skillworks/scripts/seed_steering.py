# A seed already there is kept and only diffed, so a team sees a newer Plugin's wording without losing its own.

import difflib
import sys
from pathlib import Path

from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: seed-steering [folder]\n"

SEEDS = Path(__file__).resolve().parents[1] / "skills" / "skillworks-setup" / "seeds"

PLACES = {
    "comments.md": ".claude/rules/comments.md",
    "determinism.md": ".claude/rules/determinism.md",
    "file-placement.md": ".claude/rules/file-placement.md",
    "words.md": ".claude/rules/words.md",
    "issue-tracker.md": "docs/agents/issue-tracker.md",
    "domain.md": "docs/agents/domain.md",
    "placement-checks.md": "docs/agents/placement-checks.md",
    "smell-baseline.md": "docs/agents/smell-baseline.md",
    "arrangement-baseline.md": "docs/agents/arrangement-baseline.md",
    "suite.json": "docs/agents/suite.json",
}

WORKING_FOLDERS = [".spec-loop/", ".handoff/", ".claude/worktrees/"]


def seed(top, out):
    for name, place in PLACES.items():
        wanted = (SEEDS / name).read_text(encoding="utf-8")
        target = top / place
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(wanted, encoding="utf-8", newline="\n")
            out.write("wrote {}\n".format(place))
            continue

        held = target.read_text(encoding="utf-8")
        if held == wanted:
            out.write("kept {}, the same as the seed\n".format(place))
            continue
        out.write("kept {}, which differs from the seed:\n".format(place))
        out.writelines(difflib.unified_diff(
            held.splitlines(keepends=True), wanted.splitlines(keepends=True),
            "yours/" + place, "seed/" + place))


def ignore_working_folders(top, out):
    path = top / ".gitignore"
    held = path.read_text(encoding="utf-8") if path.exists() else ""
    missing = [folder for folder in WORKING_FOLDERS if folder not in held.splitlines()]
    if not missing:
        return
    if held and not held.endswith("\n"):
        held += "\n"
    lines = ["# The spec loop's working folders. Transient, per-machine."] + missing
    path.write_text(held + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    out.write("added {} to .gitignore\n".format(", ".join(missing)))


def main(argv, runner, out, err):
    try:
        if len(argv) > 1:
            raise misuse(USAGE)
        where = argv[0] if argv else "."
        found = runner.run(["git", "-C", where, "rev-parse", "--show-toplevel"])
        if found.status != 0:
            raise refusal("{} is not in a git repository. Nothing was written.".format(where))
        top = Path(found.out.strip())
        seed(top, out)
        ignore_working_folders(top, out)
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    sys.stdout.reconfigure(newline="\n")
    sys.stderr.reconfigure(newline="\n")
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr))
