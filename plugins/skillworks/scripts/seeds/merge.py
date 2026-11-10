# Text in, text out: a caller reads its own files, so any text can be weighed, such as one block of CLAUDE.md.

import difflib

YOURS = "yours"
SEED = "seed"

ASKS_OVERLAP = "overlap"
ASKS_SETTLE = "settle"


class Weighed:
    def __init__(self, done, would=None, shown=(), text=None, base=None, asks=None, used=(), allows_settled=False):
        self.done = done
        self.would = would or done
        self.shown = list(shown)
        self.text = text
        self.base = base
        self.asks = asks
        self.used = set(used)
        self.allows_settled = allows_settled


class Hunk:
    def __init__(self, start, end, lines, side):
        self.start = start
        self.end = end
        self.lines = lines
        self.side = side


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
    changes = hunks(base, YOURS, held.splitlines(keepends=True)) + hunks(base, SEED, wanted.splitlines(keepends=True))
    merged, overlaps, at = [], [], 0
    for cluster in clusters(changes):
        merged += base[at:cluster["start"]]
        at = cluster["end"]
        sides = {side: applied(base, cluster["start"], cluster["end"], [h for h in cluster["hunks"] if h.side == side])
                 for side in (YOURS, SEED)}
        touched = {hunk.side for hunk in cluster["hunks"]}
        if touched == {YOURS} or sides[YOURS] == sides[SEED]:
            merged += sides[YOURS]
        elif touched == {SEED}:
            merged += sides[SEED]
        else:
            overlaps.append(sides)
            merged += sides[chosen.get(len(overlaps), YOURS)]
    return "".join(merged + base[at:]), overlaps


def diff(place, before, after, labels):
    return list(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        labels[0] + "/" + place, labels[1] + "/" + place))


def shown_overlaps(place, overlaps):
    shown = []
    for number, sides in enumerate(overlaps, 1):
        shown.append("overlap {} in {}\n".format(number, place))
        for side, label in ((YOURS, "yours | "), (SEED, "seed  | ")):
            shown += [label + line.rstrip("\n") + "\n" for line in sides[side]] or [label.rstrip() + "\n"]
    return shown


def weigh(place, was, held, wanted, chosen, settled):
    # Every step of the loop leans on what a Seed writes, so a place the team deleted is written again.
    if held is None:
        return Weighed("wrote {}\n".format(place), "would write {}\n".format(place), text=wanted, base=wanted)

    if held == wanted:
        same = "kept {}, the same as the seed".format(place)
        if was == wanted:
            return Weighed(same + "\n")
        if was is None:
            return Weighed(same + ", and wrote its base copy\n", same + ", and would write its base copy\n",
                           base=wanted, allows_settled=True)
        return Weighed(same + ", and brought its base copy up to the seed\n",
                       same + ", and would bring its base copy up to the seed\n", base=wanted)
    if held == was:
        return Weighed("updated {}\n".format(place), "would update {}\n".format(place),
                       shown=diff(place, held, wanted, ("old-seed", "new-seed")), text=wanted, base=wanted)
    if was == wanted:
        return Weighed("kept {}, which you edited\n".format(place))
    # With no base copy the team's edits cannot be told from an older Seed, so the base waits until the team has read the diff.
    if was is None and settled:
        return Weighed("kept {}, as you settled it, and wrote its base copy\n".format(place),
                       "would keep {}, as you settled it, and write its base copy\n".format(place),
                       base=wanted, allows_settled=True)
    if was is None:
        return Weighed("kept {}, which differs from the seed:\n".format(place),
                       shown=diff(place, held, wanted, (YOURS, SEED)), asks=ASKS_SETTLE)

    merged, overlaps = merge(was, held, wanted, chosen)
    used = {number for number in chosen if number <= len(overlaps)}
    if len(used) < len(overlaps):
        return Weighed("asks {}, where your edit and the seed's change overlap:\n".format(place),
                       shown=shown_overlaps(place, overlaps), asks=ASKS_OVERLAP, used=used)
    return Weighed("merged {}, applying the seed's change:\n".format(place),
                   "would merge {}, applying the seed's change:\n".format(place),
                   shown=diff(place, held, merged, (YOURS, "merged")), text=merged, base=wanted, used=used)
