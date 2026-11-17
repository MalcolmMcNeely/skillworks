import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from output.streams import speaking_any_character
from runner import Subprocess
from steering.steering_file import folder_files, sidecar_steering, steering_root, top
from stop import Stop, misuse

STEPS_FILE = Path(__file__).with_name("steps.json")

HOW_TO = "Name a step to see the Steering it reads: show-steering <step>\n"

STEP_MAP = "https://github.com/MalcolmMcNeely/skillworks/blob/main/docs/usage/the-loop/step-map.md"

# The Sidecar hook follows imports this many hops deep, as Claude Code does, so the two walks agree.
IMPORT_HOPS = 5

IMPORT = re.compile(r"^@(\S+)$")

ALWAYS = "always"

ON_DEMAND = "on demand"

FENCE = "---"


# The label is a field and not text, so another place, such as remote Steering, adds a value and no new format.
@dataclass(frozen=True)
class Section:
    when: str
    label: str
    path: str
    text: str | None


@dataclass(frozen=True)
class Rule:
    label: str
    path: str
    file: Path
    text: str | None
    globs: list


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
    key = key_of(path)
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


def unquoted(value):
    return value.strip().strip("\"'")


# A comma inside braces belongs to the glob, as in src/**/*.{ts,tsx}, so only a comma outside them splits.
def split_outside_braces(value):
    parts, depth, start = [], 0, 0
    for at, character in enumerate(value):
        depth += {"{": 1, "}": -1}.get(character, 0)
        if character == "," and depth == 0:
            parts.append(value[start:at])
            start = at + 1
    return parts + [value[start:]]


def inline_globs(value):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [unquoted(part) for part in split_outside_braces(value) if unquoted(part)]


def globs_of(text):
    lines = text.replace("\r\n", "\n").split("\n")
    if lines[0].strip() != FENCE:
        return []
    globs, listing = [], False
    for line in lines[1:]:
        if line.strip() == FENCE:
            return globs
        if listing and line.lstrip().startswith("- "):
            globs.append(unquoted(line.lstrip()[2:]))
            continue
        key, _, value = line.partition(":")
        listing = key.strip() == "paths" and not value.strip()
        if key.strip() == "paths" and value.strip():
            globs += inline_globs(value)
    return []


def glob_pattern(glob):
    out, at = [], 0
    while at < len(glob):
        if glob.startswith("**/", at):
            out.append("(?:.*/)?")
            at += 3
        elif glob.startswith("**", at):
            out.append(".*")
            at += 2
        elif glob[at] == "*":
            out.append("[^/]*")
            at += 1
        elif glob[at] == "?":
            out.append("[^/]")
            at += 1
        elif glob[at] == "{" and closing_brace(glob, at) is not None:
            end = closing_brace(glob, at)
            out.append("(?:{})".format("|".join(
                glob_pattern(part) for part in split_outside_braces(glob[at + 1:end]))))
            at = end + 1
        else:
            out.append(re.escape(glob[at]))
            at += 1
    return "".join(out)


def closing_brace(glob, start):
    depth = 0
    for at in range(start, len(glob)):
        depth += {"{": 1, "}": -1}.get(glob[at], 0)
        if depth == 0:
            return at
    return None


def matches(rule, path):
    return any(re.fullmatch(glob_pattern(glob), path) for glob in rule.globs)


def rules(folder, prefix, label):
    if not folder.is_dir():
        return []
    found = []
    for path in sorted(folder.rglob("*.md"), key=lambda path: path.relative_to(folder).as_posix()):
        text = read(path)
        if text is not None:
            found.append(Rule(label, prefix + path.relative_to(folder).as_posix(), path, text, globs_of(text)))
    return found


def path_rules(repo, home):
    return (rules(Path(home, ".claude", "rules"), "~/.claude/rules/", "user")
            + rules(Path(repo, ".claude", "rules"), ".claude/rules/", "repo"))


def key_of(path):
    return os.path.normcase(os.path.normpath(path))


def always(repo, home, sidecar, all_rules):
    places = [(Path(home, ".claude"), "~/.claude/", "user"), (repo, "", "repo")]
    if sidecar:
        places.append((sidecar, "", "Sidecar"))
    seen = set()
    found = []
    for root, prefix, label in places:
        found += walked(root, prefix, label, "CLAUDE.md", IMPORT_HOPS, seen)
        for rule in all_rules:
            if rule.label == label and not rule.globs and key_of(rule.file) not in seen:
                seen.add(key_of(rule.file))
                found.append(Section(ALWAYS, label, rule.path, rule.text))
    return found


def may_load(all_rules):
    listed = [rule for rule in all_rules if rule.globs]
    if not listed:
        return ""
    return "\nMay load:\n\n" + "".join("  {:<9}  {}  {}\n".format(
        "[{}]".format(rule.label), rule.path, ", ".join(rule.globs)) for rule in listed)


def loaded_by(all_rules, path):
    path = path.replace("\\", "/").removeprefix("./")
    loaded = [rule for rule in all_rules if rule.globs and matches(rule, path)]
    if not loaded:
        return "\nNo path rule matches {}.\n".format(path)
    return "\nA read of {} loads:\n".format(path) + "".join(
        with_header(Section(ALWAYS, rule.label, rule.path, rule.text)) for rule in loaded)


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


def with_header(section):
    return "\n==> [{}] {} <==\n{}".format(section.label, section.path, labelled(section))


def shown(step, sections):
    lines = ["The Steering the {} step reads:\n\n".format(step)]
    for section in sections:
        lines.append("  {:<9}  {:<9}  {}{}\n".format(
            section.when, "[{}]".format(section.label), section.path,
            "  missing" if section.text is None else ""))
    for section in sections:
        if section.text is not None:
            lines.append(with_header(section))
    return "".join(lines)


def without_path(argv):
    if "--path" not in argv:
        return argv, None
    at = argv.index("--path")
    if at + 1 >= len(argv) or at == 0:
        raise misuse("Usage: show-steering <step> --path <file>\n")
    return argv[:at] + argv[at + 2:], argv[at + 1]


def main(argv, runner, out, err, where=None, home=None):
    where = where or os.getcwd()
    try:
        repo = top(runner, where)
        all_steps = steps()
        if not argv:
            out.write(step_list(all_steps))
            return 0
        argv, path = without_path(argv)
        step = next((step for step in all_steps if step["name"] == argv[0]), None)
        if step is None:
            out.write("{} is not a step.\n\n".format(argv[0]) + step_list(all_steps))
            return 1
        sidecar = sidecar_steering(repo)
        all_rules = path_rules(repo, home or Path.home())
        sections = always(repo, home or Path.home(), sidecar, all_rules) + on_demand(
            step["on-demand"], steering_root(repo), "Sidecar" if sidecar else "repo")
        out.write(shown(step["name"], sections))
        out.write(may_load(all_rules) if path is None else loaded_by(all_rules, path))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, sys.argv[1], Path.home()))
