# Built in an index of its own, so the developer's checkout and its index are untouched until the branch moves.

import tempfile
from pathlib import Path
from typing import NamedTuple

from stop import refusal

PREFIX = "skillworks/spec/"

GRILL_SUBJECTS = ("Glossary:", "ADR:")

GRILL = "the grill"

# Characters no commit hash, name or trailer holds, so the log splits cleanly.
FIELD = "\x1f"
RECORD = "\x1e"

# The trailers come last, because their separator is the field separator too.
LOG_FORMAT = FIELD.join(("%H", "%h", "%s", "%an", "%ae", "%aI",
                         "%(trailers:key=Ticket,valueonly,separator=%x1f)")) + RECORD

FIXED_FIELDS = 6


class Commit(NamedTuple):
    hash: str
    short: str
    subject: str
    name: str
    email: str
    date: str
    tickets: frozenset


class Written(NamedTuple):
    short: str
    subject: str
    source: str


class LeftFile(NamedTuple):
    path: str
    source: str


class NotApplied(NamedTuple):
    source: str
    files: list


class Exported(NamedTuple):
    branch: str
    tip: str
    written: list
    left: list
    left_files: list
    not_applied: NotApplied | None


class DoesNotApply(Exception):
    def __init__(self, files):
        super().__init__(files)
        self.files = files


# A pathspec glob, so a file whose name holds a glob character still names itself alone.
def literal_glob(name):
    return "".join("\\" + c if c in "\\*?[" else c for c in name)


def export_branch_of(target):
    if not target.startswith(PREFIX):
        raise refusal("the Target branch {} does not start with {}, so no Export branch can be read "
                      "from its name. Nothing was exported.".format(target, PREFIX))
    return target[len(PREFIX):]


