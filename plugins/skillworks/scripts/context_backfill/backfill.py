# The Session judges and this only reads, so every count in the fit is the same on every run.

import io
import os
import re
import sys
import time
from pathlib import Path
from typing import NamedTuple

from fetch_origin import fetch_origin
from output.streams import speaking_any_character
from runner import Subprocess
from steering.target_branch import LOOP_FILE, SPEC_MODE, target_setting, tracker_setting
from stop import Stop, misuse, refusal
from tracker.files import SPEC_FILE, SPECS, TICKETS, number_of
from tracker.github import GH_QUIET

USAGE = "usage: context-backfill check\n"

SCRATCH = ".context-backfill"

# Characters no commit message holds, so the log splits cleanly.
FIELD = "\x1f"
RECORD = "\x1e"

TRAILER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*:\s")
TICKET_TRAILER = re.compile(r"^Ticket:\s*\S", re.MULTILINE | re.IGNORECASE)
ISSUE_REFERENCE = re.compile(r"(?<![\w&/])#[0-9]+\b")

COUNTS_QUERY = ("query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) "
                "{ issues { totalCount } pullRequests { totalCount } } }")
COUNTS = '.data.repository | "\\(.issues.totalCount)\\t\\(.pullRequests.totalCount)"'

PROJECT_FILES = {
    "package.json", "pyproject.toml", "setup.py", "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
    "build.gradle.kts", "Gemfile", "composer.json", "mix.exs", "Package.swift", "CMakeLists.txt",
}
PROJECT_EXTENSIONS = (".csproj", ".fsproj", ".vbproj")

LANGUAGES = {
    ".cs": "C#", ".fs": "F#", ".vb": "Visual Basic",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".jsx": "JavaScript",
    ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".py": "Python", ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".scala": "Scala",
    ".rb": "Ruby", ".php": "PHP", ".swift": "Swift", ".ex": "Elixir", ".exs": "Elixir",
    ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++", ".hpp": "C++",
    ".sh": "Shell", ".ps1": "PowerShell", ".sql": "SQL", ".dart": "Dart", ".lua": "Lua",
}


def git(runner, where, *args):
    return runner.run(["git", "-C", where] + list(args))


def top_of(runner, where):
    found = git(runner, where, "rev-parse", "--show-toplevel")
    if found.status != 0:
        raise refusal("{} is not in a git repository. Nothing was read.".format(where))
    return found.out.strip()


# A backfill read from half a history would say the half was the whole.
def refuse_part_of_a_history(runner, top):
    if git(runner, top, "rev-parse", "--is-shallow-repository").out.strip() == "true":
        raise refusal("This clone is shallow, so it holds only the last commits of the history. "
                      "Fetch the rest, then run this again:\n  git fetch --unshallow")
    # Git names the remote that serves the missing files a promisor, and marks no other kind of clone.
    promisors = git(runner, top, "config", "--get-regexp", r"^remote\..*\.promisor$").out.split("\n")
    promised = [line.split()[0] for line in promisors if line.split()[1:] == ["true"]]
    if promised:
        remote = promised[0][len("remote."):-len(".promisor")]
        url = git(runner, top, "remote", "get-url", remote).out.strip()
        raise refusal("This clone is partial, so it fetches each old file only when it is read, and "
                      "reading the history would take hours. Make a full clone, and run this again "
                      "there:\n  git clone {}".format(url))


