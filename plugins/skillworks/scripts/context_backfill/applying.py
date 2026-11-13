# Only text a person accepted reaches the repo, and no word or ADR already there is ever changed.

import re
from pathlib import Path
from typing import NamedTuple

from branches.default_branch import default_branch
from branches.open_the_pull_request import open_the_pull_request
from context_backfill.answer_sheet import (ACCEPT, ANSWERS, DECISION, MAP, SHEET_FILE, WORD, bold_name, read_sheet,
                                           references, what_is_left)
from context_backfill.context_map import MAP_FILE, contexts_of, map_edits
from steering.adr_folder import adr_folder
from steering.target_branch import PR_MODE, target_setting
from stop import refusal

GLOSSARY_FILE = "CONTEXT.md"
LANGUAGE = "## Language"
WORD_LINE = re.compile(r"^\*\*(.+?)\*\*:")
ADR_NAME = re.compile(r"^(\d+)-.*\.md$")
PART = "#### "
SUPERSEDED_BY_BELOW = "Status: superseded by the decision below"
SUPERSEDES_ABOVE = "This supersedes the decision above."
NOTHING_WRITTEN = "Nothing was written."


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


class Destination(NamedTuple):
    branch: str
    in_pr_mode: bool


WHAT_TO_DO = "Make a branch of your own, switch to it, and start again. "


def design_branch(runner, top):
    branch = git(runner, top, "branch", "--show-current").out.strip()
    if not branch:
        raise refusal("this checkout is on no branch. " + WHAT_TO_DO + NOTHING_WRITTEN)
    if branch == default_branch(runner, top, NOTHING_WRITTEN):
        raise refusal("this checkout is on {0}, and {0} is the default branch. {1}{2}".format(
            branch, WHAT_TO_DO, NOTHING_WRITTEN))
    return branch


def destination_of(runner, top):
    branch = target_setting(top)
    if branch == PR_MODE:
        return Destination(design_branch(runner, top), True)
    here = git(runner, top, "symbolic-ref", "--quiet", "--short", "HEAD").out.strip()
    if here != branch:
        raise refusal("The Target branch is {}, and this checkout is on {}. Switch to {}, then run this "
                      "again. {}".format(branch, here or "no branch", branch, NOTHING_WRITTEN))
    return Destination(branch, False)


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


def write_words(top, glossary, title, words, out):
    path = Path(top) / glossary
    held = path.read_text(encoding="utf-8") if path.exists() else ""
    written = 0
    for entry in words:
        name = bold_name(entry.text, entry.title)
        if name.casefold() in names_in(held):
            out.write("{} is already in {}, so it was left as it is.\n".format(name, glossary))
            continue
        held = with_word(held, title, entry.text, name)
        written += 1
    if written:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(held, encoding="utf-8", newline="\n")
    return written


class Numbering(NamedTuple):
    first: int
    width: int

    def of(self, number):
        return "{:0{}d}".format(number, self.width)


# A new ADR sorts in its place only when it is padded as wide as the team's own.
def numbering(folder):
    held = [found.group(1) for found in (ADR_NAME.match(path.name) for path in folder.glob("*.md")) if found]
    if not held:
        return Numbering(1, 4)
    highest = max(held, key=int)
    return Numbering(int(highest) + 1, len(highest))


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "decision"


def write_adr(top, folder, number, title, text, evidence):
    where = Path(top) / folder
    where.mkdir(parents=True, exist_ok=True)
    path = where / "{}-{}.md".format(number, slug(title))
    refs = references(evidence) or evidence
    path.write_text("# {}\n\n{}\n\nRecovered from history: {}\n".format(title, text, ", ".join(refs)),
                    encoding="utf-8", newline="\n")
    return path.relative_to(top).as_posix()


def parts_of(text):
    parts = []
    for line in text.split("\n"):
        if line.startswith(PART):
            parts.append((line[len(PART):].strip(), []))
        elif parts:
            parts[-1][1].append(line)
    return [(title, "\n".join(lines).strip("\n")) for title, lines in parts]


# The sheet is written before the numbers exist, so the numbers that tie the pair together are written here.
def superseded(text, by):
    return text.replace(SUPERSEDED_BY_BELOW, "Status: superseded by ADR-" + by)


def superseding(text, old):
    return text.replace(SUPERSEDES_ABOVE, "This supersedes ADR {}.".format(old))


