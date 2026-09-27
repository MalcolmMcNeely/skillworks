# Each file is weighed against the base copy setup last wrote, so a newer Plugin's Seed replaces only what a team never edited.

import difflib
import re
import sys
from pathlib import Path

from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: seed-steering [folder] [--keep <file>:<overlap>=yours|seed]... [--settled <file>]...\n"

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
    "loop.json": "docs/agents/loop.json",
}

BASES = "docs/agents/.seeds"

# A copy must match its Seed byte for byte, so it cannot carry a header, and this README speaks for it.
BASES_README = """# Base copies

Setup keeps these files. Each one is the Seed exactly as setup last copied it into this repo,
under the Seed's own name. A later run of setup compares it with your file and with the Plugin's
current Seed, to tell your edits from the Plugin's.

These copies are not to be edited. Edit the Steering file in `docs/agents/` instead.
"""

DEFAULT_BRANCH_PLACEHOLDER = "<default-branch>"

WORKING_FOLDERS = [".spec-loop/", ".handoff/", ".claude/worktrees/"]

CHOICE = re.compile(r"^(.+):([0-9]+)=(yours|seed)$")

KEEP = "--keep <file>:<overlap>=yours|seed for each overlap"

SETTLE = "--settled <file> for each file that differs from its seed"


class Outcome:
    def __init__(self, done, would=None, shown=(), writes=(), asks=None, used=()):
        self.done = done
        self.would = would or done
        self.shown = list(shown)
        self.writes = list(writes)
        self.asks = asks
        self.used = set(used)


class Hunk:
    def __init__(self, start, end, lines, side):
        self.start = start
        self.end = end
        self.lines = lines
        self.side = side


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def default_branch(runner, top):
    if runner.run(["git", "-C", str(top), "remote", "get-url", "origin"]).status != 0:
        current = runner.run(["git", "-C", str(top), "branch", "--show-current"]).out.strip() or "<branch>"
        raise refusal("no 'origin' remote. The loop lands every ticket by pushing to it, with either Tracker. "
                      "A bare repo on a shared drive is enough:\n"
                      "  git init --bare <shared-drive>/<repo>.git\n"
                      "  git remote add origin <shared-drive>/<repo>.git\n"
                      "  git push origin {}\n"
                      "Nothing was written.".format(current))
    found = runner.run(["git", "-C", str(top), "ls-remote", "--symref", "origin", "HEAD"])
    for line in found.out.splitlines() if found.status == 0 else []:
        if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
            return line[len("ref: refs/heads/"):-len("\tHEAD")]
    raise refusal("origin names no default branch, so loop.json has no Target branch to start from. "
                  "Nothing was written.")


def hunks(base, side, lines):
    matcher = difflib.SequenceMatcher(None, base, lines, autojunk=False)
    return [Hunk(i1, i2, lines[j1:j2], side)
            for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag != "equal"]


# Two changes that start on the same base line overlap even when one is a bare insertion, since either order would be a guess.
def clusters(changes):
    grouped = []
    for hunk in sorted(changes, key=lambda h: (h.start, h.end)):
        last = grouped[-1] if grouped else None
        if last and (hunk.start < last["end"] or any(hunk.start == held.start for held in last["hunks"])):
            last["hunks"].append(hunk)
            last["end"] = max(last["end"], hunk.end)
        else:
            grouped.append({"start": hunk.start, "end": hunk.end, "hunks": [hunk]})
    return grouped


def applied(base, start, end, hunks_of_one_side):
    lines, at = [], start
    for hunk in hunks_of_one_side:
        lines += base[at:hunk.start] + hunk.lines
        at = hunk.end
    return lines + base[at:end]


def merge(was, held, wanted, chosen):
    base = was.splitlines(keepends=True)
    changes = hunks(base, "yours", held.splitlines(keepends=True)) + hunks(base, "seed", wanted.splitlines(keepends=True))
    merged, overlaps, at = [], [], 0
    for cluster in clusters(changes):
        merged += base[at:cluster["start"]]
        at = cluster["end"]
        sides = {side: applied(base, cluster["start"], cluster["end"], [h for h in cluster["hunks"] if h.side == side])
                 for side in ("yours", "seed")}
        touched = {hunk.side for hunk in cluster["hunks"]}
        if touched == {"yours"} or sides["yours"] == sides["seed"]:
            merged += sides["yours"]
        elif touched == {"seed"}:
            merged += sides["seed"]
        else:
            overlaps.append(sides)
            merged += sides[chosen.get(len(overlaps), "yours")]
    return "".join(merged + base[at:]), overlaps


def diff(place, before, after, labels):
    return list(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        labels[0] + "/" + place, labels[1] + "/" + place))


def shown_overlaps(place, overlaps):
    shown = []
    for number, sides in enumerate(overlaps, 1):
        shown.append("overlap {} in {}\n".format(number, place))
        for side, label in (("yours", "yours | "), ("seed", "seed  | ")):
            shown += [label + line.rstrip("\n") + "\n" for line in sides[side]] or [label.rstrip() + "\n"]
    return shown


