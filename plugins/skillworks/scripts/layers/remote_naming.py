# Writes only the developer's own user file, so the repo and its Sidecar never name the remote.

import json
import sys
from pathlib import Path

from layers.remote import SETTINGS, USER_FOLDER, origin_of
from output.streams import speaking_any_character
from runner import Subprocess
from stop import Stop, misuse, refusal

USAGE = "usage: set-remote-steering yes [<url>] | no\n"

SHOWN_PATH = "~/{}/{}".format(USER_FOLDER, SETTINGS)


def held_settings(path):
    if not path.is_file():
        return {}
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise refusal("{} is not JSON. Nothing was written.".format(SHOWN_PATH))
    if not isinstance(held, dict) or not isinstance(held.get("repos", []), list):
        raise refusal("{} does not hold an object with a list of repos. Nothing was written.".format(SHOWN_PATH))
    return held


def answered_yes(runner, top, home, given):
    origin = origin_of(runner, top)
    if not origin:
        raise refusal("this repo has no origin, and a repo is named for remote Steering by its origin. "
                      "Nothing was written.")
    path = Path(home, USER_FOLDER, SETTINGS)
    settings = held_settings(path)
    url = settings.get("url")
    if not isinstance(url, str) or not url:
        url = None
    if url is None and not given:
        return "asks the URL of your remote Steering. Nothing was written.\n"
    # Every repo on the list reads one remote, so a new URL here would move every other repo too.
    if url is not None and given and given != url:
        raise refusal("{} already names {} as your remote Steering, and every repo on its list reads it. "
                      "Nothing was written.".format(SHOWN_PATH, url))
    repos = settings.get("repos", [])
    if url is not None and origin in repos:
        return "{} already reads your remote Steering at {}. Nothing was written.\n".format(origin, url)
    said = ""
    if url is None:
        settings["url"] = url = given
        said += "wrote {} as the URL of your remote Steering to {}\n".format(url, SHOWN_PATH)
    if origin not in repos:
        settings["repos"] = repos + [origin]
        said += "added {} to the repos that read your remote Steering in {}\n".format(origin, SHOWN_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return said


def main(argv, runner, out, err, home=None):
    try:
        yes = len(argv) in (2, 3) and argv[1] == "yes"
        if not yes and argv[1:] != ["no"]:
            raise misuse(USAGE)
        found = runner.run(["git", "-C", argv[0], "rev-parse", "--show-toplevel"])
        if found.status != 0:
            raise refusal("{} is not in a git repository. Nothing was written.".format(argv[0]))
        if not yes:
            out.write("changed nothing about your remote Steering\n")
            return 0
        given = argv[2] if len(argv) == 3 else None
        out.write(answered_yes(runner, found.out.strip(), home or Path.home(), given))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr, Path.home()))
