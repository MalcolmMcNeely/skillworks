# Driven through main, so each case checks what reached the remote and what the files Tracker reads back.

import contextlib
import io
import json
from pathlib import Path

import pytest

from conftest import Ran, Repo, git, launch
from files_test import Racing, commit_files, spec_file, ticket_file, write_loop
from github_test import Issues
from steering.target_branch import LOOP_FILE
from tracker import publish
from tracker.files import Files
from tracker.github import GitHub, spec_branch

SPEC_BRANCH = "spec/local-tracker"

BODY = "# SPEC: A local tracker\n\n## Problem Statement\n\nNo GitHub.\n"


class Writer:
    def __init__(self, repo, runner, scratch):
        self.repo = repo
        self.runner = runner
        self.scratch = scratch

    def written(self, name, text):
        path = self.scratch / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path.as_posix()

    def run(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.chdir(self.repo.work):
            status = publish.main(list(argv), self.runner, out, err, lambda seconds: None)
        return Ran(status, out.getvalue(), err.getvalue())

    def spec(self, slug="local-tracker", body=BODY, *branch):
        return self.run("spec", slug, self.written("spec-body.md", body), *branch)

    def tickets(self, spec, tickets):
        return self.run("tickets", spec, *[self.written("tickets/" + name, text)
                                           for name, text in tickets.items()])

    # Pushed from a clone of its own, so the main checkout never holds what the remote does.
    def push(self, files, branch="main"):
        other = self.repo.other_checkout()
        if branch != "main":
            git(other, "checkout", "--quiet", "-B", branch)
        commit_files(other, files, "Tracker state")
        git(other, "push", "--quiet", "origin", branch)

    def on_remote(self, path, branch="main"):
        return git(self.repo.origin, "show", "{}:{}".format(branch, path))

    def folders(self, branch="main"):
        return git(self.repo.origin, "ls-tree", "--name-only", branch, ".specs/").split()

    def tracker(self, spec, target="main"):
        return Files(self.runner, self.repo.work, target, spec, lambda seconds: None)


@pytest.fixture
def writer(tmp_path):
    repo = Repo(tmp_path / "repo")
    write_loop(repo.work, "main")
    return Writer(repo, Racing(), tmp_path / "scratch")


def said(ran):
    return ran.out + ran.err


def test_a_spec_is_pushed_as_a_numbered_folder_with_its_frontmatter(writer):
    ran = writer.spec()

    assert ran.status == 0, said(ran)
    assert ran.out == "1\t.specs/0001-local-tracker\n"
    assert writer.on_remote(".specs/0001-local-tracker/spec.md") == "---\nstatus: open\n---\n\n" + BODY
    assert writer.tracker("1").spec_state("1") == "open"
    assert writer.tracker("1").spec_title("1") == "SPEC: A local tracker"


def test_a_spec_takes_the_highest_number_on_the_remote_plus_one(writer):
    writer.push({".specs/0007-older/spec.md": spec_file(), ".specs/0003-oldest/spec.md": spec_file()})

    ran = writer.spec()

    assert ran.status == 0, said(ran)
    assert ".specs/0008-local-tracker" in writer.folders()


def test_the_checkout_is_left_as_it_was(writer):
    head = git(writer.repo.work, "rev-parse", "HEAD")
    (writer.repo.work / "staged.txt").write_text("staged\n", encoding="utf-8")
    git(writer.repo.work, "add", "staged.txt")

    ran = writer.spec()

    assert ran.status == 0, said(ran)
    assert git(writer.repo.work, "rev-parse", "HEAD") == head
    assert git(writer.repo.work, "diff", "--cached", "--name-only").split() == ["staged.txt"]
    assert not (writer.repo.work / ".specs").exists()


def test_two_specs_written_at_once_end_with_two_numbers(writer):
    rival = {".specs/0001-rival/spec.md": spec_file()}
    writer.runner.before_push = lambda: writer.push(rival)

    ran = writer.spec()

    assert ran.status == 0, said(ran)
    assert ran.out == "2\t.specs/0002-local-tracker\n"
    assert writer.folders() == [".specs/0001-rival", ".specs/0002-local-tracker"]


def test_a_body_that_brings_its_own_frontmatter_is_turned_down(writer):
    ran = writer.spec(body="---\nstatus: closed\n---\n\n" + BODY)

    assert ran.status == 1
    assert "frontmatter" in ran.err
    assert writer.folders() == []


def test_in_spec_mode_the_folder_is_on_the_specs_branch_and_names_it(writer):
    write_loop(writer.repo.work, "spec")
    writer.push({"base.txt": "base\nspec branch\n"}, branch=SPEC_BRANCH)

    ran = writer.spec("local-tracker", BODY, SPEC_BRANCH)

    assert ran.status == 0, said(ran)
    assert writer.folders() == []
    text = writer.on_remote(".specs/0001-local-tracker/spec.md", SPEC_BRANCH)
    assert text.startswith("---\nstatus: open\nbranch: {}\n---\n".format(SPEC_BRANCH))
    assert writer.tracker("1", target=None).branch_of("1") == SPEC_BRANCH


def test_in_spec_mode_the_number_counts_the_specs_on_every_branch(writer):
    write_loop(writer.repo.work, "spec")
    writer.push({".specs/0004-elsewhere/spec.md": spec_file(branch="spec/elsewhere")},
                branch="spec/elsewhere")
    writer.push({"base.txt": "base\nspec branch\n"}, branch=SPEC_BRANCH)

    ran = writer.spec("local-tracker", BODY, SPEC_BRANCH)

    assert ran.status == 0, said(ran)
    assert ".specs/0005-local-tracker" in writer.folders(SPEC_BRANCH)


def test_in_spec_mode_two_specs_written_at_once_on_two_branches_end_with_two_numbers(writer):
    write_loop(writer.repo.work, "spec")
    writer.push({"base.txt": "base\nrival branch\n"}, branch="spec/rival")
    writer.push({"base.txt": "base\nspec branch\n"}, branch=SPEC_BRANCH)
    rival = Writer(writer.repo, Racing(), writer.scratch / "rival")
    rivalled = []
    # The rival runs whole the moment this writer first pushes, so this writer's number is the one taken.
    writer.runner.before_push = lambda: rivalled.append(rival.spec("rival", BODY, "spec/rival"))

    ran = writer.spec("local-tracker", BODY, SPEC_BRANCH)

    assert rivalled[0].out == "1\t.specs/0001-rival\n", said(rivalled[0])
    assert ran.status == 0, said(ran)
    assert ran.out == "2\t.specs/0002-local-tracker\n"
    assert writer.tracker("2", target=None).branch_of("2") == SPEC_BRANCH


def test_in_spec_mode_a_number_reserved_with_no_folder_left_is_not_taken_again(writer):
    write_loop(writer.repo.work, "spec")
    writer.push({"base.txt": "base\nspec branch\n"}, branch=SPEC_BRANCH)
    head = git(writer.repo.origin, "rev-parse", "main").strip()
    git(writer.repo.origin, "update-ref", publish.RESERVED + "3", head)

    ran = writer.spec("local-tracker", BODY, SPEC_BRANCH)

    assert ran.status == 0, said(ran)
    assert ran.out == "4\t.specs/0004-local-tracker\n"


def test_in_spec_mode_a_spec_with_no_branch_is_turned_down(writer):
    write_loop(writer.repo.work, "spec")

    ran = writer.spec()

    assert ran.status == 1
    assert "branch" in ran.err


def test_in_spec_mode_a_branch_not_on_the_remote_is_turned_down(writer):
    write_loop(writer.repo.work, "spec")

    ran = writer.spec("local-tracker", BODY, SPEC_BRANCH)

    assert ran.status == 1
    assert SPEC_BRANCH in ran.err


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


def test_tickets_are_pushed_into_the_specs_folder_and_the_tracker_reads_them(writer):
    writer.spec()

    ran = writer.tickets("1", three_tickets())

    assert ran.status == 0, said(ran)
    tracker = writer.tracker("1")
    assert tracker.tickets("1") == ["1", "2", "3"]
    assert tracker.open_tickets("1") == ["1", "2", "3"]
    assert tracker.title("2") == "TICKET: Close in the worktree"
    assert [tracker.open_blockers(ticket) for ticket in ["1", "2", "3"]] == [0, 1, 2]
    assert writer.on_remote(".specs/0001-local-tracker/tickets/03-claim.md") == three_tickets()["03-claim.md"]


def test_in_spec_mode_tickets_reach_the_specs_branch(writer):
    write_loop(writer.repo.work, "spec")
    writer.push({"base.txt": "base\nspec branch\n"}, branch=SPEC_BRANCH)
    writer.spec("local-tracker", BODY, SPEC_BRANCH)

    ran = writer.tickets("1", three_tickets())

    assert ran.status == 0, said(ran)
    assert writer.tracker("1", target=None).tickets("1") == ["1", "2", "3"]


def test_tickets_for_a_spec_with_tickets_already_are_turned_down(writer):
    writer.spec()
    writer.tickets("1", three_tickets())

    ran = writer.tickets("1", {"04-more.md": ticket_file("TICKET: More")})

    assert ran.status == 1
    assert "already" in ran.err


def test_tickets_for_a_spec_with_no_folder_are_turned_down(writer):
    ran = writer.tickets("9", three_tickets())

    assert ran.status == 1
    assert "9" in ran.err


UNFOLLOWABLE = [
    ({"01-a.md": ticket_file("TICKET: A", blocked_by=[2]), "02-b.md": ticket_file("TICKET: B")},
     "dependency order"),
    ({"01-a.md": ticket_file("TICKET: A", blocked_by=[3])}, "dependency order"),
    ({"01-a.md": ticket_file("TICKET: A", status="closed")}, "status: open"),
    ({"01-a.md": ticket_file("TICKET: A", claimed_by="someone@example.invalid")}, "claimed-by"),
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


def test_a_drift_report_is_pushed_to_the_end_of_the_specs_file(writer):
    writer.spec()

    ran = writer.run("drift", "1", writer.written("drift.md", REPORT))

    assert ran.status == 0, said(ran)
    assert ran.out == ".specs/0001-local-tracker/spec.md\n"
    text = writer.on_remote(".specs/0001-local-tracker/spec.md")
    assert text == "---\nstatus: open\n---\n\n" + BODY + "\n" + REPORT
    assert writer.tracker("1").drift_report("1") == "- Story 1: Done\n- Story 2: Missing"


def test_a_second_drift_report_takes_the_place_of_the_first(writer):
    writer.spec()
    writer.run("drift", "1", writer.written("drift.md", REPORT))

    ran = writer.run("drift", "1", writer.written("again.md", "## Drift report\n\nAll done.\n"))

    assert ran.status == 0, said(ran)
    text = writer.on_remote(".specs/0001-local-tracker/spec.md")
    assert text.count("## Drift report") == 1
    assert "Missing" not in text
    assert writer.tracker("1").drift_report("1") == "All done."


def test_a_drift_report_that_loses_a_race_reads_again_and_keeps_the_rivals_change(writer):
    writer.spec()
    rival = "---\nstatus: open\n---\n\n" + BODY + "\nA rival line.\n"
    writer.runner.before_push = lambda: writer.push({".specs/0001-local-tracker/spec.md": rival})

    ran = writer.run("drift", "1", writer.written("drift.md", REPORT))

    assert ran.status == 0, said(ran)
    text = writer.on_remote(".specs/0001-local-tracker/spec.md")
    assert "A rival line." in text
    assert text.endswith(REPORT)


def test_a_drift_report_without_its_heading_is_turned_down(writer):
    writer.spec()

    ran = writer.run("drift", "1", writer.written("drift.md", "- Story 1: Done\n"))

    assert ran.status == 1
    assert "## Drift report" in ran.err
    assert writer.tracker("1").drift_report("1") == ""


def test_in_spec_mode_a_drift_report_reaches_the_specs_branch(writer):
    write_loop(writer.repo.work, "spec")
    writer.push({"base.txt": "base\nspec branch\n"}, branch=SPEC_BRANCH)
    writer.spec("local-tracker", BODY, SPEC_BRANCH)

    ran = writer.run("drift", "1", writer.written("drift.md", REPORT))

    assert ran.status == 0, said(ran)
    assert writer.on_remote(".specs/0001-local-tracker/spec.md", SPEC_BRANCH).endswith(REPORT)


def test_a_drift_report_for_a_spec_with_no_folder_is_turned_down(writer):
    ran = writer.run("drift", "9", writer.written("drift.md", REPORT))

    assert ran.status == 1
    assert "Spec 9 has no folder on origin/main" in ran.err


NAMES = "## Name report\n\n### Renames\n\n- `Batch`: it now holds a whole spec.\n"


def test_a_name_report_is_pushed_below_the_drift_report_and_each_reads_back_alone(writer):
    writer.spec()
    writer.run("drift", "1", writer.written("drift.md", REPORT))

    ran = writer.run("names", "1", writer.written("names.md", NAMES))

    assert ran.status == 0, said(ran)
    assert ran.out == ".specs/0001-local-tracker/spec.md\n"
    text = writer.on_remote(".specs/0001-local-tracker/spec.md")
    assert text == "---\nstatus: open\n---\n\n" + BODY + "\n" + REPORT + "\n" + NAMES
    assert writer.tracker("1").drift_report("1") == "- Story 1: Done\n- Story 2: Missing"
    assert writer.tracker("1").name_report("1") == (
        "### Renames\n\n- `Batch`: it now holds a whole spec.")


def test_a_second_name_report_takes_the_place_of_the_first(writer):
    writer.spec()
    writer.run("names", "1", writer.written("names.md", NAMES))

    ran = writer.run("names", "1", writer.written("again.md",
                                                  "## Name report\n\n### Renames\n\n- None\n"))

    assert ran.status == 0, said(ran)
    assert writer.on_remote(".specs/0001-local-tracker/spec.md").count("## Name report") == 1
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
            return Ran(0, "".join("{0}\thttps://github.com/owner/repo/issues/{0}\t{1}\n".format(
                number, title) for number, title in self.open), "")
        if called[:2] == ["issue", "create"]:
            assert called[called.index("--label") + 1] == "ready-for-agent"
            title = called[called.index("--title") + 1]
            body = Path(called[called.index("--body-file") + 1]).read_text(encoding="utf-8")
            number = str(400 + len(self.filed) + 1)
            self.filed.append((title, body))
            self.open.append((number, title))
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
    assert github_specs.filed == [("SPEC: A local tracker", "## Problem Statement\n\nNo GitHub.\n")]
    assert len(writer.runner.built("issue create")) == 1


def test_on_github_an_open_spec_with_the_title_is_printed_and_nothing_is_filed(writer, github_specs):
    github_specs.open = [("312", "SPEC: Something else"), ("398", "SPEC: A local tracker")]

    ran = writer.spec()

    assert ran.status == 0, said(ran)
    assert ran.out == "398\thttps://github.com/owner/repo/issues/398\n"
    assert github_specs.filed == []


def test_on_github_a_second_run_files_nothing_twice(writer, github_specs):
    first = writer.spec()

    ran = writer.spec()

    assert ran.out == first.out, said(ran)
    assert len(github_specs.filed) == 1


def test_on_github_in_spec_mode_the_branch_section_is_written_from_the_branch_named(writer):
    specs = specs_on_github(writer, "spec")

    ran = writer.spec("local-tracker", BODY, SPEC_BRANCH)

    assert ran.status == 0, said(ran)
    body = specs.filed[0][1]
    assert body == "## Branch\n\n{}\n\n## Problem Statement\n\nNo GitHub.\n".format(SPEC_BRANCH)
    assert spec_branch(body) == SPEC_BRANCH


def test_on_github_in_spec_mode_a_spec_that_holds_its_own_branch_section_is_turned_down(writer):
    specs = specs_on_github(writer, "spec")
    body = "# SPEC: A local tracker\n\n## Branch\n\nspec/other\n\n## Problem Statement\n"

    ran = writer.spec("local-tracker", body, SPEC_BRANCH)

    assert ran.status == 1
    assert "## Branch" in ran.err
    assert specs.filed == []


def test_on_github_in_spec_mode_a_spec_with_no_branch_is_turned_down(writer):
    specs = specs_on_github(writer, "spec")

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
    assert github_tickets.issues["400"]["body"] == "## What to build\n\nRead it.\n"
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


def test_the_command_runs_from_the_plugins_bin_folder(writer):
    body = Path(writer.written("spec-body.md", BODY))

    ran = launch("tracker-publish", "spec", "local-tracker", body.as_posix(), where=writer.repo.work)

    assert ran.status == 0, said(ran)
    assert ran.out == "1\t.specs/0001-local-tracker\n"
