import ast

import pytest

from conftest import SCRIPTS, Ran
from stop import REFUSED, Stop
from tracker.github import CLAIM_WAIT, Filing, GitHub, NewTicket


def github(runner):
    tracker = GitHub(runner, "/checkout", "owner/repo")
    tracker.me = "me"
    return tracker


def asked(runner):
    return [" ".join(call[1:]) for call in runner.started("gh")]


def test_every_question_is_asked_with_no_prompt_in_the_checkout(runner):
    runner.stub("gh", says="open\n")

    github(runner).state("168")

    [call] = runner.made
    assert call.where == "/checkout"
    assert call.env == {"GH_PROMPT_DISABLED": "1"}


def test_connecting_reads_the_repo_and_the_login(runner):
    def answer():
        line = " ".join(runner.calls[-1][1:])
        if line.startswith("repo view"):
            return Ran(0, "owner/repo\n", "")
        if line.startswith("api user"):
            return Ran(0, "me\n", "")
        return None
    runner.stub("gh", does=answer)
    tracker = GitHub(runner, "/checkout")

    assert tracker.connect() == ""
    assert (tracker.repo, tracker.me) == ("owner/repo", "me")


def test_connecting_with_no_gh_says_so(runner):
    runner.hide("gh")

    assert GitHub(runner, "/checkout").connect() == "gh is not installed"


def test_connecting_with_no_login_says_how_to_log_in(runner):
    runner.stub("gh", status=1)

    assert "gh auth login" in GitHub(runner, "/checkout").connect()


def test_a_state_that_would_not_be_read_is_no_state(runner):
    runner.stub("gh", status=1)

    assert github(runner).state("168") is None


def test_a_ticket_with_no_count_of_its_blockers_has_none(runner):
    runner.stub("gh", says="missing\n")

    assert github(runner).open_blockers("168") is None


def test_a_ticket_counts_its_open_blockers(runner):
    runner.stub("gh", says="2\n")

    assert github(runner).open_blockers("168") == 2


def test_the_rows_of_a_spec_are_a_number_a_state_and_a_title(runner):
    runner.stub("gh", says="168\topen\tTICKET: One\n169\tclosed\n")

    assert github(runner).ticket_rows("158") == [
        ("168", "open", "TICKET: One"), ("169", "closed", "")]


def test_a_claim_nobody_else_holds_is_kept(runner):
    runner.stub("gh", says="\n")
    waits = []

    assert github(runner).claim("168", waits.append) == ""
    assert waits == [CLAIM_WAIT]
    assert "issue edit 168 --remove-assignee @me" not in asked(runner)


def test_a_claim_somebody_else_holds_is_let_go_and_names_them(runner):
    runner.stub("gh", says="other\n")

    assert github(runner).claim("168", lambda seconds: None) == "other"
    assert asked(runner)[0] == "issue edit 168 --add-assignee @me"
    assert asked(runner)[-1] == "issue edit 168 --remove-assignee @me"


def test_a_close_carries_its_comment(runner):
    runner.stub("gh")

    assert github(runner).close("168", "Done, and proved.")
    assert asked(runner) == ["issue close 168 --comment Done, and proved."]


def test_a_reopen_that_failed_says_so(runner):
    runner.stub("gh", status=1)

    assert not github(runner).reopen("168")


def test_a_last_comment_the_tracker_would_not_give_is_none(runner):
    runner.stub("gh", status=1)

    assert github(runner).last_comment("168") is None


def test_a_closing_note_is_the_last_comment_on_the_issue_the_trailer_names(runner):
    runner.stub("gh", says="Done, and proved.\n")

    assert github(runner).closing_note("#168") == "Done, and proved."
    assert asked(runner) == ["issue view 168 --json comments --jq .comments[-1].body"]


