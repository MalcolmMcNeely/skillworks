# Reads only the remote's Target branch, so unpushed work cannot change what the loop starts.

import io
import time
from typing import NamedTuple

from fetch_origin import fetch_origin
from stop import is_a_number, refusal

SPECS = ".specs"
SPEC_FILE = "spec.md"
TICKETS = "tickets"
FENCE = "---"

# Every remote branch at once, because in spec mode the spec's own folder says which one is its.
EVERY_BRANCH = "*"


class Ticket(NamedTuple):
    number: str
    status: str
    blocked_by: list
    claimed_by: str
    title: str


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


def heading(body, otherwise):
    return next((line[2:].strip() for line in body.split("\n") if line.startswith("# ")), otherwise)


def as_numbers(value):
    held = value if isinstance(value, list) else as_list(value)
    return [str(int(item)) if is_a_number(item) else item for item in held]


class Files:
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

    def git(self, *args):
        return self.runner.run(["git", "-C", self.where] + [str(a) for a in args])

    def connect(self):
        found = self.git("remote", "get-url", "origin")
        if found.status != 0:
            return "this repo has no remote named origin, and the files Tracker reads from it"
        self.repo = found.out.strip()
        self.me = self.git("config", "user.email").out.strip()
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
                                  ticket.get("claimed-by", ""), heading(text, name[:-3])))
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

    def not_yet(self, what):
        return refusal("The files Tracker cannot {} yet.".format(what))

    def claim(self, ticket, wait):
        raise self.not_yet("claim ticket {}".format(ticket))

    def close(self, ticket, comment):
        raise self.not_yet("close ticket {}".format(ticket))

    def reopen(self, ticket):
        raise self.not_yet("reopen ticket {}".format(ticket))

    def comment(self, ticket, body):
        raise self.not_yet("comment on ticket {}".format(ticket))

    def last_comment(self, ticket):
        raise self.not_yet("read the last comment on ticket {}".format(ticket))
