# Settings are read in Python so no machine needs node.
# A check here warns and never fails: a team may have chosen otherwise on purpose.

import json
import os
import re
import sys
from pathlib import Path

SETTINGS_FILE = ".claude/settings.json"
OWN_PLUGIN = "skillworks@"
STYLES_FOLDER = "output-styles"

FRONT_MATTER = re.compile(r"---\r?\n(.*?)\r?\n---", re.S)
FORCES = re.compile(r"^force-for-plugin:\s*true\s*$", re.M)


def ok(out, said):
    out.write("ok    " + said + "\n")


def warn(out, said):
    out.write("warn  " + said + "\n")


# A file that cannot be read says nothing about the setting, so it counts as not false.
def auto_memory_off(top):
    try:
        held = json.loads((Path(top) / SETTINGS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(held, dict) and held.get("autoMemoryEnabled") is False


def check_auto_memory(top, out):
    if auto_memory_off(top):
        ok(out, "auto-memory off")
    else:
        warn(out, "autoMemoryEnabled is not false in {}, so each session loads memory files only this "
                  "machine holds. Add \"autoMemoryEnabled\": false to that file.".format(SETTINGS_FILE))


# Claude Code names a project by the path it was opened in, and Windows does not tell letter case apart.
def path_key(path):
    whole = os.path.abspath(path)
    return whole.lower() if sys.platform == "win32" else whole


def style_files(where):
    if not where.exists():
        return []
    if not where.is_dir():
        return [where]
    return sorted(where.glob("*.md"))


def forces(style):
    front = FRONT_MATTER.match(style.read_text(encoding="utf-8"))
    return front is not None and FORCES.search(front.group(1)) is not None


# A manifest that is missing or unreadable still leaves the folder every plugin may use.
def style_places(home):
    places = [STYLES_FOLDER]
    try:
        manifest = json.loads((home / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        named = manifest.get("outputStyles")
        if named is not None:
            places += named if isinstance(named, list) else [named]
    except (OSError, ValueError, AttributeError):
        pass
    return places


def forcing_plugins(plugins, top):
    here = path_key(top)
    forcing = []
    for plugin in plugins:
        if not plugin.get("enabled") or plugin["id"].startswith(OWN_PLUGIN):
            continue
        if plugin.get("projectPath") and path_key(plugin["projectPath"]) != here:
            continue
        home = Path(plugin["installPath"])
        files = [style for place in style_places(home) for style in style_files(home / place)]
        if any(forces(style) for style in files):
            forcing.append(plugin["id"])
    return forcing


def check_output_styles(runner, top, out):
    listed = runner.run(["claude", "plugin", "list", "--json"])
    try:
        if listed.status != 0:
            raise ValueError(listed.err)
        forcing = forcing_plugins(json.loads(listed.out), top)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        warn(out, "could not check which plugins force an output style, because claude plugin list --json "
                  "gave nothing the preflight could read.")
        return
    for plugin in forcing:
        warn(out, "{} also forces an output style. When two plugins force one the first loaded wins, so the "
                  "loop's reports may not come in the skillworks style.".format(plugin))
    if not forcing:
        ok(out, "no other plugin forces an output style")


def check_configuration(runner, top, out):
    check_auto_memory(top, out)
    check_output_styles(runner, top, out)