def test_a_drift_report_is_the_last_comment_on_the_spec_below_its_heading(runner):
    runner.stub("gh", says="## Drift report\n\n- Story 1: Done\n")

    assert github(runner).drift_report("158") == "- Story 1: Done"
    assert asked(runner) == ["issue view 158 --json comments --jq .comments[-1].body"]


@pytest.mark.parametrize("last", ["Looks good to me.\n", ""])
def test_a_spec_whose_last_comment_is_no_drift_report_has_none(runner, last):
    runner.stub("gh", says=last)

    assert github(runner).drift_report("158") == ""


def test_a_name_report_is_the_last_comment_on_the_spec_below_its_heading(runner):
    runner.stub("gh", says="## Name report\n\n### Renames\n\n- None\n")

    assert github(runner).name_report("158") == "### Renames\n\n- None"
    assert asked(runner) == ["issue view 158 --json comments --jq .comments[-1].body"]


@pytest.mark.parametrize("last", ["## Drift report\n\n- S1: Done\n", "Looks good to me.\n", ""])
def test_a_spec_whose_last_comment_is_no_name_report_has_none(runner, last):
    runner.stub("gh", says=last)

    assert github(runner).name_report("158") == ""


def test_a_commit_names_its_issue_by_number_alone(runner):
    assert github(runner).trailer("168") == "#168"
    assert github(runner).reference("168") == "168"


def test_a_spec_is_left_for_a_person_or_its_pull_request_to_close(runner):
    runner.stub("gh")

    assert github(runner).close_spec("158") == ""
    assert asked(runner) == []


def test_the_body_of_a_spec_is_read_whole(runner):
    runner.stub("gh", says="## Branch\n\n`spec/x`\n")

    assert github(runner).spec_body("158") == "## Branch\n\n`spec/x`\n"
    assert asked(runner) == ["api repos/owner/repo/issues/158 --jq .body"]


def test_the_branch_of_a_spec_is_the_one_its_body_names(runner):
    runner.stub("gh", says="## Problem Statement\r\n\r\nWords.\r\n\r\n## Branch\r\n\r\n`spec/target-branch`\r\n\r\n## Solution\r\n")

    assert github(runner).branch_of("158") == "spec/target-branch"


def test_a_spec_that_names_no_branch_stops_and_says_so(runner):
    runner.stub("gh", says="## Problem Statement\n\nWords.\n")

    with pytest.raises(Stop) as stopped:
        github(runner).branch_of("158")

    assert stopped.value.status == REFUSED
    assert "## Branch" in stopped.value.said
    assert "/skillworks:grill writes it" in stopped.value.said


# --- filing a ticket under a spec ---------------------------------------------

