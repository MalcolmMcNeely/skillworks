# Other tools write in docs/agents too, so only what Skillworks put there moves, and every other file stays for its tool.

import json
import re

from context_backfill.context_map import steering_file
from seeds.outcome import BASES, Outcome
from steering.steering_file import STEERING_FOLDER
from suite import SUITE_FILE

OLD_FOLDER = "docs/agents"

OLD_BASES = OLD_FOLDER + "/.seeds"


def old_place(place):
    return OLD_FOLDER + place[len(STEERING_FOLDER):]


class Move:
    def __init__(self, pairs=(), texts=None):
        self.pairs = list(pairs)
        self.texts = texts or {}
        self.came_from = {new: old for old, new in self.pairs}

    # A run that asks a question moves nothing, so each file is read where it is now and weighed where it will be.
    def read(self, top, place):
        if place in self.texts:
            return self.texts[place]
        path = top / self.came_from.get(place, place)
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def outcomes(self, runner, top):
        moves = [Outcome("moved {} to {}\n".format(old, new), "would move {} to {}\n".format(old, new),
                         does=[lambda old=old, new=new: move(runner, top, old, new)])
                 for old, new in self.pairs]
        changes = [Outcome("changed {} to name {}/\n".format(place, STEERING_FOLDER),
                           "would change {} to name {}/\n".format(place, STEERING_FOLDER),
                           writes=[(top / place, text)])
                   for place, text in self.texts.items()]
        return moves + changes


def is_tracked(runner, top, place):
    return runner.run(["git", "-C", str(top), "ls-files", "--error-unmatch", "--", place]).status == 0


def move(runner, top, old, new):
    (top / new).parent.mkdir(parents=True, exist_ok=True)
    if is_tracked(runner, top, old):
        runner.run(["git", "-C", str(top), "mv", "--", old, new])
    else:
        (top / old).rename(top / new)
    folder = (top / old).parent
    while folder != top and folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()
        folder = folder.parent


def strings_in(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings_in(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings_in(item)


def suites_own_files(top, suite_text):
    try:
        named = set(strings_in(json.loads(suite_text)))
    except ValueError:
        return []
    return sorted(place for place in named if place.startswith(OLD_FOLDER + "/") and (top / place).is_file())


def named_anew(text, pairs, mark):
    for old, new in pairs:
        text = re.sub(re.escape(mark(old)) + r"(?![\w./-])", lambda _, new=new: mark(new), text)
    return text


def planned(top, places):
    held = [place for place in places if (top / old_place(place)).is_file()]
    if not held or any((top / place).is_file() for place in places):
        return Move()
    pairs = [(old_place(place), place) for place in held]
    bases = top / OLD_BASES
    if bases.is_dir():
        pairs += [("{}/{}".format(OLD_BASES, path.name), "{}/{}".format(BASES, path.name))
                  for path in sorted(bases.iterdir()) if path.is_file()]
    suite_text = (top / old_place(SUITE_FILE)).read_text(encoding="utf-8") if SUITE_FILE in held else ""
    own = [place for place in suites_own_files(top, suite_text) if place not in dict(pairs)]
    pairs += [(place, STEERING_FOLDER + place[len(OLD_FOLDER):]) for place in own]
    unchanged = Move(pairs)
    readme = "{}/README.md".format(BASES)
    claude = steering_file(top)
    rewrites = {
        SUITE_FILE: lambda text: named_anew(text, pairs, json.dumps),
        readme: lambda text: text.replace("`{}/`".format(OLD_FOLDER), "`{}/`".format(STEERING_FOLDER)),
        claude: lambda text: named_anew(text, pairs, lambda place: "@" + place),
    }
    texts = {}
    for place, rewrite in rewrites.items():
        said = unchanged.read(top, place)
        if said is not None and rewrite(said) != said:
            texts[place] = rewrite(said)
    return Move(pairs, texts)
