# Each file is weighed against the base copy setup last wrote, so a newer Plugin's Seed replaces only what a team never edited.

import difflib
import sys
from pathlib import Path

from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: seed-steering [folder]\n"

SEEDS = Path(__file__).resolve().parents[1] / "skills" / "skillworks-setup" / "seeds"

PLACES = {
    "comments.md": "docs/agents/rules/comments.md",
    "determinism.md": "docs/agents/rules/determinism.md",
    "file-placement.md": "docs/agents/rules/file-placement.md",
    "words.md": "docs/agents/rules/words.md",
    "issue-tracker.md": "docs/agents/issue-tracker.md",
    "domain.md": "docs/agents/domain.md",
    "placement-checks.md": "docs/agents/placement-checks.md",
    "smell-baseline.md": "docs/agents/smell-baseline.md",
    "arrangement-baseline.md": "docs/agents/arrangement-baseline.md",
    "suite.json": "docs/agents/suite.json",
}

BASES = "docs/agents/.seeds"

# A copy must match its Seed byte for byte, so it cannot carry a header, and this README speaks for it.
BASES_README = """# Base copies

Setup keeps these files. Each one is the Seed exactly as setup last copied it into this repo,
under the Seed's own name. A later run of setup compares it with your file and with the Plugin's
current Seed, to tell your edits from the Plugin's.

These copies are not to be edited. Edit the Steering file in `docs/agents/` instead.
"""

WORKING_FOLDERS = [".spec-loop/", ".handoff/", ".claude/worktrees/"]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def seed(top, out):
    readme = top / BASES / "README.md"
    if not readme.exists():
        write(readme, BASES_README)
        out.write("wrote {}/README.md\n".format(BASES))

    for name, place in PLACES.items():
        wanted = (SEEDS / name).read_text(encoding="utf-8")
        target = top / place
        base = top / BASES / name
        was = base.read_text(encoding="utf-8") if base.exists() else None
        if not target.exists():
            if was is not None:
                out.write("left out {}, which you deleted\n".format(place))
                continue
            write(target, wanted)
            write(base, wanted)
            out.write("wrote {}\n".format(place))
            continue

        held = target.read_text(encoding="utf-8")
        if held == wanted:
            out.write("kept {}, the same as the seed\n".format(place))
            continue
        if held == was:
            write(target, wanted)
            write(base, wanted)
            out.write("updated {}\n".format(place))
            continue
        if was == wanted:
            out.write("kept {}, which you edited\n".format(place))
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
