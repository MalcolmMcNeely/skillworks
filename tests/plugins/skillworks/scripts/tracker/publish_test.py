# Driven through main, so each case checks what reached the Sidecar and what the files Tracker reads back.

import contextlib
import io
import json
import threading
from pathlib import Path

import pytest

from clock.held_clock import HeldClock
from conftest import Ran, RecordingRunner, Repo, git, launch
from files_test import refs_of, ticket_file, write_loop
from github_test import Issues
from runner import Subprocess
from sidecar.locator import sidecar_of
from sidecar.sidecar import WAIT_SECONDS
from steering.target_branch import LOOP_FILE
from tracker import publish
from tracker.files import Files
from tracker.github import GitHub, spec_branch

SPEC_BRANCH = "spec/local-tracker"

BODY = "# SPEC: A local tracker\n\n## Problem Statement\n\nNo GitHub.\n"

FILED_BODY = "## Problem Statement\n\nNo GitHub.\n"

# The sha256 of the title, a newline and FILED_BODY, worked out outside the code under test.
HASH_LINE = ("<!-- skillworks-spec sha256:e167abbc1f143b1e3955268f97d0530bb70cada2af94b2bee3968b5d9e2"
             "6e0c6 -->")

# The sha256 of BODY, worked out outside the code under test.
BODY_HASH = "sha256:df4a0fc9315e9ed0fb9bb4de51fb64e2db0ce7c135055c2aa1ecc7919117db96"


class Writer:
    def __init__(self, repo, runner, scratch):
        self.repo = repo
        self.runner = runner
        self.scratch = scratch
        self.clock = HeldClock()

    def written(self, name, text):
        path = self.scratch / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path.as_posix()

    def run(self, *argv, where=None):
        out, err = io.StringIO(), io.StringIO()
        where = where or self.repo.work
        with contextlib.chdir(where):
            status = publish.main(list(argv), self.runner, out, err, self.clock,
                                  Path(where).as_posix())
        return Ran(status, out.getvalue(), err.getvalue())

    def spec(self, slug="local-tracker", body=BODY, *branch, where=None):
        return self.run("spec", slug, self.written(slug + "-body.md", body), *branch, where=where)

    def tickets(self, spec, tickets):
        return self.run("tickets", spec, *[self.written("tickets/" + name, text)
                                           for name, text in tickets.items()])

    def sidecar(self):
        return sidecar_of(Subprocess(), self.repo.work)

    def held(self, path):
        return (self.sidecar() / path).read_text(encoding="utf-8")

    def folders(self):
        specs = self.sidecar() / ".specs"
        return sorted(".specs/" + each.name for each in specs.iterdir()) if specs.is_dir() else []

    def tracker(self, spec, target="main"):
        return Files(RecordingRunner(), self.repo.work, target, spec, HeldClock())


@pytest.fixture
def writer(tmp_path):
    repo = Repo(tmp_path / "repo")
    write_loop(repo.work, "main")
    return Writer(repo, RecordingRunner(), tmp_path / "scratch")


def said(ran):
    return ran.out + ran.err


def spec_text(status="open", branch=None):
    lines = ["---", "status: " + status, "hash: " + BODY_HASH]
    if branch:
        lines.append("branch: " + branch)
    return "\n".join(lines + ["---", "", ""]) + BODY


def test_a_spec_is_written_to_the_sidecar_as_a_numbered_folder_with_its_frontmatter(writer):
    ran = writer.spec()

    assert ran.status == 0, said(ran)
    assert ran.out == "1\t.specs/0001-local-tracker\n"
    assert writer.held(".specs/0001-local-tracker/spec.md") == spec_text()
    assert writer.tracker("1").spec_state("1") == "open"
    assert writer.tracker("1").spec_title("1") == "SPEC: A local tracker"


def test_a_spec_takes_the_highest_number_in_the_sidecar_plus_one(writer):
    writer.spec("older", "# SPEC: Older\n")
    writer.spec("old", "# SPEC: Old\n")

    ran = writer.spec()

    assert (ran.status, ran.out) == (0, "3\t.specs/0003-local-tracker\n"), said(ran)


