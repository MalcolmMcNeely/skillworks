# A script and never a judge, so an invented reason is caught the same way on every run.

import re
from typing import NamedTuple

import blind_clone
from context_backfill.answer_sheet import DECISION, read_sheet

DECISIONS_FILE = "decisions.md"
FAILED = "## Failed a test"
COMMIT_MAP = ".git/filter-repo/commit-map"

CITED_COMMIT = re.compile(r"\bcommit\s+`?([0-9a-f]{7,40})\b", re.IGNORECASE)
SHORT_ID = re.compile(r"\b[0-9a-f]{7,40}\b")
QUOTED = re.compile(r'"([^"]+)"|“([^”]+)”')
ELLIPSIS = re.compile(r"\.\.\.|…")
DIFF_MARK = re.compile(r"^[-+ ]")
CITATION = re.compile("|".join((
    CITED_COMMIT.pattern,
    r"#\d+",
    r"\b(?:issue|ticket|pull request|PR|spec)\s+#?\d+",
    r"\.specs/\S",
    r"[\w.-]+(?:/[\w.-]+)*\.\w+(?::|#L|,? line )\d+",
)), re.IGNORECASE)


class Checked(NamedTuple):
    absent: list
    unquoted: list
    uncited: list


def joined(text):
    return " ".join(text.split())


def paragraphs(text):
    return [joined(part) for part in re.split(r"\n\s*\n", text) if part.strip()]


def quotes(unit):
    return [joined(first or second) for first, second in QUOTED.findall(unit)]


class History:
    def __init__(self, runner, clone):
        self.runner = runner
        self.clone = clone
        self.resolved = {}
        self.said = {}

    def git(self, *args):
        return blind_clone.git(self.runner, self.clone, *args)

    def full(self, short):
        if short not in self.resolved:
            ran = self.git("rev-parse", "--verify", "--quiet", short + "^{commit}")
            self.resolved[short] = ran.out.strip() if ran.status == 0 else None
        return self.resolved[short]

    # A quote that wraps in the diff is still a quote, so lines are joined before the search.
    def text_of(self, commit):
        if commit not in self.said:
            message = blind_clone.must(self.git("log", "-1", "--format=%B", commit), "read commit " + commit)
            diff = blind_clone.must(self.git("show", "--format=", "--no-color", "--no-ext-diff", commit),
                                    "read the diff of " + commit)
            self.said[commit] = joined(message + "\n" + "\n".join(DIFF_MARK.sub("", line)
                                                                 for line in diff.splitlines()))
        return self.said[commit]

    def holds(self, commit, quote):
        return all(part.strip() in self.text_of(commit) for part in ELLIPSIS.split(quote) if part.strip())

    def mapped(self):
        path = self.clone / COMMIT_MAP
        pairs = (line.split() for line in path.read_text(encoding="utf-8").splitlines()[1:]) if path.is_file() else []
        return {pair[0]: pair[1] for pair in pairs if len(pair) == 2}


def checked(history, sheet):
    absent, unquoted, uncited = [], [], []
    for entry in read_sheet(sheet).entries:
        cited = [short for item in entry.evidence for short in CITED_COMMIT.findall(item)]
        absent += [(entry, short) for short in dict.fromkeys(cited) if history.full(short) is None]
        if not entry.is_draft:
            continue
        for unit in paragraphs(entry.text) + [joined(item) for item in entry.evidence]:
            named = [short for short in CITED_COMMIT.findall(unit) if history.full(short)]
            unquoted += [(entry, quote, named[0]) for quote in quotes(unit)
                         if named and not any(history.holds(history.full(short), quote) for short in named)]
        if entry.letter == DECISION and not CITATION.search(entry.text):
            uncited.append(entry)
    return Checked(absent, unquoted, uncited)


def failed_commits(history, decisions):
    lines = (decisions or "").splitlines()
    stripped = [line.rstrip() for line in lines]
    if FAILED not in stripped:
        return {}
    start = stripped.index(FAILED) + 1
    end = next((at for at in range(start, len(lines)) if lines[at].startswith("## ")), len(lines))
    found = {}
    for short in SHORT_ID.findall("\n".join(lines[start:end])):
        full = history.full(short)
        if full:
            found.setdefault(full, short)
    return found


# The Statement files name commits of this repo, and the scrub gave every one a new id in the clone.
def seen_in(history, commits, failed):
    mapped = history.mapped()
    return next((failed[mapped[commit]] for commit in commits if mapped.get(commit) in failed), None)