def write_decisions(runner, top, folder, entry):
    parts = parts_of(entry.text)
    numbers = numbering(Path(top) / folder)
    first, second = numbers.of(numbers.first), numbers.of(numbers.first + 1)
    if len(parts) != 2:
        return [commit(runner, top, (write_adr(top, folder, first, entry.title, entry.text, entry.evidence),),
                       "ADR: " + entry.title)]
    (old_title, old_text), (new_title, new_text) = parts
    return [commit(runner, top, (write_adr(top, folder, first, old_title, superseded(old_text, second),
                                           entry.evidence),), "ADR: " + old_title),
            commit(runner, top, (write_adr(top, folder, second, new_title, superseding(new_text, first),
                                           entry.evidence),), "ADR: " + new_title)]


# Staged and committed by path, so work elsewhere in the tree stays out of the commit.
def commit(runner, top, paths, subject):
    for args in (("add", "--") + paths, ("commit", "--quiet", "-m", subject, "--") + paths):
        ran = git(runner, top, *args)
        if ran.status != 0:
            raise refusal("git would not commit {}. git said:\n{}".format(", ".join(paths), said_by(ran)))
    return "{} {}".format(git(runner, top, "rev-parse", "--short", "HEAD").out.strip(), subject)


def on_origin(runner, top, branch):
    return git(runner, top, "ls-remote", "--quiet", "--exit-code", "--heads", "origin", branch).status == 0


def push(runner, top, destination, out):
    branch = destination.branch
    # A developer's branch may not be on origin yet, and then there is nothing to pull.
    pull = ("pull", "--quiet", "--rebase", "--autostash", "origin", branch)
    steps = ((pull,) if on_origin(runner, top, branch) else ()) + (("push", "--quiet", "-u", "origin", branch),)
    for args in steps:
        ran = git(runner, top, *args)
        if ran.status != 0:
            raise refusal("The commits are made, and git would not send them to origin/{}. git said:\n{}\n"
                          "Mend it, then run: git pull --rebase origin {} && git push -u origin {}".format(
                              branch, said_by(ran), branch, branch))
    out.write("Pushed to origin/{}.\n".format(branch))
    if destination.in_pr_mode:
        out.write(open_the_pull_request(branch) + "\n")


def words_of(count):
    return "{} word{}".format(count, "" if count == 1 else "s")


def apply(runner, top, scratch, out):
    path, sheet = marked_sheet(top, scratch)
    taken = accepted(sheet)
    map_entry, contexts = map_of(top, taken)
    groups = glossaries(top, taken, contexts)
    edits = map_edits(Path(top), map_entry) if map_entry else {}
    folder = adr_folder(top) if any(entry.letter == DECISION for entry in taken) else None
    destination = destination_of(runner, top)
    if any(entry.letter == MAP for entry in taken) and not map_entry:
        out.write("{} is already there, so it was left as it is.\n".format(MAP_FILE))
    made = []
    # The map and its Steering edits go first and together, so no commit holds a map the Suite cannot read.
    if edits:
        for edited, text in edits.items():
            edited.write_text(text, encoding="utf-8", newline="\n")
        in_repo = tuple(edited.relative_to(top).as_posix() for edited in edits if edited.is_relative_to(Path(top)))
        elsewhere = [edited.as_posix() for edited in edits if not edited.is_relative_to(Path(top))]
        if elsewhere:
            out.write("Sidecar Steering is on, so the map's Steering edits went to the Sidecar, and no commit holds "
                      "them:\n" + "".join("  " + name + "\n" for name in elsewhere))
        made.append(commit(runner, top, in_repo, "Glossary: the map in " + MAP_FILE))
    for glossary, (title, words) in groups.items():
        written = write_words(top, glossary, title, words, out)
        if written:
            made.append(commit(runner, top, (glossary,), "Glossary: {} in {}".format(words_of(written), glossary)))
    for entry in (entry for entry in taken if entry.letter == DECISION):
        made += write_decisions(runner, top, folder, entry)
    rewritten = what_is_left(sheet)
    path.write_text(rewritten, encoding="utf-8", newline="\n")
    left = [entry.name for entry in read_sheet(rewritten).entries]
    if made:
        out.write("Commits made:\n" + "".join("  " + line + "\n" for line in made))
    else:
        out.write("Nothing was accepted, so nothing was committed.\n")
    out.write("Left on the sheet: {}\n".format(len(left)) + "".join("  " + name + "\n" for name in left))
    if made:
        push(runner, top, destination, out)