def test_a_spec_takes_a_number_above_every_one_the_loop_state_already_uses(writer):
    (writer.repo.work / ".spec-loop" / "12").mkdir(parents=True)
    (writer.repo.work / ".spec-loop" / "grill").mkdir(parents=True)
    git(writer.repo.work, "branch", "spec-loop/15/ticket-1")

    ran = writer.spec()

    assert (ran.status, ran.out) == (0, "16\t.specs/0016-local-tracker\n"), said(ran)


def test_the_checkout_is_left_as_it_was(writer):
    head = git(writer.repo.work, "rev-parse", "HEAD")
    (writer.repo.work / "staged.txt").write_text("staged\n", encoding="utf-8")
    git(writer.repo.work, "add", "staged.txt")

    ran = writer.spec()

    assert ran.status == 0, said(ran)
    assert git(writer.repo.work, "rev-parse", "HEAD") == head
    assert git(writer.repo.work, "diff", "--cached", "--name-only").split() == ["staged.txt"]
    assert not (writer.repo.work / ".specs").exists()


# The first writer is held inside the lock until the second waits on it, so both truly run at once.
class HeldInsideTheLock(RecordingRunner):
    def __init__(self):
        super().__init__()
        self.holds = threading.Event()
        self.let_go = threading.Event()

    def run(self, args, where=None, env=None, stdin=None):
        if [str(each) for each in args][-2:] == ["add", "--all"] and not self.holds.is_set():
            self.holds.set()
            self.let_go.wait()
        return super().run(args, where, env, stdin)


def test_two_specs_published_at_once_from_two_worktrees_get_two_different_numbers(writer):
    nested = writer.repo.work / ".spec-loop" / "grill" / "other"
    git(writer.repo.work, "worktree", "add", "--quiet", "-b", "other", nested.as_posix())
    write_loop(nested, "main")
    first_runner = HeldInsideTheLock()
    first = Writer(writer.repo, first_runner, writer.scratch / "first")
    first.clock = writer.clock
    ran = {}

    def publish_first():
        ran["first"] = first.spec("first", "# SPEC: First\n")

    def publish_second():
        ran["second"] = writer.spec("second", "# SPEC: Second\n", where=nested)

    first_thread = threading.Thread(target=publish_first)
    second_thread = threading.Thread(target=publish_second)
    first_thread.start()
    first_runner.holds.wait()
    second_thread.start()
    writer.clock.repeating.wait()
    first_runner.let_go.set()
    first_thread.join()
    writer.clock.move(WAIT_SECONDS)
    second_thread.join()

    assert (ran["first"].out, ran["second"].out) == (
        "1\t.specs/0001-first\n", "2\t.specs/0002-second\n"), said(ran["second"])


def test_a_rerun_after_a_failure_prints_the_spec_it_already_wrote_and_files_none(writer):
    writer.spec()

    ran = writer.spec()

    assert (ran.status, ran.out) == (0, "1\t.specs/0001-local-tracker\n"), said(ran)
    assert "already holds this spec, so nothing was written" in ran.err
    assert writer.folders() == [".specs/0001-local-tracker"]


def test_a_spec_with_the_same_body_as_a_closed_spec_is_written_anew(writer):
    writer.spec()
    writer.tracker("1").close_spec("1")

    ran = writer.spec()

    assert (ran.status, ran.out) == (0, "2\t.specs/0002-local-tracker\n"), said(ran)


def test_a_body_that_brings_its_own_frontmatter_is_turned_down(writer):
    ran = writer.spec(body="---\nstatus: closed\n---\n\n" + BODY)

    assert ran.status == 1
    assert "frontmatter" in ran.err
    assert writer.folders() == []


