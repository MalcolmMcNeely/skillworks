# Reads and writes the Sidecar alone, so nothing about a spec or a ticket ever reaches origin.

import hashlib
import re
from pathlib import Path
from typing import NamedTuple

from clock.clock import Clock
from sidecar.sidecar import Sidecar
from stop import is_a_number, refusal
from tracker.reading import DRIFT_REPORT, FLAKES, NAME_REPORT, listed

SPECS = ".specs"
SPEC_FILE = "spec.md"
TICKETS = "tickets"
FENCE = "---"
STATUS = "status"
CLOSED = "closed"
CLOSING_NOTE = "## Closing note"
OPEN = "open"
HASH = "hash"
BRANCH = "branch"

# The committed state, so a read never sees a write the lock is still holding.
HEAD = "HEAD"

LOOP_STATE = ".spec-loop"
LOOP_BRANCHES = "spec-loop/"

REPORTS = (DRIFT_REPORT, NAME_REPORT)


class Ticket(NamedTuple):
    number: str
    status: str
    blocked_by: list
    title: str
    path: str


class Spec(NamedTuple):
    status: str
    title: str
    tickets: list
    body: str
    branch: str
    folder: str


def number_of(name):
    lead = name.split("-", 1)[0]
    return str(int(lead)) if is_a_number(lead) else ""


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


def section_in(body, named, ends_at=None):
    lines = body.split("\n")
    stripped = [line.strip() for line in lines]
    if named not in stripped:
        return ""
    start = stripped.index(named) + 1
    end = stripped.index(ends_at, start) if ends_at in stripped[start:] else len(lines)
    return "\n".join(lines[start:end]).strip("\n")


def closing_note_in(body):
    return section_in(body, CLOSING_NOTE)


# The section runs to the end of the file, so a report holding headings of its own is replaced whole.
def with_last_section(text, named, section):
    ending = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(ending)
    stripped = [line.strip() for line in lines]
    kept = lines[:stripped.index(named)] if named in stripped else lines
    while kept and kept[-1].strip() == "":
        kept.pop()
    added = section.replace("\r\n", "\n").strip("\n").split("\n")
    return ending.join(kept + [""] + added) + ending


# Above the reports, because each report runs to the end of the file and a new one cuts what is below it.
def with_section_above(text, named, section, above):
    ending = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(ending)
    stripped = [line.strip() for line in lines]
    if named in stripped:
        start = stripped.index(named)
        end = next((at for at in range(start + 1, len(lines)) if stripped[at] in above), len(lines))
        del lines[start:end]
        del stripped[start:end]
    at = next((at for at, line in enumerate(stripped) if line in above), len(lines))
    kept = lines[:at]
    while kept and kept[-1].strip() == "":
        kept.pop()
    added = section.replace("\r\n", "\n").strip("\n").split("\n")
    below = [""] + lines[at:] if at < len(lines) else [""]
    return ending.join(kept + [""] + added + below).rstrip(ending) + ending


def heading(body, otherwise):
    return next((line[2:].strip() for line in body.split("\n") if line.startswith("# ")), otherwise)


def slug_of(title):
    return "-".join(re.findall(r"[a-z0-9]+", title.lower())) or "ticket"


def new_ticket_text(title, body):
    return "\n".join([FENCE, STATUS + ": open", "blocked-by: []", FENCE, "",
                      "# " + title, "", body.replace("\r\n", "\n").strip("\n"), ""])


def as_numbers(value):
    held = value if isinstance(value, list) else as_list(value)
    return [str(int(item)) if is_a_number(item) else item for item in held]