def weigh(top, default, name, place, choices, settled):
    wanted = (SEEDS / name).read_text(encoding="utf-8").replace(DEFAULT_BRANCH_PLACEHOLDER, default)
    target = top / place
    base = top / BASES / name
    was = base.read_text(encoding="utf-8") if base.exists() else None
    if not target.exists():
        if was is not None:
            return Outcome("left out {}, which you deleted\n".format(place))
        return Outcome("wrote {}\n".format(place), "would write {}\n".format(place),
                       writes=[(target, wanted), (base, wanted)])

    held = target.read_text(encoding="utf-8")
    if held == wanted:
        same = "kept {}, the same as the seed".format(place)
        if was == wanted:
            return Outcome(same + "\n")
        if was is None:
            return Outcome(same + ", and wrote its base copy\n", same + ", and would write its base copy\n",
                           writes=[(base, wanted)], used=[place])
        return Outcome(same + ", and brought its base copy up to the seed\n",
                       same + ", and would bring its base copy up to the seed\n", writes=[(base, wanted)])
    if held == was:
        return Outcome("updated {}\n".format(place), "would update {}\n".format(place),
                       shown=diff(place, held, wanted, ("old-seed", "new-seed")),
                       writes=[(target, wanted), (base, wanted)])
    if was == wanted:
        return Outcome("kept {}, which you edited\n".format(place))
    # With no base copy the team's edits cannot be told from an older Seed, so the base waits until the team has read the diff.
    if was is None and place in settled:
        return Outcome("kept {}, as you settled it, and wrote its base copy\n".format(place),
                       "would keep {}, as you settled it, and write its base copy\n".format(place),
                       writes=[(base, wanted)], used=[place])
    if was is None:
        return Outcome("kept {}, which differs from the seed:\n".format(place),
                       shown=diff(place, held, wanted, ("yours", "seed")), asks=SETTLE)

    chosen = {number: keep for (where, number), keep in choices.items() if where == place}
    merged, overlaps = merge(was, held, wanted, chosen)
    used = {(place, number) for number in chosen if number <= len(overlaps)}
    if len(used) < len(overlaps):
        return Outcome("asks {}, where your edit and the seed's change overlap:\n".format(place),
                       shown=shown_overlaps(place, overlaps), asks=KEEP, used=used)
    return Outcome("merged {}, applying the seed's change:\n".format(place),
                   "would merge {}, applying the seed's change:\n".format(place),
                   shown=diff(place, held, merged, ("yours", "merged")), writes=[(target, merged), (base, wanted)], used=used)


def seed(top, default, choices, settled):
    outcomes = []
    readme = top / BASES / "README.md"
    if not readme.exists():
        outcomes.append(Outcome("wrote {}/README.md\n".format(BASES), "would write {}/README.md\n".format(BASES),
                                writes=[(readme, BASES_README)]))
    outcomes += [weigh(top, default, name, place, choices, settled) for name, place in PLACES.items()]
    used = set().union(*(outcome.used for outcome in outcomes))
    unused = sorted(choice for choice in choices if choice not in used)
    if unused:
        raise refusal("{}:{} names no overlap. Nothing was written.".format(*unused[0]))
    unsettled = sorted(place for place in settled if place not in used)
    if unsettled:
        raise refusal("{} is not a file that differs from its seed with no base copy. Nothing was written."
                      .format(unsettled[0]))
    return outcomes


def ignore_working_folders(top):
    path = top / ".gitignore"
    held = path.read_text(encoding="utf-8") if path.exists() else ""
    missing = [folder for folder in WORKING_FOLDERS if folder not in held.splitlines()]
    if not missing:
        return []
    if held and not held.endswith("\n"):
        held += "\n"
    lines = ["# The spec loop's working folders. Transient, per-machine."] + missing
    named = ", ".join(missing)
    return [Outcome("added {} to .gitignore\n".format(named), "would add {} to .gitignore\n".format(named),
                    writes=[(path, held + "\n".join(lines) + "\n")])]


def parsed(argv):
    where, choices, settled = None, {}, set()
    rest = iter(argv)
    for arg in rest:
        if arg == "--keep":
            found = CHOICE.match(next(rest, ""))
            if not found:
                raise misuse(USAGE)
            choices[(found.group(1), int(found.group(2)))] = found.group(3)
        elif arg == "--settled":
            place = next(rest, "")
            if not place or place.startswith("--"):
                raise misuse(USAGE)
            settled.add(place)
        elif where is None and not arg.startswith("--"):
            where = arg
        else:
            raise misuse(USAGE)
    return where or ".", choices, settled


# A run that stops for a question writes nothing, so no Steering file is left half-merged while the team decides.
def report(outcomes, out):
    asking = [ask for ask in (KEEP, SETTLE) if any(outcome.asks == ask for outcome in outcomes)]
    for outcome in outcomes:
        out.write(outcome.would if asking else outcome.done)
        out.writelines(outcome.shown)
        if not asking:
            for path, text in outcome.writes:
                write(path, text)
    if asking:
        out.write("Nothing was written. Run again with {}.\n".format(" and ".join(asking)))


def main(argv, runner, out, err):
    try:
        where, choices, settled = parsed(argv)
        found = runner.run(["git", "-C", where, "rev-parse", "--show-toplevel"])
        if found.status != 0:
            raise refusal("{} is not in a git repository. Nothing was written.".format(where))
        top = Path(found.out.strip())
        report(seed(top, default_branch(runner, top), choices, settled) + ignore_working_folders(top), out)
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    sys.stdout.reconfigure(newline="\n")
    sys.stderr.reconfigure(newline="\n")
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr))