def test_in_pr_mode_the_spec_names_its_branch_in_its_frontmatter(writer):
    write_loop(writer.repo.work, "pr")

    ran = writer.spec("local-tracker", BODY, SPEC_BRANCH)

    assert ran.status == 0, said(ran)
    assert writer.held(".specs/0001-local-tracker/spec.md") == spec_text(branch=SPEC_BRANCH)
    assert writer.tracker("1", target=None).branch_of("1") == SPEC_BRANCH


def test_in_pr_mode_a_spec_with_no_branch_is_turned_down(writer):
    write_loop(writer.repo.work, "pr")

    ran = writer.spec()

    assert ran.status == 1
    assert "branch" in ran.err


def test_a_checkout_with_no_loop_file_is_told_to_seed_it_even_beside_an_old_steering_branch(writer):
    (writer.repo.work / LOOP_FILE).unlink()
    git(writer.repo.work, "update-ref", "refs/remotes/origin/skillworks/steering", "HEAD")
    git(writer.repo.work, "checkout", "--quiet", "-b", "proj-12/local-tracker")

    ran = writer.spec()

    assert ran.err == "FAIL  docs/skillworks/loop.json is missing. Run seed-steering to write it.\n"


def test_with_a_branch_named_target_a_branch_given_is_turned_down(writer):
    ran = writer.spec("local-tracker", BODY, SPEC_BRANCH)

    assert ran.status == 1
    assert writer.folders() == []


def three_tickets():
    return {
        "01-read-loop-json.md": ticket_file("TICKET: Read loop.json"),
        "02-close-in-worktree.md": ticket_file("TICKET: Close in the worktree", blocked_by=[1]),
        "03-claim.md": ticket_file("TICKET: Claim", blocked_by=[1, 2]),
    }


def test_tickets_are_written_into_the_specs_folder_and_the_tracker_reads_them(writer):
    writer.spec()

    ran = writer.tickets("1", three_tickets())

    assert ran.status == 0, said(ran)
    tracker = writer.tracker("1")
    assert tracker.tickets("1") == ["1", "2", "3"]
    assert tracker.open_tickets("1") == ["1", "2", "3"]
    assert tracker.title("2") == "TICKET: Close in the worktree"
    assert [tracker.open_blockers(ticket) for ticket in ["1", "2", "3"]] == [0, 1, 2]
    assert writer.held(".specs/0001-local-tracker/tickets/03-claim.md") == three_tickets()["03-claim.md"]


def test_tickets_for_a_spec_with_tickets_already_are_turned_down(writer):
    writer.spec()
    writer.tickets("1", three_tickets())

    ran = writer.tickets("1", {"04-more.md": ticket_file("TICKET: More")})

    assert ran.status == 1
    assert "already" in ran.err
    assert writer.tracker("1").tickets("1") == ["1", "2", "3"]


def test_tickets_for_a_spec_with_no_folder_are_turned_down(writer):
    ran = writer.tickets("9", three_tickets())

    assert ran.status == 1
    assert "9" in ran.err


def test_a_ticket_that_names_a_claim_is_written_as_given_because_nothing_reads_one(writer):
    writer.spec()
    claimed = ticket_file("TICKET: A", more=["claimed-by: someone@example.invalid"])

    ran = writer.tickets("1", {"01-a.md": claimed})

    assert ran.status == 0, said(ran)
    assert writer.held(".specs/0001-local-tracker/tickets/01-a.md") == claimed


UNFOLLOWABLE = [
    ({"01-a.md": ticket_file("TICKET: A", blocked_by=[2]), "02-b.md": ticket_file("TICKET: B")},
     "dependency order"),
    ({"01-a.md": ticket_file("TICKET: A", blocked_by=[3])}, "dependency order"),
    ({"01-a.md": ticket_file("TICKET: A", status="closed")}, "status: open"),
    ({"a.md": ticket_file("TICKET: A")}, "number"),
    ({"01-a.md": ticket_file("TICKET: A"), "01-b.md": ticket_file("TICKET: B")}, "number"),
    ({"01-a.md": ticket_file("TICKET: A"), "02-b.md": ticket_file("TICKET: A")}, "title"),
]


