import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from output.streams import speaking_any_character
from runner import Subprocess
from steering.steering_file import folder_files, sidecar_steering, steering_root, top
from stop import Stop

STEPS_FILE = Path(__file__).with_name("steps.json")

HOW_TO = "Name a step to see the Steering it reads: show-steering <step>\n"

STEP_MAP = "https://github.com/MalcolmMcNeely/skillworks/blob/main/docs/usage/the-loop/step-map.md"

# The Sidecar hook follows imports this many hops deep, as Claude Code does, so the two walks agree.
IMPORT_HOPS = 5

IMPORT = re.compile(r"^@(\S+)$")

ALWAYS = "always"

ON_DEMAND = "on demand"


# The label is a field and not text, so another place, such as remote Steering, adds a value and no new format.
@dataclass(frozen=True)
class Section:
    when: str
    label: str
    path: str
    text: str | None


def steps():
    return json.loads(STEPS_FILE.read_text(encoding="utf-8"))["steps"]


def step_list(all_steps):
    width = max(len(step["name"]) for step in all_steps) + 2
    lines = [HOW_TO]
    stage = None
    for step in all_steps:
        if step["stage"] != stage:
            stage = step["stage"]
            lines.append("\n{}\n".format(stage[0].upper() + stage[1:]))
        lines.append("  {}{}\n".format(step["name"].ljust(width), step["description"]))
    lines.append("\nThe step map: {}\n".format(STEP_MAP))
    return "".join(lines)


def read(path):
    try:
        return path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return None


# An import names a path from the root of its own place, the rule the Sidecar hook follows.
def walked(root, prefix, label, name, hops, seen):
    path = Path(root, name)
    key = os.path.normcase(os.path.normpath(path))
    if key in seen:
        return []
    seen.add(key)
    text = read(path)
    found = [Section(ALWAYS, label, prefix + name, text)]
    if text is None or hops == 0:
        return found
    for line in text.splitlines():
        imported = IMPORT.match(line.strip())
        if imported:
            found += walked(root, prefix, label, imported.group(1), hops - 1, seen)
    return found


def always(repo, home, sidecar):
    places = [(Path(home, ".claude"), "~/.claude/", "user"), (repo, "", "repo")]
    if sidecar:
        places.append((sidecar, "", "Sidecar"))
    seen = set()
    found = []
    for root, prefix, label in places:
        found += walked(root, prefix, label, "CLAUDE.md", IMPORT_HOPS, seen)
    return found


def on_demand(paths, root, label):
    found = []
    for path in paths:
        folder = Path(root, path)
        if path.endswith("/") and folder.is_dir():
            found += [Section(ON_DEMAND, label, path + name, read(folder / name))
                      for name in folder_files(root, path)]
        else:
            found.append(Section(ON_DEMAND, label, path, read(Path(root, path))))
    return found


def labelled(section):
    text = section.text if section.text.endswith("\n") or not section.text else section.text + "\n"
    lines = text.splitlines(keepends=True)
    return "".join(
        "[{}]\n{}".format(section.label, line) if line.startswith("## ") else line for line in lines)


def shown(step, sections):
    lines = ["The Steering the {} step reads:\n\n".format(step)]
    for section in sections:
        lines.append("  {:<9}  {:<9}  {}{}\n".format(
            section.when, "[{}]".format(section.label), section.path,
            "  missing" if section.text is None else ""))
    for section in sections:
        if section.text is not None:
            lines.append("\n==> [{}] {} <==\n".format(section.label, section.path))
            lines.append(labelled(section))
    return "".join(lines)


def main(argv, runner, out, err, where=None, home=None):
    where = where or os.getcwd()
    try:
        repo = top(runner, where)
        all_steps = steps()
        if not argv:
            out.write(step_list(all_steps))
            return 0
        step = next((step for step in all_steps if step["name"] == argv[0]), None)
        if step is None:
            out.write("{} is not a step.\n\n".format(argv[0]) + step_list(all_steps))
            return 1
        sidecar = sidecar_steering(repo)
        sections = always(repo, home or Path.home(), sidecar) + on_demand(
            step["on-demand"], steering_root(repo), "Sidecar" if sidecar else "repo")
        out.write(shown(step["name"], sections))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1], Path.home()))
