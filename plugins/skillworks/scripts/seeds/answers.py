import re
from pathlib import Path

from seeds import merge
from stop import misuse, refusal

CHOICE = re.compile(r"^(.+):([0-9]+)=(yours|seed)$")

BLEND = re.compile(r"^(.+?):([0-9]+)=(.+)$")


def blended(path):
    try:
        return merge.Blend(Path(path).read_text(encoding="utf-8"))
    except OSError:
        raise refusal("the blend file {} cannot be read. Nothing was written.".format(path))


def took_an_answer(arg, rest, choices, settled, usage):
    if arg == "--keep":
        found = CHOICE.match(next(rest, ""))
        if not found:
            raise misuse(usage)
        choices[(found.group(1), int(found.group(2)))] = found.group(3)
    elif arg == "--blend":
        found = BLEND.match(next(rest, ""))
        if not found:
            raise misuse(usage)
        choices[(found.group(1), int(found.group(2)))] = blended(found.group(3))
    elif arg == "--settled":
        place = next(rest, "")
        if not place or place.startswith("--"):
            raise misuse(usage)
        settled.add(place)
    else:
        return False
    return True