def text_of(path):
    return Path(path).read_text(encoding="utf-8")


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def spec_hash(body):
    return "sha256:" + hashlib.sha256(body.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def folders_in(sidecar):
    specs = Path(sidecar) / SPECS
    return sorted(each for each in specs.iterdir() if each.is_dir()) if specs.is_dir() else []


def folder_on_disk(sidecar, spec):
    named = [each for each in folders_in(sidecar) if number_of(each.name) == spec]
    return named[0] if len(named) == 1 else None


def highest_of(names):
    return max([int(number_of(name) or 0) for name in names], default=0)


class Files:
    # The Closing note is a section of the ticket file, which has no thread to take a later comment.
    close_names_commits = False

    # A target of None is PR mode, where each spec's frontmatter names its own branch.
    def __init__(self, runner, where, target, spec=None, clock=None):
        self.runner = runner
        self.where = str(where)
        self.target = target
        self.spec = spec
        self.clock = clock or Clock()
        self.opened = None
        # Keyed by the Sidecar's commit, so a Sidecar that has not changed is not read again.
        self.read_at = {}

    def sidecar(self):
        if self.opened is None:
            self.opened = Sidecar.of(self.runner, self.where, self.clock)
        return self.opened

    def git(self, *args):
        return self.runner.run(["git", "-C", self.sidecar().folder.as_posix()] + [str(a) for a in args])

    def connect(self):
        self.sidecar()
        return ""

    def kept_in(self):
        return self.sidecar().folder.as_posix()

    # A Sidecar no write has made yet holds nothing, and git run there would read the folder above it.
    def commit(self):
        if not (self.sidecar().folder / ".git").exists():
            return ""
        said = self.git("rev-parse", "--verify", "--quiet", HEAD)
        return said.out.strip() if said.status == 0 else ""

    def shown(self, path):
        return self.git("show", "{}:{}".format(HEAD, path)).out

    def folder_on(self, spec):
        held = self.git("ls-tree", "--name-only", HEAD, SPECS + "/").out
        named = [path for path in listed(held) if number_of(path.rsplit("/", 1)[-1]) == spec]
        return named[0] if len(named) == 1 else ""

    def branch_of(self, spec):
        if self.target is not None:
            return self.target
        held = self.read(spec)
        if held is None:
            raise refusal("The Sidecar at {} holds no folder for spec {}, so it names no branch "
                          "for it.".format(self.kept_in(), spec))
        if not held.branch:
            raise refusal("Spec {} names no branch in its spec.md frontmatter, and in PR mode the "
                          "loop Lands on that branch. /skillworks:grill writes it, or add it by "
                          "hand.".format(spec))
        return held.branch

    def read(self, spec):
        if spec is None:
            raise refusal("The files Tracker numbers each ticket inside its spec, and it was given "
                          "no spec.")
        commit = self.commit()
        if (commit, spec) not in self.read_at:
            self.read_at[(commit, spec)] = self.spec_on(spec) if commit else None
        return self.read_at[(commit, spec)]

    def open_spec_branches(self):
        if not self.commit():
            return {}
        held = {}
        for path in listed(self.git("ls-tree", "--name-only", HEAD, SPECS + "/").out):
            spec = number_of(path.rsplit("/", 1)[-1])
            found = self.read(spec) if spec else None
            if found and found.status == OPEN and found.branch:
                held[found.branch] = spec
        return held

    def spec_on(self, spec):
        folder = self.folder_on(spec)
        if not folder:
            return None
        held, body = frontmatter(self.shown(folder + "/" + SPEC_FILE))
        tickets = []
        paths = listed(self.git("ls-tree", "--name-only", HEAD, folder + "/" + TICKETS + "/").out)
        for path in paths:
            name = path.rsplit("/", 1)[-1]
            number = number_of(name)
            if not number or not name.endswith(".md"):
                continue
            ticket, text = frontmatter(self.shown(path))
            tickets.append(Ticket(number, ticket.get(STATUS, ""),
                                  as_numbers(ticket.get("blocked-by", [])),
                                  heading(text, name[:-3]), path))
        tickets.sort(key=lambda ticket: int(ticket.number))
        return Spec(held.get(STATUS, ""), heading(body, folder.rsplit("/", 1)[-1]), tickets, body,
                    held.get(BRANCH, ""), folder)

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

    def spec_body(self, spec):
        held = self.read(spec)
        return held.body if held else ""

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
        return [ticket.number for ticket in held.tickets if ticket.status == OPEN] if held else []

    def ticket_rows(self, spec):
        held = self.read(spec)
        return [(ticket.number, ticket.status, ticket.title) for ticket in held.tickets] if held else []

    # A blocker with no file is not known to be closed, so it counts as open.
    def open_blockers(self, ticket):
        held = self.read(self.spec)
        closed = {each.number for each in held.tickets if each.status == CLOSED} if held else set()
        found = self.ticket(ticket)
        return sum(1 for blocker in found.blocked_by if blocker not in closed) if found else None

    # The Sidecar serves one machine, where spec-loop runs one loop to a spec, so no other loop holds a ticket.
    def claimed_by_others(self, ticket):
        return ""

    # A ticket number is local to its spec, so the spec comes with it wherever it is named.
    def reference(self, ticket):
        if self.spec is None:
            raise refusal("The files Tracker numbers each ticket inside its spec, and it was "
                          "given no spec to name ticket {} by.".format(ticket))
        return "{}/{}".format(self.spec, ticket)

    # A landing run by hand may name no spec, and its stop still has to say which ticket it was.
    def named(self, ticket):
        return self.reference(ticket) if self.spec is not None else "ticket " + ticket

    def spec_named(self, spec):
        return spec

    def trailer(self, ticket):
        return self.reference(ticket)

    def close_asked(self, ticket):
        return ("Ticket {0} is still open. Close it with tracker-close {0} and a note file saying "
                "what was done and which tests prove it.\n".format(self.reference(ticket)))

    def path_of(self, spec, ticket=None):
        held = self.read(spec)
        if held is None:
            raise refusal("The Sidecar at {} holds no spec {}.".format(
                self.kept_in(), spec))
        if ticket is None:
            return held.folder + "/" + SPEC_FILE
        found = [each for each in held.tickets if each.number == ticket]
        if not found:
            raise refusal("Spec {} in the Sidecar holds no ticket {}.".format(spec, ticket))
        return found[0].path

    def text(self, spec, ticket=None):
        return self.shown(self.path_of(spec, ticket))

    def closing_note(self, trailer):
        spec, _, ticket = trailer.partition("/")
        if not is_a_number(spec) or not is_a_number(ticket):
            return None
        spec, ticket = str(int(spec)), str(int(ticket))
        held = self.read(spec)
        found = [each for each in held.tickets if each.number == ticket] if held else []
        if not found:
            return None
        return closing_note_in(frontmatter(self.shown(found[0].path))[1])

    # The Name check runs after the drift check, so its report is the one written below.
    def drift_report(self, spec):
        return section_in(self.spec_body(spec), DRIFT_REPORT, NAME_REPORT)

    def name_report(self, spec):
        return section_in(self.spec_body(spec), NAME_REPORT)

    # The file is read again inside the lock, so a change builds on the last write and not on a stale read.
    def changed(self, spec, ticket, message, change):
        path = self.path_of(spec, ticket)

        def written(sidecar):
            write_text(sidecar / path, change(text_of(sidecar / path)))
        self.sidecar().write(message, written)
        return path

    def claim(self, ticket, wait):
        return ""

    def close(self, ticket, note):
        section = CLOSING_NOTE + "\n\n" + note.replace("\r\n", "\n").strip("\n") + "\n"
        self.changed(self.spec, ticket, "Close ticket {} of spec {}".format(ticket, self.spec),
                     lambda text: with_last_section(with_field(text, STATUS, CLOSED),
                                                    CLOSING_NOTE, section))
        return True

    # The Closing note stays until a new close replaces it, so a person still reads why it closed.
    def reopen(self, ticket):
        self.changed(self.spec, ticket, "Reopen ticket {} of spec {}".format(ticket, self.spec),
                     lambda text: with_field(text, STATUS, OPEN))
        return True

    def close_spec(self, spec):
        self.changed(spec, None, "Close spec {}".format(spec),
                     lambda text: with_field(text, STATUS, CLOSED))
        return "in the Sidecar as {}".format(self.git("rev-parse", "--short", HEAD).out.strip())

    # One section and not one per run, so spec.md carries the last run's Flakes and never a pile of them.
    def record_flakes(self, spec, note):
        self.changed(spec, None, "Note the Flakes of spec {}".format(spec),
                     lambda text: with_section_above(text, FLAKES, note, REPORTS))

    # Each report replaces its heading to the end of the file, so a drift report takes the Name report after it too.
    def record_report(self, spec, heading, report, what):
        path = self.changed(spec, None, "Record the {} of spec {}".format(what, spec),
                            lambda text: with_last_section(text, heading, report))
        return (self.sidecar().folder / path).as_posix()

    # The number is read inside the lock, so two filings at once take two numbers.
    def file_ticket(self, spec, title, body):
        self.path_of(spec)
        filed = []

        def file(sidecar):
            folder = folder_on_disk(sidecar, spec) / TICKETS
            number = highest_of([each.name for each in folder.iterdir()] if folder.is_dir() else []) + 1
            write_text(folder / "{:02d}-{}.md".format(number, slug_of(title)),
                       new_ticket_text(title, body))
            filed.append(str(number))
        self.sidecar().write("File ticket under spec {}: {}".format(spec, title), file)
        return filed[0]

    def write_tickets(self, spec, tickets):
        if self.read(spec) is None:
            raise refusal("Spec {} has no folder in the Sidecar. Write it with tracker-publish spec "
                          "first.".format(spec))
        written = []

        def write(sidecar):
            folder = folder_on_disk(sidecar, spec) / TICKETS
            if folder.is_dir() and any(folder.iterdir()):
                raise refusal("Spec {} already has tickets in the Sidecar, so none were "
                              "written.".format(spec))
            for name, text in tickets:
                write_text(folder / name, text)
                written.append((folder / name).as_posix())
        self.sidecar().write("Write the tickets of spec {}".format(spec), write)
        return written

    # A new spec never takes a number whose log, journal or kept work the loop already holds.
    def used_by_loop_state(self):
        main = self.sidecar().main
        state = main / LOOP_STATE
        folders = [each.name for each in state.iterdir() if each.is_dir()] if state.is_dir() else []
        branches = listed(self.runner.run(
            ["git", "-C", main.as_posix(), "for-each-ref", "--format=%(refname:strip=2)",
             "refs/heads/" + LOOP_BRANCHES]).out)
        named = [branch[len(LOOP_BRANCHES):].split("/", 1)[0] for branch in branches]
        return [int(name) for name in folders + named if is_a_number(name)]

    # A rerun finds the open spec by its hash, so a spec written before a failure is not written twice.
    def write_spec(self, slug, body, branch):
        hashed = spec_hash(body)
        fields = [STATUS + ": " + OPEN, HASH + ": " + hashed] + ([BRANCH + ": " + branch] if branch else [])
        text = "\n".join([FENCE] + fields + [FENCE, "", ""]) + body
        found = []

        def write(sidecar):
            folders = folders_in(sidecar)
            for folder in folders:
                held = frontmatter(text_of(folder / SPEC_FILE))[0] if (folder / SPEC_FILE).is_file() else {}
                if held.get(HASH) == hashed and held.get(STATUS) == OPEN:
                    found.append((number_of(folder.name), SPECS + "/" + folder.name, False))
                    return
            number = max([highest_of([each.name for each in folders])] + self.used_by_loop_state()) + 1
            named = "{}/{:04d}-{}".format(SPECS, number, slug)
            write_text(Path(sidecar) / named / SPEC_FILE, text)
            found.append((str(number), named, True))
        self.sidecar().write("Write spec: {}".format(heading(body, slug)), write)
        return found[0]


