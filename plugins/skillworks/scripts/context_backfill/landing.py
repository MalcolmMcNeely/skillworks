# Only text a person accepted reaches the repo, and no word or ADR already there is ever changed.

import re
from pathlib import Path

from context_backfill.answer_sheet import (ACCEPT, ANSWERS, DECISION, MAP, SHEET_FILE, WORD, bold_name, is_left,
                                           read_sheet, references, what_is_left)
from context_backfill.context_map import MAP_FILE, contexts_of, map_edits
from steering.target_branch import LOOP_FILE, SPEC_MODE, target_setting
from stop import refusal

GLOSSARY_FILE = "CONTEXT.md"
ADR_FOLDER = "docs/adr"
LANGUAGE = "## Language"
WORD_LINE = re.compile(r"^\*\*(.+?)\*\*:")
ADR_NAME = re.compile(r"^(\d+)-.*\.md$")


def git(runner, where, *args):
    return runner.run(["git", "-C", where] + list(args))


def said_by(ran):
    return (ran.out + ran.err).rstrip("\n")


def marked_sheet(top, scratch):
    path = Path(top) / scratch / SHEET_FILE
    if not path.is_file():
        raise refusal("There is no Answer sheet at {}/{}. Run /skillworks:context-backfill to write "
                      "one.".format(scratch, SHEET_FILE))
    sheet = read_sheet(path.read_text(encoding="utf-8"))
    if not any(entry.is_marked for entry in sheet.entries):
        raise refusal("Mark the sheet: write accept, reject or ? on each Answer: line of {}/{}, then run "
                      "this again. Nothing was written.".format(scratch, SHEET_FILE))
    strays = [entry.name for entry in sheet.entries if entry.is_draft and entry.answer not in ANSWERS + ("",)]
    if strays:
        raise refusal("An Answer is accept, reject or ?, and these Drafts hold another word:\n{}\nMend "
                      "them, then run this again. Nothing was written.".format(
                          "\n".join("  " + name for name in strays)))
    return path, sheet


def accepted(sheet):
    return [entry for entry in sheet.entries if entry.is_draft and entry.answer == ACCEPT]


def map_of(top, taken):
    held = Path(top) / MAP_FILE
    if held.is_file():
        return None, contexts_of(held.read_text(encoding="utf-8"))
    entry = next((entry for entry in taken if entry.letter == MAP), None)
    return entry, contexts_of(entry.text) if entry else {}


def glossaries(top, taken, contexts):
    by_name = {name.casefold(): (name, path) for name, path in contexts.items()}
    groups, strays = {}, []
    for entry in (entry for entry in taken if entry.letter == WORD):
        title, path = by_name.get(entry.context.casefold(), (None, None)) if entry.context else (
            Path(top).name, GLOSSARY_FILE)
        if path is None:
            strays.append(entry.name)
            continue
        groups.setdefault(path, (title, []))[1].append(entry)
    if strays:
        raise refusal("These Drafts name a context that no map in the repo or accepted on the sheet holds:\n{}\n"
                      "Mend the Context: line, or accept the map, then run this again. Nothing was written.".format(
                          "\n".join("  " + name for name in strays)))
    return groups


def target_of(runner, top):
    branch = target_setting(top)
    if branch == SPEC_MODE:
        raise refusal("{} says spec, and this version lands only on a named Target branch. Nothing was "
                      "written.".format(LOOP_FILE))
    here = git(runner, top, "symbolic-ref", "--quiet", "--short", "HEAD").out.strip()
    if here != branch:
        raise refusal("The Target branch is {}, and this checkout is on {}. Switch to {}, then run this "
                      "again. Nothing was written.".format(branch, here or "no branch", branch))
    return branch


def names_in(held):
    return {found.group(1).strip().casefold() for found in map(WORD_LINE.match, held.splitlines()) if found}


def with_word(held, title, entry, name):
    if not held.strip():
        return "# {}\n\n{}\n\n{}\n".format(title, LANGUAGE, entry)
    lines = held.rstrip("\n").split("\n")
    if LANGUAGE not in lines:
        return "\n".join(lines) + "\n\n{}\n\n{}\n".format(LANGUAGE, entry)
    start = lines.index(LANGUAGE) + 1
    end = next((at for at in range(start, len(lines)) if lines[at].startswith("## ")), len(lines))
    for at in range(start, end):
        found = WORD_LINE.match(lines[at])
        if found and found.group(1).strip().casefold() > name.casefold():
            return "\n".join(lines[:at] + [entry, ""] + lines[at:]) + "\n"
    last = max((at for at in range(start, end) if lines[at].strip()), default=start - 1)
    return "\n".join(lines[:last + 1] + ["", entry] + lines[last + 1:]) + "\n"