@pytest.mark.parametrize("tickets, reason", UNFOLLOWABLE)
def test_a_ticket_the_tracker_could_not_follow_is_turned_down(writer, tickets, reason):
    writer.spec()

    ran = writer.tickets("1", tickets)

    assert ran.status == 1
    assert reason in ran.err
    assert writer.tracker("1").tickets("1") == []


REPORT = "## Drift report\n\n- Story 1: Done\n- Story 2: Missing\n"


def test_a_drift_report_is_written_to_the_end_of_the_specs_file(writer):
    writer.spec()

    ran = writer.run("drift", "1", writer.written("drift.md", REPORT))

    assert ran.status == 0, said(ran)
    assert ran.out == (writer.sidecar() / ".specs/0001-local-tracker/spec.md").as_posix() + "\n"
    assert writer.held(".specs/0001-local-tracker/spec.md") == spec_text() + "\n" + REPORT
    assert writer.tracker("1").drift_report("1") == "- Story 1: Done\n- Story 2: Missing"


def test_a_second_drift_report_takes_the_place_of_the_first(writer):
    writer.spec()
    writer.run("drift", "1", writer.written("drift.md", REPORT))

    ran = writer.run("drift", "1", writer.written("again.md", "## Drift report\n\nAll done.\n"))

    assert ran.status == 0, said(ran)
    text = writer.held(".specs/0001-local-tracker/spec.md")
    assert text.count("## Drift report") == 1
    assert "Missing" not in text
    assert writer.tracker("1").drift_report("1") == "All done."


def test_a_drift_report_without_its_heading_is_turned_down(writer):
    writer.spec()

    ran = writer.run("drift", "1", writer.written("drift.md", "- Story 1: Done\n"))

    assert ran.status == 1
    assert "## Drift report" in ran.err
    assert writer.tracker("1").drift_report("1") == ""


def test_a_drift_report_for_a_spec_with_no_folder_is_turned_down(writer):
    ran = writer.run("drift", "9", writer.written("drift.md", REPORT))

    assert ran.status == 1
    assert "holds no spec 9" in ran.err


NAMES = "## Name report\n\n### Renames\n\n- `Batch`: it now holds a whole spec.\n"


def test_a_name_report_is_written_below_the_drift_report_and_each_reads_back_alone(writer):
    writer.spec()
    writer.run("drift", "1", writer.written("drift.md", REPORT))

    ran = writer.run("names", "1", writer.written("names.md", NAMES))

    assert ran.status == 0, said(ran)
    text = writer.held(".specs/0001-local-tracker/spec.md")
    assert text == spec_text() + "\n" + REPORT + "\n" + NAMES
    assert writer.tracker("1").drift_report("1") == "- Story 1: Done\n- Story 2: Missing"
    assert writer.tracker("1").name_report("1") == (
        "### Renames\n\n- `Batch`: it now holds a whole spec.")


def test_a_second_name_report_takes_the_place_of_the_first(writer):
    writer.spec()
    writer.run("names", "1", writer.written("names.md", NAMES))

    ran = writer.run("names", "1", writer.written("again.md",
                                                  "## Name report\n\n### Renames\n\n- None\n"))

    assert ran.status == 0, said(ran)
    assert writer.held(".specs/0001-local-tracker/spec.md").count("## Name report") == 1
    assert writer.tracker("1").name_report("1") == "### Renames\n\n- None"


# A new drift check starts a new round of judging, so the Name report it follows is out of date.
def test_a_new_drift_report_takes_the_name_report_below_it_away(writer):
    writer.spec()
    writer.run("drift", "1", writer.written("drift.md", REPORT))
    writer.run("names", "1", writer.written("names.md", NAMES))

    ran = writer.run("drift", "1", writer.written("again.md", "## Drift report\n\nAll done.\n"))

    assert ran.status == 0, said(ran)
    assert writer.tracker("1").drift_report("1") == "All done."
    assert writer.tracker("1").name_report("1") == ""


