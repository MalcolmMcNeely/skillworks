# gh 2.92.0 has no dependency flags, so reads go through `gh api`: docs/research/harness/ticket-state-guardrails.md.

from stop import is_a_number, refusal

# gh asks at a terminal, and a script run by a loop or by hand may have nobody at one.
GH_QUIET = {"GH_PROMPT_DISABLED": "1"}

# gh fills these in from the checkout it runs in.
THIS_REPO = "{owner}/{repo}"

# Long enough for another loop's write to be visible, and handed a wait so a test need not pay it.
CLAIM_WAIT = 3

BRANCH_HEADING = "## Branch"

DRIFT_REPORT = "## Drift report"


def listed(said):
    return [line for line in said.split("\n") if line != ""]


def spec_branch(spec):
    lines = [line.strip() for line in spec.splitlines()]
    if BRANCH_HEADING in lines:
        below = lines[lines.index(BRANCH_HEADING) + 1:]
        named = next((line for line in below if line), "").strip("`")
        if named and not named.startswith("#"):
            return named
    raise refusal("The spec names no branch under {}. Run to-spec, which writes it, or add it by hand.".format(BRANCH_HEADING))


class GitHub:
    # A Session closes the issue naming its commits, and a rebase at Land replaces them.
    close_names_commits = True
    marks_pull_requests = True

    def __init__(self, runner, where, repo=THIS_REPO):
        self.runner = runner
        self.where = str(where)
        self.repo = repo
        self.me = ""

    def gh(self, *args):
        return self.runner.run(["gh"] + [str(a) for a in args], self.where, GH_QUIET)

    # A reason and not a stop, so the caller says it in its own words.
    def connect(self):
        if not self.runner.found("gh"):
            return "gh is not installed"
        if self.gh("auth", "status").status != 0:
            return "gh is not authenticated. Run: gh auth login"
        self.repo = self.gh("repo", "view", "--json", "nameWithOwner",
                            "--jq", ".nameWithOwner").out.strip()
        self.me = self.gh("api", "user", "--jq", ".login").out.strip()
        return ""

    def field(self, issue, jq):
        return self.gh("api", "repos/{}/issues/{}".format(self.repo, issue), "--jq", jq)

    def sub_issues(self, spec, query):
        return self.gh("api", "--paginate", "repos/{}/issues/{}/sub_issues".format(
            self.repo, spec), "--jq", query)

    # An issue number is unique in the repo, so it names a ticket on its own.
    def reference(self, ticket):
        return ticket

    def named(self, ticket):
        return "#" + ticket

    def spec_named(self, spec):
        return "#" + spec

    def trailer(self, ticket):
        return self.named(ticket)

    # A failed read is not a ticket in any state.
    def state(self, issue):
        read = self.field(issue, ".state")
        return read.out.strip() if read.status == 0 else None

    # The issue is the one place a GitHub ticket's state is kept, whichever worktree asks.
    def state_in(self, ticket, worktree):
        return self.state(ticket)

    def close_asked(self, ticket):
        return ("Ticket #{} is still open. Close it with a comment saying what was done and "
                "which tests prove it.\n".format(ticket))

    # A person closes a GitHub spec, or its pull request does as it merges.
    def close_spec(self, spec):
        return ""

    def title(self, issue):
        return self.field(issue, ".title").out.strip()

    # A spec is an issue like its tickets, so it is asked the same way.
    def spec_state(self, spec):
        return self.state(spec)

    def spec_title(self, spec):
        return self.title(spec)

    def spec_body(self, spec):
        asked = self.field(spec, ".body")
        if asked.status != 0:
            raise refusal("The tracker would not give the body of spec #{}, which names its "
                          "branch. gh said:\n{}".format(spec, (asked.out + asked.err).rstrip("\n")))
        return asked.out

    def branch_of(self, spec):
        return spec_branch(self.spec_body(spec))

    # --paginate runs --jq once per page, so a length would count only the first hundred.
    def tickets(self, spec):
        return listed(self.sub_issues(spec, ".[].number").out)

    def open_tickets(self, spec):
        return listed(self.sub_issues(spec, '.[] | select(.state=="open") | .number').out)

    def ticket_rows(self, spec):
        rows = self.sub_issues(spec, '.[] | "\\(.number)\\t\\(.state)\\t\\(.title)"').out
        return [tuple((line.split("\t") + ["", ""])[:3]) for line in listed(rows)]

    # blocked_by counts OPEN blockers only, and a missing count is not guessed.
    def open_blockers(self, ticket):
        blocked = self.field(
            ticket, '.issue_dependencies_summary.blocked_by // "missing"').out.strip()
        return int(blocked) if is_a_number(blocked) else None

    def claimed_by_others(self, ticket):
        return self.field(ticket, '[.assignees[].login] | map(select(. != "{}")) | '
                                  'join(",")'.format(self.me)).out.strip()

    # There is no compare-and-swap here, so this detects a race rather than preventing one.
    def claim(self, ticket, wait):
        self.gh("issue", "edit", ticket, "--add-assignee", "@me")
        wait(CLAIM_WAIT)
        others = self.claimed_by_others(ticket)
        if others:
            self.gh("issue", "edit", ticket, "--remove-assignee", "@me")
        return others

    def close(self, ticket, comment):
        return self.gh("issue", "close", ticket, "--comment", comment).status == 0

    def reopen(self, ticket):
        return self.gh("issue", "reopen", ticket).status == 0

    def comment(self, ticket, body):
        return self.gh("issue", "comment", ticket, "--body", body).status == 0

    def last_comment(self, ticket):
        ran = self.gh("issue", "view", ticket, "--json", "comments", "--jq", ".comments[-1].body")
        return ran.out.rstrip("\n") if ran.status == 0 else None

    # The last comment is how a ticket was closed.
    def closing_note(self, trailer):
        return self.last_comment(trailer.removeprefix("#"))

    # The heading tells the report from a comment a person left after it, or from none at all.
    def drift_report(self, spec):
        lines = (self.last_comment(spec) or "").replace("\r\n", "\n").split("\n")
        if lines[0].strip() != DRIFT_REPORT:
            return ""
        return "\n".join(lines[1:]).strip("\n")