def target_of(runner, top):
    named = target_setting(top)
    if named != SPEC_MODE:
        return named
    # Each spec names its own branch, and the history a repo grew on is the one origin opens on.
    found = git(runner, top, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if found.status != 0:
        raise refusal("{} says spec, and origin names no default branch to read the history from. "
                      "Name it, then run this again:\n  git remote set-head origin --auto".format(LOOP_FILE))
    return found.out.strip().removeprefix("origin/")


class Commit(NamedTuple):
    at: int
    day: str
    author: str
    message: str


def commits_on(runner, top, ref):
    said = git(runner, top, "log", "--format=" + RECORD + "%at" + FIELD + "%as" + FIELD + "%aE" + FIELD + "%B", ref)
    if said.status != 0:
        raise refusal("git would not read the log of {}. git said:\n{}".format(ref, (said.out + said.err).rstrip("\n")))
    commits = []
    for record in said.out.split(RECORD)[1:]:
        at, day, author, message = record.split(FIELD, 3)
        commits.append(Commit(int(at), day, author.lower(), message.strip("\n")))
    return commits


def paragraphs(message):
    return [part.strip("\n") for part in re.split(r"\n[ \t]*\n", message) if part.strip()]


def is_trailer_block(paragraph):
    return all(TRAILER.match(line) for line in paragraph.splitlines())


# Git reads only the last paragraph as trailers, and a trailer gives no reason, so it is no body.
def has_a_body(message):
    rest = paragraphs(message)[1:]
    if rest and is_trailer_block(rest[-1]):
        rest = rest[:-1]
    return bool(rest)


def names_a_ticket(message, tracker):
    parts = paragraphs(message)
    if len(parts) > 1 and is_trailer_block(parts[-1]) and TICKET_TRAILER.search(parts[-1]):
        return True
    return tracker == "github" and bool(ISSUE_REFERENCE.search(message))


def share(count, total):
    percent = (200 * count + total) // (2 * total) if total else 0
    return "{}% ({} of {})".format(percent, count, total)


def files_on(runner, top, ref):
    return [path for path in git(runner, top, "ls-tree", "-r", "--name-only", ref).out.split("\n") if path]


def code_roots(files):
    roots = {path.rpartition("/")[0] or "." for path in files
             if path.rpartition("/")[2] in PROJECT_FILES or path.endswith(PROJECT_EXTENSIONS)}
    return ", ".join(sorted(roots)) or "none"


def languages(files):
    counts = {}
    for path in files:
        named = LANGUAGES.get(os.path.splitext(path)[1].lower())
        if named:
            counts[named] = counts.get(named, 0) + 1
    ranked = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return ", ".join("{} ({} file{})".format(name, count, "" if count == 1 else "s")
                     for name, count in ranked) or "none"


def github_tickets(runner, top):
    said = runner.run(["gh", "api", "graphql", "-f", "query=" + COUNTS_QUERY,
                       "-F", "owner={owner}", "-F", "name={repo}", "--jq", COUNTS], top, GH_QUIET)
    counts = said.out.split()
    if said.status != 0 or len(counts) != 2:
        reason = (said.err or said.out).strip().split("\n")[0] or "nothing"
        return ("none read, because gh said: {}. The history will be read from git "
                "alone.".format(reason))
    return "{}, and {} pull requests".format(*counts)


def files_tickets(files):
    specs = {path.split("/")[1] for path in files
             if path.startswith(SPECS + "/") and path.count("/") == 2 and path.endswith("/" + SPEC_FILE)}
    tickets = [path for path in files
               if path.startswith(SPECS + "/") and path.count("/") == 3
               and path.split("/")[2] == TICKETS and path.endswith(".md") and number_of(path.split("/")[3])]
    return "{}, in {} specs".format(len(tickets), len(specs))


def fit(runner, top, ref, tracker):
    commits = commits_on(runner, top, ref)
    if not commits:
        raise refusal("{} holds no commits, so there is no history to read.".format(ref))
    total = len(commits)
    oldest = min(commits, key=lambda commit: commit.at)
    newest = max(commits, key=lambda commit: commit.at)
    files = files_on(runner, top, ref)
    tickets = github_tickets(runner, top) if tracker == "github" else files_tickets(files)
    return [
        "Commits: {}".format(total),
        "First: {}".format(oldest.day),
        "Last: {}".format(newest.day),
        "Authors: {}".format(len({commit.author for commit in commits})),
        "With a body: {}".format(share(sum(has_a_body(commit.message) for commit in commits), total)),
        "Naming a ticket: {}".format(share(sum(names_a_ticket(commit.message, tracker) for commit in commits), total)),
        "Tickets: {}".format(tickets),
        "Code roots: {}".format(code_roots(files)),
        "Languages: {}".format(languages(files)),
    ]


def make_scratch_folder(top):
    (Path(top) / SCRATCH).mkdir(exist_ok=True)
    path = Path(top) / ".gitignore"
    held = path.read_text(encoding="utf-8") if path.exists() else ""
    if any(line.strip().strip("/") == SCRATCH for line in held.splitlines()):
        return "Scratch folder: {}/\n".format(SCRATCH)
    if held and not held.endswith("\n"):
        held += "\n"
    path.write_text(held + SCRATCH + "/\n", encoding="utf-8", newline="\n")
    return "Scratch folder: {}/, added to .gitignore\n".format(SCRATCH)


def check(runner, where, out, wait):
    top = top_of(runner, where)
    refuse_part_of_a_history(runner, top)
    tracker = tracker_setting(top)
    branch = target_of(runner, top)
    said = io.StringIO()
    if not fetch_origin(runner, top, branch, said, wait):
        raise refusal("origin/{} could not be fetched, so there is no history to read. git said:\n{}".format(
            branch, said.getvalue().rstrip("\n")))
    ref = "origin/" + branch
    lines = fit(runner, top, ref, tracker)
    out.write("The fit of {}:\n".format(ref) + "".join("  " + line + "\n" for line in lines) + "\n")
    out.write(make_scratch_folder(top))


def main(argv, runner, out, err, wait, where=None):
    where = where or os.getcwd()
    try:
        if argv != ["check"]:
            raise misuse(USAGE)
        check(runner, where, out, wait)
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    # python -m runs from the scripts folder, so the caller's folder is handed in first.
    sys.exit(main(sys.argv[2:], Subprocess(), sys.stdout, sys.stderr, time.sleep, sys.argv[1]))