def test_a_name_report_without_its_heading_is_turned_down(writer):
    writer.spec()

    ran = writer.run("names", "1", writer.written("names.md", "### Renames\n\n- None\n"))

    assert ran.status == 1
    assert "## Name report" in ran.err
    assert writer.tracker("1").name_report("1") == ""


def test_publishing_a_spec_its_tickets_and_its_reports_neither_pushes_nor_fetches(writer):
    write_loop(writer.repo.work, "pr")
    before = refs_of(writer.repo)

    writer.spec("local-tracker", BODY, SPEC_BRANCH)
    writer.tickets("1", three_tickets())
    writer.run("drift", "1", writer.written("drift.md", REPORT))
    writer.run("names", "1", writer.written("names.md", NAMES))

    assert refs_of(writer.repo) == before
    assert [call for call in writer.runner.started("git")
            if "push" in call or "fetch" in call or "ls-remote" in call] == []


class Comments:
    def __init__(self, runner):
        self.runner = runner
        self.fails = False
        self.posted = []
        runner.stub("gh", does=self.answer)

    def answer(self):
        called = self.runner.calls[-1][1:]
        if called[:2] == ["repo", "view"]:
            return Ran(0, "owner/repo\n", "")
        if called[:2] == ["api", "user"]:
            return Ran(0, "me\n", "")
        if called[:2] == ["issue", "comment"]:
            if self.fails:
                return Ran(1, "", "HTTP 502: Bad Gateway\n")
            assert "--edit-last" not in called
            body = Path(called[called.index("--body-file") + 1]).read_text(encoding="utf-8")
            self.posted.append((called[2], body))
            return Ran(0, "https://github.com/owner/repo/issues/{}#issuecomment-{}\n".format(
                called[2], len(self.posted)), "")
        if called[:2] == ["issue", "view"]:
            return Ran(0, self.posted[-1][1] if self.posted else "", "")
        return None


@pytest.fixture
def on_github(writer):
    path = writer.repo.work / LOOP_FILE
    path.write_text(json.dumps({"tracker": "github", "target-branch": "main"}), encoding="utf-8")
    return Comments(writer.runner)


def github(runner):
    return GitHub(runner, "/checkout", "owner/repo")


@pytest.mark.parametrize("command, report, read_back", [
    ("drift", REPORT, GitHub.drift_report),
    ("names", NAMES, GitHub.name_report),
])
def test_on_github_a_report_is_posted_as_a_comment_on_the_spec_and_its_url_printed(
        writer, on_github, command, report, read_back):
    ran = writer.run(command, "158", writer.written("report.md", report))

    assert ran.status == 0, said(ran)
    assert ran.out == "https://github.com/owner/repo/issues/158#issuecomment-1\n"
    assert on_github.posted == [("158", report)]
    assert read_back(github(writer.runner), "158") == report.split("\n", 2)[2].strip("\n")


def test_on_github_a_second_report_is_a_second_comment_and_the_first_stays(writer, on_github):
    writer.run("drift", "158", writer.written("drift.md", REPORT))

    ran = writer.run("drift", "158", writer.written("again.md", "## Drift report\n\nAll done.\n"))

    assert ran.status == 0, said(ran)
    assert ran.out == "https://github.com/owner/repo/issues/158#issuecomment-2\n"
    assert on_github.posted == [("158", REPORT), ("158", "## Drift report\n\nAll done.\n")]
    assert github(writer.runner).drift_report("158") == "All done."


@pytest.mark.parametrize("command, report, heading", [
    ("drift", "- Story 1: Done\n", "## Drift report"),
    ("names", "### Renames\n\n- None\n", "## Name report"),
])
def test_on_github_a_report_without_its_heading_is_turned_down(writer, on_github, command, report,
                                                                heading):
    ran = writer.run(command, "158", writer.written("report.md", report))

    assert ran.status == 1
    assert heading in ran.err
    assert on_github.posted == []


