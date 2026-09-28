# One check, so setup's preflight and the loop can never disagree on which rules load.

from pathlib import Path

RULES_FOLDER = "docs/agents/rules"


# A rule loads into a session only through its @ import in CLAUDE.md, so a deleted line turns it off in silence.
def missing_import(top):
    folder = Path(top) / RULES_FOLDER
    if not folder.is_dir():
        return None
    try:
        imports = {line.strip() for line in (Path(top) / "CLAUDE.md").read_text(encoding="utf-8").splitlines()}
    except OSError:
        imports = set()
    for rule in sorted(path.name for path in folder.glob("*.md") if path.is_file()):
        line = "@{}/{}".format(RULES_FOLDER, rule)
        if line not in imports:
            return ("{}/{} has no import in CLAUDE.md, so it does not load into a session. "
                    "Add this line to CLAUDE.md: {}".format(RULES_FOLDER, rule, line))
    return None