class Issues:
    # Kept across filings, so a second filing reads what the first one left.
    def __init__(self, runner):
        self.runner = runner
        self.issues = {}
        self.fails = []
        self.writes = []
        runner.stub("gh", does=self.answer)

    def holds(self, title, parent="", state="open", blocked_by=(), body=""):
        number = str(400 + len(self.issues))
        self.issues[number] = {"title": title, "body": body, "labels": ["ready-for-agent"],
                               "state": state, "parent": parent, "blocked_by": list(blocked_by)}
        return number

    # Only the nth call that starts so fails, so a second filing finds GitHub answering again.
    def fail(self, start, nth=1):
        self.fails.append([start, nth])

    def failing(self, asked):
        for held in self.fails:
            if asked.startswith(held[0]):
                held[1] -= 1
                if held[1] == 0:
                    return True
        return False

    def answer(self):
        called = self.runner.calls[-1][1:]
        asked = " ".join(called)
        if self.failing(asked):
            return Ran(1, "", "HTTP 422: refused\n")
        if called[:2] == ["issue", "create"]:
            given = dict(zip(called[2::2], called[3::2]))
            number = self.holds(given["--title"])
            self.issues[number].update(body=given["--body"], labels=[given["--label"]])
            self.writes.append("issue create")
            return Ran(0, "https://github.com/owner/repo/issues/{}\n".format(number), "")
        if called[:3] == ["api", "--method", "POST"]:
            number = called[3].split("/")[4]
            given = called[-1].split("=", 1)[1][1:]
            if called[3].endswith("/sub_issues"):
                self.issues[given]["parent"] = number
            else:
                self.issues[number]["blocked_by"].append(given)
            self.writes.append(asked)
            return Ran(0, "{}\n", "")
        if called[:2] == ["api", "--paginate"] and called[2].endswith("/sub_issues"):
            spec = called[2].split("/")[4]
            children = [(n, i) for n, i in self.issues.items() if i["parent"] == spec]
            if 'select(.state=="open")' in called[-1]:
                return Ran(0, "".join(n + "\n" for n, i in children if i["state"] == "open"), "")
            return Ran(0, "".join("{}\t{}\t{}\n".format(n, i["state"], i["title"])
                                  for n, i in children), "")
        if called[:2] == ["api", "--paginate"] and called[2].endswith("/dependencies/blocked_by"):
            number = called[2].split("/")[4]
            return Ran(0, "".join(n + "\n" for n in self.issues[number]["blocked_by"]), "")
        if called[:2] == ["api", "--paginate"] and "labels=ready-for-agent&state=open" in called[2]:
            ready = [(n, i) for n, i in self.issues.items()
                     if i["state"] == "open" and "ready-for-agent" in i["labels"]]
            if ".body" in called[-1]:
                return Ran(0, "".join("{}\t{}\t{}\n".format(n, i["body"].split("\n", 1)[0], i["title"])
                                      for n, i in ready), "")
            return Ran(0, "".join("{}\t{}\n".format(n, i["title"]) for n, i in ready), "")
        if asked.endswith("--jq .id"):
            return Ran(0, "9" + called[1].rsplit("/", 1)[-1] + "\n", "")
        if asked.endswith('--jq .parent_issue_url // ""'):
            parent = self.issues[called[1].rsplit("/", 1)[-1]]["parent"]
            return Ran(0, (parent and "https://api.github.com/repos/owner/repo/issues/" + parent)
                       + "\n", "")
        return Ran(1, "", "no answer for: " + asked + "\n")


# Numbered blockers first, as to-tickets writes a set.
A_SET = [NewTicket("TICKET: Read the file", "## What to build\n\nOne.\n"),
         NewTicket("TICKET: Check the file", "Two.\n"),
         NewTicket("TICKET: Write the report", "Three.\n",
                   ("TICKET: Read the file", "TICKET: Check the file"))]


def test_a_set_is_filed_in_order_each_a_sub_issue_with_its_label_and_its_blockers(runner):
    issues = Issues(runner)

    filing = github(runner).file_tickets("158", A_SET)

    assert filing == Filing(["400", "401", "402"], True)
    assert [(i["title"], i["parent"], i["labels"], i["blocked_by"])
            for i in issues.issues.values()] == [
        ("TICKET: Read the file", "158", ["ready-for-agent"], []),
        ("TICKET: Check the file", "158", ["ready-for-agent"], []),
        ("TICKET: Write the report", "158", ["ready-for-agent"], ["400", "401"])]
    assert issues.issues["400"]["body"] == (
        "<!-- skillworks-ticket spec:158 -->\n\n## What to build\n\nOne.\n")


def test_a_second_filing_after_a_full_one_changes_nothing_and_says_so(runner):
    issues = Issues(runner)
    tracker = github(runner)
    tracker.file_tickets("158", A_SET)
    issues.writes.clear()

    filing = tracker.file_tickets("158", A_SET)

    assert filing == Filing(["400", "401", "402"], False)
    assert issues.writes == []