def test_on_github_a_report_gh_would_not_post_is_refused_and_says_to_run_again(writer, on_github):
    on_github.fails = True

    ran = writer.run("names", "158", writer.written("names.md", NAMES))

    assert ran.status == 1
    assert ran.out == ""
    assert "HTTP 502: Bad Gateway" in ran.err
    assert "Name report" in ran.err
    assert "again" in ran.err


class Specs:
    def __init__(self, runner):
        self.runner = runner
        self.open = []
        self.filed = []
        self.fails = None
        runner.stub("gh", does=self.answer)

    def answer(self):
        called = self.runner.calls[-1][1:]
        if called[:2] == ["repo", "view"]:
            return Ran(0, "owner/repo\n", "")
        if called[:2] == ["api", "user"]:
            return Ran(0, "me\n", "")
        if self.fails and self.fails in " ".join(called):
            return Ran(1, "", "HTTP 502: Bad Gateway\n")
        if called[0] == "api" and "labels=ready-for-agent&state=open" in " ".join(called):
            return Ran(0, "".join("{0}\thttps://github.com/owner/repo/issues/{0}\t{1}\t{2}\n".format(
                number, body.split("\n", 1)[0], title) for number, title, body in self.open), "")
        if called[:2] == ["issue", "create"]:
            assert called[called.index("--label") + 1] == "ready-for-agent"
            title = called[called.index("--title") + 1]
            body = Path(called[called.index("--body-file") + 1]).read_text(encoding="utf-8")
            number = str(400 + len(self.filed) + 1)
            self.filed.append((title, body))
            self.open.append((number, title, body))
            return Ran(0, "https://github.com/owner/repo/issues/{}\n".format(number), "")
        return None


def specs_on_github(writer, target):
    path = writer.repo.work / LOOP_FILE
    path.write_text(json.dumps({"tracker": "github", "target-branch": target}), encoding="utf-8")
    return Specs(writer.runner)


@pytest.fixture
def github_specs(writer):
    return specs_on_github(writer, "main")


def test_on_github_a_spec_is_filed_as_one_labelled_issue_and_its_number_and_url_printed(
        writer, github_specs):
    ran = writer.spec()

    assert ran.status == 0, said(ran)
    assert ran.out == "401\thttps://github.com/owner/repo/issues/401\n"
    assert github_specs.filed == [("SPEC: A local tracker", HASH_LINE + "\n\n" + FILED_BODY)]
    assert len(writer.runner.built("issue create")) == 1


def test_on_github_a_spec_with_the_title_of_an_open_spec_and_another_body_gets_an_issue_of_its_own(
        writer, github_specs):
    github_specs.open = [("312", "SPEC: Something else", "Other.\n")]
    writer.spec(body="# SPEC: A local tracker\n\n## Problem Statement\n\nAn older design.\n")

    ran = writer.spec()

    assert (ran.status, ran.out) == (0, "402\thttps://github.com/owner/repo/issues/402\n"), said(ran)
    assert "#401" in ran.err and "#312" not in ran.err


def test_on_github_an_open_spec_with_the_title_and_no_hash_line_is_never_taken(writer, github_specs):
    github_specs.open = [("398", "SPEC: A local tracker", FILED_BODY)]

    ran = writer.spec()

    assert ran.status == 0, said(ran)
    assert ran.out == "401\thttps://github.com/owner/repo/issues/401\n"


def test_on_github_a_second_run_with_the_same_spec_files_nothing_twice_and_says_so(
        writer, github_specs):
    first = writer.spec()

    ran = writer.spec()

    assert (ran.out, len(github_specs.filed)) == (first.out, 1), said(ran)
    assert "already filed as #401" in ran.err


def test_on_github_in_pr_mode_the_branch_section_is_written_from_the_branch_named(writer):
    specs = specs_on_github(writer, "pr")

    ran = writer.spec("local-tracker", BODY, SPEC_BRANCH)

    assert ran.status == 0, said(ran)
    body = specs.filed[0][1]
    assert body == ("<!-- skillworks-spec sha256:b95cba84204c93438290de83947d711604739f4d6d3e94d2c"
                    "eb749063abe730c -->\n\n## Branch\n\n{}\n\n## Problem Statement\n\nNo "
                    "GitHub.\n".format(SPEC_BRANCH))
    assert spec_branch(body) == SPEC_BRANCH


