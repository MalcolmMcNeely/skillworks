# Only text a person accepted reaches the repo, and no word or ADR already there is ever changed.

import re
from pathlib import Path

from context_backfill.answer_sheet import (ACCEPT, ANSWERS, DECISION, SHEET_FILE, WORD, bold_name, is_left,
                                           read_sheet, references, what_is_left)
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
    taken = [entry for entry in sheet.entries if entry.is_draft and entry.answer == ACCEPT]
    beyond = [entry.name for entry in taken if entry.letter not in (WORD, DECISION) or entry.context]
    if beyond:
        raise refusal("This version lands words and decisions into one glossary, and these Drafts need a "
                      "map:\n{}\nNothing was written.".format("\n".join("  " + name for name in beyond)))
    return taken


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


def land_words(top, words, out):
    path = Path(top) / GLOSSARY_FILE
    held = path.read_text(encoding="utf-8") if path.exists() else ""
    landed = 0
    for entry in words:
        name = bold_name(entry.text, entry.title)
        if name.casefold() in names_in(held):
            out.write("{} is already in {}, so it was left as it is.\n".format(name, GLOSSARY_FILE))
            continue
        held = with_word(held, Path(top).name, entry.text, name)
        landed += 1
    if landed:
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
def commit(runner, top, path, subject):
    for args in (("add", "--", path), ("commit", "--quiet", "-m", subject, "--", path)):
        ran = git(runner, top, *args)
        if ran.status != 0:
            raise refusal("git would not commit {}. git said:\n{}".format(path, said_by(ran)))
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
    branch = target_of(runner, top)
    made = []
    landed = land_words(top, [entry for entry in taken if entry.letter == WORD], out)
    if landed:
        made.append(commit(runner, top, GLOSSARY_FILE, "Glossary: {} in {}".format(words_of(landed), GLOSSARY_FILE)))
    for entry in (entry for entry in taken if entry.letter == DECISION):
        made.append(commit(runner, top, land_decision(top, entry), "ADR: " + entry.title))
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