def test_a_second_filing_after_one_that_failed_halfway_files_and_links_only_what_is_missing(runner):
    issues = Issues(runner)
    tracker = github(runner)
    issues.fail("issue create", nth=2)
    with pytest.raises(Stop):
        tracker.file_tickets("158", A_SET)
    issues.writes.clear()

    filing = tracker.file_tickets("158", A_SET)

    assert filing == Filing(["400", "401", "402"], True)
    assert issues.writes == [
        "issue create",
        "api --method POST repos/owner/repo/issues/158/sub_issues -F sub_issue_id=9401",
        "issue create",
        "api --method POST repos/owner/repo/issues/158/sub_issues -F sub_issue_id=9402",
        "api --method POST repos/owner/repo/issues/402/dependencies/blocked_by -F issue_id=9400",
        "api --method POST repos/owner/repo/issues/402/dependencies/blocked_by -F issue_id=9401"]


def test_a_second_filing_after_an_issue_was_filed_and_not_linked_links_it(runner):
    issues = Issues(runner)
    tracker = github(runner)
    tracker.file_tickets("158", A_SET[:2])
    issues.holds("TICKET: Write the report", blocked_by=["400"],
                 body="<!-- skillworks-ticket spec:158 -->\n\nThree.\n")
    issues.writes.clear()

    filing = tracker.file_tickets("158", A_SET)

    assert filing == Filing(["400", "401", "402"], True)
    assert issues.writes == [
        "api --method POST repos/owner/repo/issues/158/sub_issues -F sub_issue_id=9402",
        "api --method POST repos/owner/repo/issues/402/dependencies/blocked_by -F issue_id=9401"]


def test_an_issue_under_another_spec_or_a_closed_one_is_not_taken_for_the_ticket(runner):
    issues = Issues(runner)
    issues.holds("TICKET: Read the file", parent="157")
    issues.holds("TICKET: Read the file", parent="158", state="closed")

    filing = github(runner).file_tickets("158", A_SET[:1])

    assert filing == Filing(["402"], True)
    assert issues.issues["402"]["parent"] == "158"


@pytest.mark.parametrize("start, nth, reason, done", [
    ("issue create", 1, "would not file the ticket TICKET: Read the file", "Nothing was filed"),
    ("issue create", 3, "would not file the ticket TICKET: Write the report",
     "Already filed: #400, #401"),
    ("api --method POST repos/owner/repo/issues/158/sub_issues", 2,
     "would not make #401 a sub-issue of spec #158", "Already filed: #400, #401"),
    ("api --method POST repos/owner/repo/issues/402/dependencies", 1,
     "would not mark #402 blocked by #400", "Already filed: #400, #401, #402"),
    ("api --paginate repos/owner/repo/issues/158/sub_issues", 1,
     "would not list the tickets of spec #158", "Nothing was filed"),
])
def test_a_filing_gh_refuses_stops_and_names_the_tickets_already_filed(runner, start, nth, reason,
                                                                       done):
    issues = Issues(runner)
    issues.fail(start, nth)

    with pytest.raises(Stop) as stopped:
        github(runner).file_tickets("158", A_SET)

    assert stopped.value.status == REFUSED
    assert reason in stopped.value.said
    assert done in stopped.value.said
    assert "HTTP 422: refused" in stopped.value.said
    assert "files nothing twice" in stopped.value.said


@pytest.mark.parametrize("tickets", [
    [NewTicket("TICKET: One", ""), NewTicket("TICKET: One", "")],
    [NewTicket("TICKET: Two", "", ("TICKET: One",)), NewTicket("TICKET: One", "")],
])
def test_a_set_with_a_title_twice_or_a_blocker_not_before_it_is_turned_down(runner, tickets):
    Issues(runner)

    with pytest.raises(Stop) as stopped:
        github(runner).file_tickets("158", tickets)

    assert stopped.value.status == REFUSED
    assert runner.calls == []