def test_on_github_in_pr_mode_a_spec_that_holds_its_own_branch_section_is_turned_down(writer):
    specs = specs_on_github(writer, "pr")
    body = "# SPEC: A local tracker\n\n## Branch\n\nspec/other\n\n## Problem Statement\n"

    ran = writer.spec("local-tracker", body, SPEC_BRANCH)

    assert ran.status == 1
    assert "## Branch" in ran.err
    assert specs.filed == []


def test_on_github_in_pr_mode_a_spec_with_no_branch_is_turned_down(writer):
    specs = specs_on_github(writer, "pr")

    ran = writer.spec()

    assert ran.status == 1
    assert "branch" in ran.err
    assert specs.filed == []


def test_on_github_with_a_branch_named_target_a_branch_given_is_turned_down(writer, github_specs):
    ran = writer.spec("local-tracker", BODY, SPEC_BRANCH)

    assert ran.status == 1
    assert "main" in ran.err
    assert github_specs.filed == []


def test_on_github_a_spec_file_with_no_spec_heading_is_turned_down(writer, github_specs):
    ran = writer.spec(body="## Problem Statement\n\nNo GitHub.\n")

    assert ran.status == 1
    assert "# SPEC: " in ran.err
    assert github_specs.filed == []


@pytest.mark.parametrize("tracker", ["files", "github"])
def test_a_slug_not_in_kebab_case_is_turned_down(writer, tracker):
    specs = specs_on_github(writer, "main") if tracker == "github" else None

    ran = writer.spec("Local_Tracker")

    assert ran.status == 1
    assert "kebab case" in ran.err
    assert writer.folders() == []
    assert specs is None or specs.filed == []


@pytest.mark.parametrize("failing, what", [
    ("labels=ready-for-agent", "list"),
    ("issue create", "file"),
])
def test_on_github_a_gh_call_that_fails_is_refused_and_says_to_run_again(writer, github_specs,
                                                                        failing, what):
    github_specs.fails = failing

    ran = writer.spec()

    assert ran.status == 1
    assert ran.out == ""
    assert what in ran.err
    assert "HTTP 502: Bad Gateway" in ran.err
    assert "again" in ran.err
    assert github_specs.filed == []


class ConnectedIssues(Issues):
    def answer(self):
        called = self.runner.calls[-1][1:]
        if called[:2] == ["auth", "status"]:
            return Ran(0, "", "")
        if called[:2] == ["repo", "view"]:
            return Ran(0, "owner/repo\n", "")
        if called[:2] == ["api", "user"]:
            return Ran(0, "me\n", "")
        return super().answer()


@pytest.fixture
def github_tickets(writer):
    path = writer.repo.work / LOOP_FILE
    path.write_text(json.dumps({"tracker": "github", "target-branch": "main"}), encoding="utf-8")
    return ConnectedIssues(writer.runner)


def with_body(ticket, body):
    return ticket + "\n" + body


def test_on_github_tickets_are_filed_blockers_first_each_a_labelled_sub_issue_with_its_blockers(
        writer, github_tickets):
    tickets = three_tickets()
    tickets["01-read-loop-json.md"] = with_body(tickets["01-read-loop-json.md"],
                                                "## What to build\n\nRead it.\n")

    ran = writer.tickets("158", tickets)

    assert ran.status == 0, said(ran)
    assert ran.out == "400\n401\n402\n"
    assert [(i["title"], i["parent"], i["labels"], i["blocked_by"])
            for i in github_tickets.issues.values()] == [
        ("TICKET: Read loop.json", "158", ["ready-for-agent"], []),
        ("TICKET: Close in the worktree", "158", ["ready-for-agent"], ["400"]),
        ("TICKET: Claim", "158", ["ready-for-agent"], ["400", "401"])]
    assert github_tickets.issues["400"]["body"] == (
        "<!-- skillworks-ticket spec:158 -->\n\n## What to build\n\nRead it.\n")
    assert all("status:" not in i["body"] for i in github_tickets.issues.values())


