# The member is edited in place, so the team's layout and every other key survive and the diff is one line.

import json
import re
import sys
from pathlib import Path

from output.streams import speaking_any_character
from runner import Subprocess
from steering.allowlist import member, skip
from steering.co_authored_by import with_member
from steering.steering_file import sidecar_steering
from stop import Stop, misuse, refusal

USAGE = "usage: set-plugin-commit [<sha>]\n"

SETTINGS_FILE = ".claude/settings.json"

MARKETPLACE = "skillworks"

KINDS = {"directory": "a folder source", "file": "a file source"}

# A short sha can come to name a second commit as the repo grows, and the pin must never move by itself.
FULL_COMMIT = re.compile(r"[0-9a-f]{40}")


def settle(runner, top, asked):
    sidecar = sidecar_steering(top)
    path = Path(sidecar or top) / SETTINGS_FILE
    named = "the Sidecar's {}".format(SETTINGS_FILE) if sidecar else SETTINGS_FILE
    if asked is not None and not FULL_COMMIT.fullmatch(asked):
        raise refusal("{} is not a full commit: give all 40 hex characters. Nothing was written.".format(asked))
    text, source = marketplace_source(path, named)
    kind = source.get("source")
    if kind != "github":
        raise refusal(("{} names the Marketplace by {}, and only a GitHub source pins a commit. "
                       "Nothing was written.").format(named, KINDS.get(kind, "a {} source".format(kind))))
    new = asked or tip_of_main(runner, source)
    old = source.get("ref")
    path.write_bytes(with_ref(text, source, new).encode("utf-8"))
    return ("old commit: {}\nnew commit: {}\nwrote the new commit as the Marketplace ref in {}. Nothing was "
            "committed: review the edit, then commit and push it with git.\n").format(old or "none", new, named)


def marketplace_source(path, named):
    no_marketplace = refusal("{} holds no Marketplace named {}. Nothing was written.".format(named, MARKETPLACE))
    if not path.is_file():
        raise no_marketplace
    text = path.read_bytes().decode("utf-8")
    try:
        held = json.loads(text)
    except json.JSONDecodeError:
        raise refusal("{} is not JSON. Nothing was written.".format(named))
    marketplaces = held.get("extraKnownMarketplaces") if isinstance(held, dict) else None
    marketplace = marketplaces.get(MARKETPLACE) if isinstance(marketplaces, dict) else None
    if not isinstance(marketplace, dict) or not isinstance(marketplace.get("source"), dict):
        raise no_marketplace
    return text, marketplace["source"]


def tip_of_main(runner, source):
    url = "https://github.com/{}.git".format(source.get("repo"))
    found = runner.run(["git", "ls-remote", url, "refs/heads/main"])
    if found.status != 0 or not found.out.strip():
        raise refusal("git ls-remote could not read the tip of main from {}. Nothing was written.".format(url))
    return found.out.split()[0]


def with_ref(text, source, commit):
    marketplaces, _ = member(text, skip(text, 0), "extraKnownMarketplaces")
    marketplace, _ = member(text, marketplaces, MARKETPLACE)
    start, end = member(text, marketplace, "source")
    return text[:start] + with_member(text[start:end], source, "ref", commit) + text[end:]


def main(argv, runner, out, err):
    try:
        if len(argv) not in (1, 2):
            raise misuse(USAGE)
        found = runner.run(["git", "-C", argv[0], "rev-parse", "--show-toplevel"])
        if found.status != 0:
            raise refusal("{} is not in a git repository. Nothing was written.".format(argv[0]))
        out.write(settle(runner, found.out.strip(), argv[1] if len(argv) == 2 else None))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr))
