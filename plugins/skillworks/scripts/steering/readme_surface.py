# Found by its heading and not by its path, so a team whose README lives elsewhere keeps the rules.

from pathlib import Path

SURFACES_FILE = "docs/agents/surfaces.md"

HEADING = "## The README"
WHERE = "- **Where it lives:**"

FENCE = "```"


# A heading inside a fence belongs to an example, so it never opens or ends the Surface.
def readme_surface(text):
    held = None
    fenced = False
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.lstrip().startswith(FENCE):
            fenced = not fenced
        elif fenced:
            continue
        elif line.startswith("## "):
            if held is not None:
                return held
            if line.strip() == HEADING:
                held = ""
        elif held == "" and line.startswith(WHERE):
            held = line[len(WHERE):].strip().rstrip(".").strip("`")
    return held


def readme_surface_of(top):
    path = Path(top) / SURFACES_FILE
    if not path.is_file():
        return None
    return readme_surface(path.read_text(encoding="utf-8", errors="replace"))