@pytest.mark.parametrize("tickets, reason", UNFOLLOWABLE)
def test_on_github_a_ticket_the_tracker_could_not_follow_is_turned_down_before_any_write(
        writer, github_tickets, tickets, reason):
    ran = writer.tickets("158", tickets)

    assert ran.status == 1
    assert reason in ran.err
    assert github_tickets.issues == {}
    assert writer.runner.started("gh") == []


def test_on_github_a_second_run_after_one_that_failed_halfway_files_only_what_is_missing(
        writer, github_tickets):
    github_tickets.fail("issue create", nth=2)
    first = writer.tickets("158", three_tickets())
    github_tickets.writes.clear()

    ran = writer.tickets("158", three_tickets())

    assert first.status == 1
    assert "Already filed: #400" in first.err
    assert "again" in first.err
    assert ran.status == 0, said(ran)
    assert ran.out == "400\n401\n402\n"
    assert github_tickets.writes == [
        "issue create",
        "api --method POST repos/owner/repo/issues/158/sub_issues -F sub_issue_id=9401",
        "api --method POST repos/owner/repo/issues/401/dependencies/blocked_by -F issue_id=9400",
        "issue create",
        "api --method POST repos/owner/repo/issues/158/sub_issues -F sub_issue_id=9402",
        "api --method POST repos/owner/repo/issues/402/dependencies/blocked_by -F issue_id=9400",
        "api --method POST repos/owner/repo/issues/402/dependencies/blocked_by -F issue_id=9401"]


def test_on_github_a_second_run_after_a_full_one_changes_nothing_and_says_so(writer, github_tickets):
    writer.tickets("158", three_tickets())
    github_tickets.writes.clear()

    ran = writer.tickets("158", three_tickets())

    assert ran.status == 0, said(ran)
    assert ran.out == "400\n401\n402\n"
    assert "nothing" in ran.err.lower()
    assert github_tickets.writes == []


def test_on_github_a_loose_ticket_of_another_spec_with_the_title_is_not_linked_and_one_is_filed(
        writer, github_tickets):
    theirs = github_tickets.holds("TICKET: Read loop.json",
                                  body="<!-- skillworks-ticket spec:157 -->\n\nTheirs.\n")

    ran = writer.tickets("158", {"01-read-loop-json.md": ticket_file("TICKET: Read loop.json")})

    assert ran.status == 0, said(ran)
    assert (github_tickets.issues[theirs]["parent"], ran.out) == ("", "401\n")


def test_on_github_a_loose_ticket_that_names_this_spec_is_linked_and_nothing_is_filed_twice(
        writer, github_tickets):
    ours = github_tickets.holds("TICKET: Read loop.json",
                                body="<!-- skillworks-ticket spec:158 -->\n\nOurs.\n")

    ran = writer.tickets("158", {"01-read-loop-json.md": ticket_file("TICKET: Read loop.json")})

    assert ran.status == 0, said(ran)
    assert (list(github_tickets.issues), github_tickets.issues[ours]["parent"]) == ([ours], "158")


def test_on_github_a_loose_ticket_with_no_hidden_line_is_not_linked(writer, github_tickets):
    unmarked = github_tickets.holds("TICKET: Read loop.json", body="Read it.\n")

    ran = writer.tickets("158", {"01-read-loop-json.md": ticket_file("TICKET: Read loop.json")})

    assert ran.status == 0, said(ran)
    assert (github_tickets.issues[unmarked]["parent"], ran.out) == ("", "401\n")


def test_the_command_runs_from_the_plugins_bin_folder(writer):
    body = Path(writer.written("spec-body.md", BODY))

    ran = launch("tracker-publish", "spec", "local-tracker", body.as_posix(), where=writer.repo.work)

    assert ran.status == 0, said(ran)
    assert ran.out == "1\t.specs/0001-local-tracker\n"