def test_a_ticket_the_driver_files_is_a_set_of_one_under_the_spec(runner):
    issues = Issues(runner)

    number = github(runner).file_ticket("158", "TICKET: Build the Gaps", "## What to build\n\nS2.\n")

    assert number == "400"
    assert issues.issues["400"]["title"] == "TICKET: Build the Gaps"
    assert issues.issues["400"]["parent"] == "158"


def test_a_ticket_the_driver_files_opens_with_the_line_that_names_its_spec(runner):
    issues = Issues(runner)

    github(runner).file_ticket("158", "TICKET: Build the Gaps", "## What to build\n\nS2.\n")

    assert issues.issues["400"]["body"] == (
        "<!-- skillworks-ticket spec:158 -->\n\n## What to build\n\nS2.\n")


def test_a_ticket_the_driver_files_again_after_a_failure_is_not_filed_twice(runner):
    issues = Issues(runner)
    tracker = github(runner)
    issues.fail("api --method POST")
    with pytest.raises(Stop):
        tracker.file_ticket("158", "TICKET: Build the Gaps", "S2.\n")

    number = tracker.file_ticket("158", "TICKET: Build the Gaps", "S2.\n")

    assert number == "400"
    assert list(issues.issues) == ["400"]
    assert tracker.open_tickets("158") == ["400"]


# --- only the Tracker asks gh about an issue ---------------------------------

# Every issue, sub-issue and dependency read goes through `gh api`, and every write through `gh issue`.
ISSUE_WORK = ("api", "issue")


def asks_of_gh(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.List) and node.elts and getattr(node.elts[0], "value", None) == "gh":
            if len(node.elts) > 1 and isinstance(node.elts[1], ast.Constant):
                yield node.elts[1:]
        if isinstance(node, ast.Call):
            named = getattr(node.func, "attr", getattr(node.func, "id", None))
            if named == "gh" and node.args and isinstance(node.args[0], ast.Constant):
                yield node.args


def first_words_to_gh(tree):
    return [asked[0].value for asked in asks_of_gh(tree)]


# The fixed text of a path still shows through a path built with format or +.
def spelled(nodes):
    return " ".join(part.value for node in nodes for part in ast.walk(node)
                    if isinstance(part, ast.Constant) and isinstance(part.value, str))


# The preflight asks `gh api` about the login, the repo and its branches. A path the code does not spell could be anything.
def about_an_issue(asked):
    word = asked[0].value
    if word == "api":
        path = spelled(asked[1:])
        return path == "" or "issue" in path
    return word in ISSUE_WORK


def test_the_walk_finds_the_issue_work_the_tracker_itself_asks_of_gh():
    tree = ast.parse((SCRIPTS / "tracker" / "github.py").read_text(encoding="utf-8"))

    assert set(ISSUE_WORK) <= set(first_words_to_gh(tree))


@pytest.mark.parametrize("code, issue_work", [
    ('gh("api", "repos/{}/issues/{}".format(repo, n))', True),
    ('run(["gh", "api", path])', True),
    ('run(["gh", "api", "repos/" + repo, "--jq", ".has_issues"])', True),
    ('gh("issue", "close", n)', True),
    ('gh("api", "user", "--jq", ".login")', False),
    ('run(["gh", "api", "repos/{}/branches/{}".format(repo, branch)])', False),
])
def test_the_walk_counts_a_gh_api_path_about_an_issue_or_spelled_nowhere_as_issue_work(code, issue_work):
    [asked] = asks_of_gh(ast.parse(code))

    assert about_an_issue(asked) == issue_work


def test_no_script_outside_the_tracker_asks_gh_about_an_issue():
    tracker = SCRIPTS / "tracker"
    reached = []
    for script in SCRIPTS.rglob("*.py"):
        if tracker in script.parents:
            continue
        tree = ast.parse(script.read_text(encoding="utf-8"))
        reached += ["{}: gh {}".format(script.relative_to(SCRIPTS).as_posix(), spelled(asked))
                    for asked in asks_of_gh(tree) if about_an_issue(asked)]

    assert reached == []
