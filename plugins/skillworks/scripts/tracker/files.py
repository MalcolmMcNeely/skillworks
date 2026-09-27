# Reads only the remote's Target branch, so unpushed work cannot change what the loop starts.

import io
import tempfile
import time
from pathlib import Path
from typing import NamedTuple

from fetch_origin import fetch_origin
from stop import is_a_number, refusal

SPECS = ".specs"
SPEC_FILE = "spec.md"
TICKETS = "tickets"
FENCE = "---"
CLAIMED_BY = "claimed-by"
STATUS = "status"
CLOSED = "closed"
CLOSING_NOTE = "## Closing note"

# Every remote branch at once, because in spec mode the spec's own folder says which one is its.
EVERY_BRANCH = "*"

# Enough for several loops starting at once, few enough that a remote refusing for another reason cannot spin.
PUSH_ATTEMPTS = 5

LOST_RACE = ("[rejected]", "fetch first", "non-fast-forward", "cannot lock ref")


class Ticket(NamedTuple):
    number: str
    status: str
    blocked_by: list
    claimed_by: str
    title: str
    path: str


class Spec(NamedTuple):
    status: str
    title: str
    tickets: list


def number_of(name):
    lead = name.split("-", 1)[0]
    return str(int(lead)) if is_a_number(lead) else ""


def listed(said):
    return [line for line in said.split("\n") if line != ""]


def bare(value):
    return value.strip().strip("\"'")


def as_list(value):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [bare(item) for item in value.split(",") if bare(item)]


def frontmatter(text):
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != FENCE:
        return {}, "\n".join(lines)
    held = {}
    key = None
    for at, line in enumerate(lines[1:], start=1):
        if line.strip() == FENCE:
            return held, "\n".join(lines[at + 1:])
        if line.lstrip().startswith("- ") and key is not None:
            held[key] = (held[key] if isinstance(held[key], list) else []) + [bare(line.lstrip()[2:])]
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        held[key] = as_list(value) if value.startswith("[") else bare(value)
    return {}, "\n".join(lines)


def with_field(text, key, value):
    ending = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(ending)
    line = "{}: {}".format(key, value)
    closing = next((at for at, each in enumerate(lines) if at > 0 and each.strip() == FENCE), None)
    if not lines or lines[0].strip() != FENCE or closing is None:
        return ending.join([FENCE, line, FENCE] + lines)
    held = [at for at in range(1, closing) if lines[at].partition(":")[0].strip() == key]
    if held:
        lines[held[0]] = line
    else:
        lines.insert(closing, line)
    return ending.join(lines)


def closing_note_in(body):
    lines = body.split("\n")
    stripped = [line.strip() for line in lines]
    if CLOSING_NOTE not in stripped:
        return ""
    return "\n".join(lines[stripped.index(CLOSING_NOTE) + 1:]).strip("\n")


def heading(body, otherwise):
    return next((line[2:].strip() for line in body.split("\n") if line.startswith("# ")), otherwise)


def as_numbers(value):
    held = value if isinstance(value, list) else as_list(value)
    return [str(int(item)) if is_a_number(item) else item for item in held]