class Export:
    def __init__(self, runner, where, tracker, spec):
        self.runner = runner
        self.where = where
        self.tracker = tracker
        self.spec = spec
        self.env = None
        self.steering_files = []
        self.left_files = []

    def git(self, *args):
        return self.runner.run(["git", "-C", self.where] + [str(a) for a in args], None, self.env)

    def must(self, why, *args):
        ran = self.git(*args)
        if ran.status != 0:
            raise refusal("{}, so nothing was exported. git said:\n{}".format(
                why, (ran.out + ran.err).rstrip("\n")))
        return ran.out.strip()

    def commits_after(self, tip, target):
        said = self.must("git would not list the commits on origin/" + target,
                         "log", "--reverse", "--format=" + LOG_FORMAT, "{}..origin/{}".format(tip, target))
        commits = []
        for record in said.split(RECORD):
            fields = record.strip("\n").split(FIELD)
            if len(fields) <= FIXED_FIELDS:
                continue
            trailers = frozenset(value.strip() for value in fields[FIXED_FIELDS:] if value.strip())
            commits.append(Commit(*fields[:FIXED_FIELDS], trailers))
        return commits

    # A ticket's place is where its first commit sits, so the tickets come in the order they Landed.
    def grouped(self, commits):
        named = {self.tracker.trailer(ticket): ticket for ticket in self.tracker.tickets(self.spec)}
        grill, tickets, left = [], {}, []
        for commit in commits:
            owned = [named[trailer] for trailer in sorted(commit.tickets) if trailer in named]
            if owned:
                tickets.setdefault(owned[0], []).append(commit)
            elif not commit.tickets and commit.subject.startswith(GRILL_SUBJECTS):
                grill.append(commit)
            else:
                left.append(commit)
        return grill, tickets, left

    # The -z goes straight after the command, because after a "--" git reads it as a path.
    def file_names(self, why, command, *args):
        return [name for name in self.must(why, command, "-z", *args).split("\0") if name]

    # A file only a left-out commit brought in is Steering, so no ticket's change can carry it back.
    def created_by(self, left, tip):
        on_tip = set(self.file_names("git would not list the files of the Export branch",
                                     "ls-tree", "-r", "--name-only", tip))
        created = []
        for commit in left:
            for name in self.file_names("git would not read the change of " + commit.short,
                                        "diff-tree", "--root", "-r", "--no-commit-id", "--name-only",
                                        "--no-renames", "--diff-filter=A", commit.hash):
                if name not in on_tip and name not in created:
                    created.append(name)
        return created

    def note_left_files(self, commit, source):
        if not self.steering_files:
            return
        for name in self.file_names("git would not read the change of " + commit.short,
                                    "diff", "--name-only", "--no-renames", commit.hash + "^", commit.hash,
                                    "--", *(":(literal)" + name for name in self.steering_files)):
            if LeftFile(name, source) not in self.left_files:
                self.left_files.append(LeftFile(name, source))

    # Each file is tried alone, so the stop names every file that does not apply and none that does.
    def not_applying(self, patch):
        names = [line.split("\t", 2)[2] for line in self.file_names(
            "git would not read the files of " + patch, "apply", "--numstat", patch)]
        return [name for name in names
                if self.git("apply", "--cached", "--check", "--include=" + literal_glob(name), patch).status != 0]

    # Each commit's own change is applied, so a ticket brings its edit and never a whole file.
    def apply(self, commit, held):
        patch = (Path(held) / "change.patch").as_posix()
        self.must("git would not read the change of " + commit.short,
                  "diff", "--binary", "--full-index", "--no-renames", "--output=" + patch,
                  commit.hash + "^", commit.hash, "--", ".", ":(exclude).specs",
                  *(":(exclude,literal)" + name for name in self.steering_files))
        if Path(patch).stat().st_size == 0:
            return
        if self.git("apply", "--cached", "--binary", patch).status != 0:
            raise DoesNotApply(self.not_applying(patch))

    def committed(self, parent, commits, subject, source, held):
        for commit in commits:
            self.apply(commit, held)
        tree = self.must("git would not write the tree of " + source, "write-tree")
        if tree == self.must("git would not read the tree of " + parent, "rev-parse", parent + "^{tree}"):
            return parent, None
        first = commits[0]
        index = self.env
        self.env = dict(index, GIT_AUTHOR_NAME=first.name, GIT_AUTHOR_EMAIL=first.email,
                        GIT_AUTHOR_DATE=first.date)
        try:
            made = self.must("git would not write the commit for " + source,
                             "commit-tree", tree, "-p", parent, "-m", subject)
        finally:
            self.env = index
        return made, Written(self.must("git would not name " + made, "rev-parse", "--short", made),
                             subject, source)

    def checked_out_in(self, branch):
        said = self.must("git would not list the worktrees", "worktree", "list", "--porcelain")
        tree = None
        for line in said.split("\n"):
            if line.startswith("worktree "):
                tree = line[len("worktree "):]
            elif line == "branch refs/heads/" + branch:
                return tree
        return None

    # Moved once, and through the checkout that holds it, so its files follow the branch.
    def move(self, branch, tip, made):
        tree = self.checked_out_in(branch)
        if tree is None:
            self.must("the Export branch {} would not move".format(branch),
                      "update-ref", "refs/heads/" + branch, made, tip)
            return
        ran = self.runner.run(["git", "-C", tree, "merge", "--ff-only", "--quiet", made])
        if ran.status != 0:
            raise refusal("the Export branch {} is checked out at {} and would not move to {}, so nothing "
                          "was exported. git said:\n{}".format(branch, tree, made, (ran.out + ran.err).rstrip("\n")))

    def run(self, target, spec_title):
        branch = export_branch_of(target)
        tip = self.must("the Export branch {} is not a branch in this checkout".format(branch),
                        "rev-parse", "--verify", "--quiet", "refs/heads/" + branch + "^{commit}")
        grill, tickets, left = self.grouped(self.commits_after(tip, target))
        self.steering_files = self.created_by(left, tip)
        parts = ([(grill, spec_title.removeprefix("SPEC: "), GRILL)] if grill else []) + [
            (commits, self.tracker.title(ticket).removeprefix("TICKET: "), self.tracker.named(ticket))
            for ticket, commits in tickets.items()]

        # Read before any commit is built, so a stop still lists every file the Export would leave out.
        for commits, _, source in parts:
            for commit in commits:
                self.note_left_files(commit, source)

        written = []
        parent = tip
        with tempfile.TemporaryDirectory() as held:
            self.env = {"GIT_INDEX_FILE": (Path(held) / "index").as_posix()}
            try:
                self.must("git would not read the Export branch " + branch, "read-tree", tip)
                for commits, subject, source in parts:
                    try:
                        parent, made = self.committed(parent, commits, subject, source, held)
                    except DoesNotApply as failed:
                        return Exported(branch, tip, [], left, self.left_files,
                                        NotApplied(source, failed.files))
                    if made:
                        written.append(made)
            finally:
                self.env = None
        if parent != tip:
            self.move(branch, tip, parent)
        return Exported(branch, tip, written, left, self.left_files, None)


def export(runner, where, target, tracker, spec, spec_title):
    return Export(runner, where, tracker, spec).run(target, spec_title)
