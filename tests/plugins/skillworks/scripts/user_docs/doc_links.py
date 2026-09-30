import re

USER_DOCS = "docs/usage"
LOOP_OVERVIEW = "the-loop.md"

LINK = re.compile(r"\]\(([^)\s]+)")
HEADING = re.compile(r"^ {0,3}#{1,6}\s+(.*?)(?:\s+#+)?\s*$", re.MULTILINE)
WEB = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def prose(text):
    kept, fence = [], None
    for line in text.split("\n"):
        opened = FENCE.match(line)
        if fence is None and opened:
            fence = opened.group(1)
        elif fence is not None:
            if opened and opened.group(1)[0] == fence[0] and len(opened.group(1)) >= len(fence) \
                    and not line.strip().strip(fence[0]):
                fence = None
        else:
            kept.append(line)
    return "\n".join(kept)


def anchor(heading):
    words = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading).lower()
    return re.sub(r"[^\w\- ]", "", words).replace(" ", "-")


# The host numbers a repeated anchor from its second use on: -1, -2 and so on.
def anchors(text):
    seen = {}
    for heading in HEADING.findall(prose(text)):
        name = anchor(heading)
        count = seen.get(name, 0)
        seen[name] = count + 1
        yield name if count == 0 else "{}-{}".format(name, count)


def links(page):
    for target in LINK.findall(prose(page.read_text(encoding="utf-8"))):
        if not WEB.match(target):
            path, _, heading = target.partition("#")
            yield target, (page.parent / path).resolve() if path else page.resolve(), heading


def lands(linked, heading):
    if not linked.exists():
        return False
    return not heading or linked.is_file() and heading in set(anchors(linked.read_text(encoding="utf-8")))


def broken_links(root):
    docs = root / USER_DOCS
    broken = []
    into = docs.resolve()
    for page in sorted(root.glob("*.md")):
        for target, linked, heading in links(page):
            if (linked == into or into in linked.parents) and not lands(linked, heading):
                broken.append("{} links {}".format(page.relative_to(root).as_posix(), target))
    for page in sorted(docs.rglob("*.md")):
        for target, linked, heading in links(page):
            if not lands(linked, heading):
                broken.append("{} links {}".format(page.relative_to(root).as_posix(), target))

    loop = docs / LOOP_OVERVIEW
    folder = loop.with_suffix("")
    linked = {path for _, path, _ in links(loop)} if loop.is_file() else set()
    for page in sorted(folder.rglob("*.md")):
        if page.resolve() not in linked:
            broken.append("{} has no link from {}".format(page.relative_to(root).as_posix(),
                                                          loop.relative_to(root).as_posix()))
    return broken