class Files:
    # The close is in the commit that Lands, so no rebase can leave it naming a commit on no branch.
    close_names_commits = False

    # A target of None is spec mode, where each spec's frontmatter names its own branch.
    def __init__(self, runner, where, target, spec=None, wait=time.sleep):
        self.runner = runner
        self.where = str(where)
        self.target = target
        self.spec = spec
        self.wait = wait
        self.repo = ""
        self.me = ""
        self.branches = {}
        # Keyed by the commit read, so a ref that has not moved is not read again.
        self.read_at = {}

    def git(self, *args, env=None):
        return self.runner.run(["git", "-C", self.where] + [str(a) for a in args], None, env)

    def connect(self):
        found = self.git("remote", "get-url", "origin")
        if found.status != 0:
            return "this repo has no remote named origin, and the files Tracker reads from it"
        self.repo = found.out.strip()
        self.me = self.git("config", "user.email").out.strip()
        if not self.me:
            return "git has no user.email, and the files Tracker claims each ticket in that name"
        return ""

    def fetched(self, branch):
        said = io.StringIO()
        if not fetch_origin(self.runner, self.where, branch, said, self.wait):
            raise refusal("The files Tracker could not fetch {} from origin, so it has nothing to "
                          "read. git said:\n{}".format(branch, said.getvalue().rstrip("\n")))

    def shown(self, ref, path):
        return self.git("show", "{}:{}".format(ref, path)).out

    def folder_on(self, ref, spec):
        held = self.git("ls-tree", "--name-only", ref, SPECS + "/").out
        named = [path for path in listed(held) if number_of(path.rsplit("/", 1)[-1]) == spec]
        return named[0] if len(named) == 1 else ""

    def branch_of(self, spec):
        if self.target is not None:
            return self.target
        if spec not in self.branches:
            self.branches[spec] = self.branch_named_by(spec)
        return self.branches[spec]

    def branch_named_by(self, spec):
        self.fetched(EVERY_BRANCH)
        refs = listed(self.git("for-each-ref", "--format=%(refname:strip=3)",
                               "refs/remotes/origin").out)
        found = []
        for branch in refs:
            if branch == "HEAD":
                continue
            folder = self.folder_on("origin/" + branch, spec)
            if not folder:
                continue
            held, _ = frontmatter(self.shown("origin/" + branch, folder + "/" + SPEC_FILE))
            if held.get("branch") == branch:
                found.append(branch)
        if len(found) == 1:
            return found[0]
        if not found:
            raise refusal("No branch on origin holds the folder of spec {} with that branch named "
                          "as branch in its spec.md frontmatter. Run to-spec, which writes it, or "
                          "add it by hand.".format(spec))
        raise refusal("Spec {} names its own branch on more than one branch of origin: {}. Keep "
                      "it on one.".format(spec, ", ".join(found)))

    def read(self, spec):
        if spec is None:
            raise refusal("The files Tracker numbers each ticket inside its spec, and it was given "
                          "no spec.")
        branch = self.branch_of(spec)
        self.fetched(branch)
        ref = "origin/" + branch
        commit = self.git("rev-parse", ref).out.strip()
        if (commit, spec) not in self.read_at:
            self.read_at[(commit, spec)] = self.spec_on(ref, spec)
        return self.read_at[(commit, spec)]

    def spec_on(self, ref, spec):
        folder = self.folder_on(ref, spec)
        if not folder:
            return None
        held, body = frontmatter(self.shown(ref, folder + "/" + SPEC_FILE))
        tickets = []
        paths = listed(self.git("ls-tree", "--name-only", ref, folder + "/" + TICKETS + "/").out)
        for path in paths:
            name = path.rsplit("/", 1)[-1]
            number = number_of(name)
            if not number or not name.endswith(".md"):
                continue
            ticket, text = frontmatter(self.shown(ref, path))
            tickets.append(Ticket(number, ticket.get("status", ""),
                                  as_numbers(ticket.get("blocked-by", [])),
                                  ticket.get(CLAIMED_BY, ""), heading(text, name[:-3]), path))
        tickets.sort(key=lambda ticket: int(ticket.number))
        return Spec(held.get("status", ""), heading(body, folder.rsplit("/", 1)[-1]), tickets)

    def ticket(self, number):
        held = self.read(self.spec)
        found = [ticket for ticket in held.tickets if ticket.number == number] if held else []
        return found[0] if found else None

    def spec_state(self, spec):
        held = self.read(spec)
        return held.status if held else None

    def spec_title(self, spec):
        held = self.read(spec)
        return held.title if held else ""

    def state(self, ticket):
        held = self.ticket(ticket)
        return held.status if held else None

    def title(self, ticket):
        held = self.ticket(ticket)
        return held.title if held else ""

    def tickets(self, spec):
        held = self.read(spec)
        return [ticket.number for ticket in held.tickets] if held else []

    def open_tickets(self, spec):
        held = self.read(spec)
        return [ticket.number for ticket in held.tickets if ticket.status == "open"] if held else []

    def ticket_rows(self, spec):
        held = self.read(spec)
        return [(ticket.number, ticket.status, ticket.title) for ticket in held.tickets] if held else []

    # A blocker with no file is not known to be closed, so it counts as open.
    def open_blockers(self, ticket):
        held = self.read(self.spec)
        closed = {each.number for each in held.tickets if each.status == "closed"} if held else set()
        found = self.ticket(ticket)
        return sum(1 for blocker in found.blocked_by if blocker not in closed) if found else None

    def claimed_by_others(self, ticket):
        found = self.ticket(ticket)
        if found is None or found.claimed_by == self.me:
            return ""
        return found.claimed_by

    # A ticket number is local to its spec, so the spec comes with it wherever it is named.
    def reference(self, ticket):
        if self.spec is None:
            raise refusal("The files Tracker numbers each ticket inside its spec, and it was "
                          "given no spec to name ticket {} by.".format(ticket))
        return "{}/{}".format(self.spec, ticket)

    def trailer(self, ticket):
        return self.reference(ticket)

    # Read in the worktree, because the close is made there and reaches origin only as it Lands.
    def state_in(self, ticket, worktree):
        found = self.ticket(ticket)
        if found is None:
            return None
        try:
            text = (Path(worktree) / found.path).read_text(encoding="utf-8")
        except OSError:
            return None
        return frontmatter(text)[0].get(STATUS, "")

    def close_asked(self, ticket):
        found = self.ticket(ticket)
        named = found.path if found else "the file of ticket " + self.reference(ticket)
        return ("Ticket {} is still open in {}. Set status: closed in its frontmatter and add its "
                "closing note under {}, in the same commit as the code.\n".format(
                    self.reference(ticket), named, CLOSING_NOTE))

    def closing_note(self, trailer):
        spec, _, ticket = trailer.partition("/")
        if not is_a_number(spec) or not is_a_number(ticket):
            return None
        spec, ticket = str(int(spec)), str(int(ticket))
        held = self.read(spec)
        found = [each for each in held.tickets if each.number == ticket] if held else []
        if not found:
            return None
        ref = "origin/" + self.branch_of(spec)
        return closing_note_in(frontmatter(self.shown(ref, found[0].path))[1])

    # A ticket closes only in the commit that Lands, so one that failed to Land was never closed.
    def reopen(self, ticket):
        return False

    # The remote takes only the first push on top of a read, so the loser reads again.
    def claim(self, ticket, wait):
        for _ in range(PUSH_ATTEMPTS):
            found = self.ticket(ticket)
            if found is None:
                raise refusal("Ticket {} of spec {} has no file on origin, so it cannot be "
                              "claimed.".format(ticket, self.spec))
            if found.claimed_by:
                return "" if found.claimed_by == self.me else found.claimed_by
            if self.pushed_change(
                    self.spec, found.path, lambda text: with_field(text, CLAIMED_BY, self.me),
                    "Claim ticket {} of spec {} for {}".format(found.number, self.spec, self.me),
                    "The claim on ticket {} of spec {}".format(found.number, self.spec)):
                return ""
        raise refusal("The claim on ticket {} of spec {} lost to another push {} times in a row. "
                      "Run the loop again.".format(ticket, self.spec, PUSH_ATTEMPTS))

    def close_spec(self, spec):
        for _ in range(PUSH_ATTEMPTS):
            branch = self.branch_of(spec)
            self.fetched(branch)
            folder = self.folder_on("origin/" + branch, spec)
            if not folder:
                raise refusal("Spec {} has no folder on origin/{}, so it cannot be "
                              "closed.".format(spec, branch))
            commit = self.pushed_change(
                spec, folder + "/" + SPEC_FILE, lambda text: with_field(text, STATUS, CLOSED),
                "Close spec {}".format(spec), "The close of spec {}".format(spec))
            if commit:
                return self.git("rev-parse", "--short", commit).out.strip()
        raise refusal("The close of spec {} lost to another push {} times in a row. Set status: "
                      "closed in its spec.md by hand.".format(spec, PUSH_ATTEMPTS))

    def pushed_change(self, spec, path, change, message, what):
        branch = self.branch_of(spec)
        parent = self.git("rev-parse", "origin/" + branch).out.strip()
        text = change(self.shown(parent, path))
        with tempfile.TemporaryDirectory() as scratch:
            written = Path(scratch) / "changed.md"
            written.write_text(text, encoding="utf-8", newline="")
            blob = self.git("hash-object", "-w", "--no-filters", written.as_posix()).out.strip()
            # An index of its own, so neither the checkout nor its staged work is touched.
            index = {"GIT_INDEX_FILE": (Path(scratch) / "index").as_posix()}
            self.git("read-tree", parent, env=index)
            self.git("update-index", "--cacheinfo", "100644,{},{}".format(blob, path), env=index)
            tree = self.git("write-tree", env=index).out.strip()
        commit = self.git("commit-tree", tree, "-p", parent, "-m", message).out.strip()
        pushed = self.git("push", "--quiet", "origin", "{}:refs/heads/{}".format(commit, branch))
        if pushed.status == 0:
            return commit
        said = (pushed.out + pushed.err).rstrip("\n")
        if any(mark in said for mark in LOST_RACE):
            return ""
        raise refusal("{} did not reach {} on origin. git said:\n{}".format(what, branch, said))