def land_words(top, glossary, title, words, out):
    path = Path(top) / glossary
    held = path.read_text(encoding="utf-8") if path.exists() else ""
    landed = 0
    for entry in words:
        name = bold_name(entry.text, entry.title)
        if name.casefold() in names_in(held):
            out.write("{} is already in {}, so it was left as it is.\n".format(name, glossary))
            continue
        held = with_word(held, title, entry.text, name)
        landed += 1
    if landed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(held, encoding="utf-8", newline="\n")
    return landed


def next_number(folder):
    numbers = [int(found.group(1)) for found in (ADR_NAME.match(path.name) for path in folder.glob("*.md")) if found]
    return max(numbers, default=0) + 1


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "decision"


def land_decision(top, entry):
    folder = Path(top) / ADR_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "{:04d}-{}.md".format(next_number(folder), slug(entry.title))
    refs = references(entry.evidence) or entry.evidence
    path.write_text("# {}\n\n{}\n\nRecovered from history: {}\n".format(entry.title, entry.text, ", ".join(refs)),
                    encoding="utf-8", newline="\n")
    return path.relative_to(top).as_posix()


# Staged and committed by path, so work elsewhere in the tree stays out of the commit.
def commit(runner, top, paths, subject):
    for args in (("add", "--") + paths, ("commit", "--quiet", "-m", subject, "--") + paths):
        ran = git(runner, top, *args)
        if ran.status != 0:
            raise refusal("git would not commit {}. git said:\n{}".format(", ".join(paths), said_by(ran)))
    return "{} {}".format(git(runner, top, "rev-parse", "--short", "HEAD").out.strip(), subject)


def push(runner, top, branch):
    for args in (("pull", "--quiet", "--rebase", "--autostash", "origin", branch),
                 ("push", "--quiet", "origin", branch)):
        ran = git(runner, top, *args)
        if ran.status != 0:
            raise refusal("The commits are made, and git would not send them to origin/{}. git said:\n{}\n"
                          "Mend it, then run: git pull --rebase origin {} && git push origin {}".format(
                              branch, said_by(ran), branch, branch))


def words_of(count):
    return "{} word{}".format(count, "" if count == 1 else "s")


def apply(runner, top, scratch, out):
    path, sheet = marked_sheet(top, scratch)
    taken = accepted(sheet)
    map_entry, contexts = map_of(top, taken)
    groups = glossaries(top, taken, contexts)
    edits = map_edits(Path(top), map_entry) if map_entry else {}
    branch = target_of(runner, top)
    if any(entry.letter == MAP for entry in taken) and not map_entry:
        out.write("{} is already there, so it was left as it is.\n".format(MAP_FILE))
    made = []
    # The map and its Steering edits go first and together, so no commit holds a map the Suite cannot read.
    if edits:
        for name, text in edits.items():
            (Path(top) / name).write_text(text, encoding="utf-8", newline="\n")
        made.append(commit(runner, top, tuple(edits), "Glossary: the map in " + MAP_FILE))
    for glossary, (title, words) in groups.items():
        landed = land_words(top, glossary, title, words, out)
        if landed:
            made.append(commit(runner, top, (glossary,), "Glossary: {} in {}".format(words_of(landed), glossary)))
    for entry in (entry for entry in taken if entry.letter == DECISION):
        made.append(commit(runner, top, (land_decision(top, entry),), "ADR: " + entry.title))
    path.write_text(what_is_left(sheet), encoding="utf-8", newline="\n")
    left = [entry.name for entry in sheet.entries if is_left(entry)]
    if made:
        out.write("Commits made:\n" + "".join("  " + line + "\n" for line in made))
    else:
        out.write("Nothing was accepted, so nothing was committed.\n")
    out.write("Left on the sheet: {}\n".format(len(left)) + "".join("  " + name + "\n" for name in left))
    if made:
        push(runner, top, branch)
        out.write("Pushed to origin/{}.\n".format(branch))
