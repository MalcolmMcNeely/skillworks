import json
from pathlib import Path

import blind_clone
from scrub_rules import ADR_FOLDER

FOLDER = blind_clone.HERE / "statements"
KINDS = ("decision", "reason", "rejected", "status")


def held_out(runner, source, pin):
    return sorted(path for _, _, path in blind_clone.entries(runner, source, pin, ADR_FOLDER)
                  if path.endswith(".md"))


def file_for(record):
    return Path(record).stem + ".json"


def problems_of(name, said, history):
    kinds = [statement["kind"] for statement in said["statements"]]
    found = ["{} holds a Statement of the kind {}, and a kind is one of {}, {}, {} or {}".format(name, kind, *KINDS)
             for kind in kinds if kind not in KINDS]
    if KINDS[0] not in kinds:
        found.append("{} holds no decision Statement".format(name))
    found.extend("{} names the commit {}, which is not in this repo at or before the pin".format(name, commit)
                 for commit in said["commits"] if commit not in history)
    return found


def problems(runner, source, pin, folder=FOLDER):
    records = held_out(runner, source, pin)
    history = set(blind_clone.must(blind_clone.git(runner, source, "rev-list", pin), "list the commits of " + pin)
                  .split())
    named = {file_for(record) for record in records}
    found = ["{} names {}{}.md, which is not held out at the pin".format(file.name, ADR_FOLDER, file.stem)
             for file in sorted(Path(folder).glob("*.json")) if file.name not in named]
    for record in records:
        file = Path(folder) / file_for(record)
        if not file.is_file():
            found.append("{} has no Statement file {}".format(record, file.name))
            continue
        found.extend(problems_of(file.name, json.loads(file.read_text(encoding="utf-8")), history))
    return found
