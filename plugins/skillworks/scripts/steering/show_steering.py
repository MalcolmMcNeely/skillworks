import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from layers.layers import Layer, repo_steering_of
from output.streams import speaking_any_character
from runner import Subprocess
from steering.steering_file import folder_files, top
from stop import Stop, misuse

STEPS_FILE = Path(__file__).with_name("steps.json")

HOW_TO = "Name a step to see the Steering it reads: show-steering <step>\n"

STEP_MAP = "https://github.com/MalcolmMcNeely/skillworks/blob/main/docs/usage/the-loop/step-map.md"

# The Sidecar hook follows imports this many hops deep, as Claude Code does, so the two walks agree.
IMPORT_HOPS = 5

# Claude Code reads an import with this pattern, so the two agree on what loads.
IMPORT = re.compile(r"(?:^|(?<=\s))@((?:[^\s\\]|\\ )+)", re.MULTILINE)

FENCE_OPEN = re.compile(r"^\s*(`{3,}|~{3,})")

CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+?\1", re.DOTALL)

ALWAYS = "always"

ON_DEMAND = "on demand"

FENCE = "---"

ROOT_FILE = "CLAUDE.md"


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


def outside_code(text):
    kept, fence = [], None
    for line in text.splitlines():
        opened = FENCE_OPEN.match(line)
        if fence is None and opened:
            fence = opened.group(1)
        elif fence is not None and line.strip().startswith(fence[0] * len(fence)):
            fence = None
        elif fence is None:
            kept.append(line)
    return CODE_SPAN.sub(" ", "\n".join(kept))


def imports_of(text):
    return [name.replace("\\ ", " ").split("#")[0] for name in IMPORT.findall(outside_code(text))]


def shown_path(path, layer, home):
    for root, prefix in ((layer.root, layer.prefix), (Path(home), "~/")):
        try:
            return prefix + Path(path).relative_to(root).as_posix()
        except ValueError:
            pass
    return Path(path).as_posix()


# Claude Code resolves an import from the folder of the file that holds it, and ~/ from the home folder.
def resolved(name, holder, layer, home):
    if name.startswith("~/"):
        path = Path(os.path.normpath(Path(home, name[2:])))
        return path, shown_path(path, Layer(Path(home), "~/", "user"), home), "user"
    path = Path(os.path.normpath(Path(holder.parent, name)))
    return path, shown_path(path, layer, home), layer.label


def walked(path, shown_as, label, layer, home, hops, seen):
    key = key_of(path)
    if key in seen:
        return []
    seen.add(key)
    text = read(path)
    found = [Section(ALWAYS, label, shown_as, text)]
    if text is None or hops == 0:
        return found
    for name in imports_of(text):
        found += walked(*resolved(name, path, layer, home), layer, home, hops - 1, seen)
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


def always(repo_steering, home, all_rules):
    seen = set()
    found = []
    for layer in [Layer(Path(home, ".claude"), "~/.claude/", "user")] + repo_steering.layers():
        found += walked(Path(layer.root, ROOT_FILE), layer.prefix + ROOT_FILE, layer.label, layer, home,
                        IMPORT_HOPS, seen)
        for rule in all_rules:
            if rule.label == layer.label and not rule.globs and key_of(rule.file) not in seen:
                seen.add(key_of(rule.file))
                found.append(Section(ALWAYS, layer.label, rule.path, rule.text))
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


def part(path, layer):
    return Section(ON_DEMAND, layer.label, path, read(Path(layer.root, path)))


def on_demand(paths, layer):
    found = []
    for path in paths:
        if path.endswith("/") and Path(layer.root, path).is_dir():
            found += [part(path + name, layer) for name in folder_files(layer.root, path)]
        else:
            found.append(part(path, layer))
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
    home = home or Path.home()
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
        repo_steering = repo_steering_of(repo)
        all_rules = path_rules(repo_steering.repo.root, home)
        sections = always(repo_steering, home, all_rules) + on_demand(step["on-demand"], repo_steering.steering)
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
