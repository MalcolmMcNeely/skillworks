import ast

import pytest

from conftest import SCRIPTS, Ran
from stop import REFUSED, Stop
from tracker.github import CLAIM_WAIT, GitHub


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
    assert "to-spec" in stopped.value.said


# --- filing a ticket under a spec ---------------------------------------------

class Issues:
    # Holds what was filed, so a filed ticket is read back the way the loop reads every ticket.
    def __init__(self, runner, fails=""):
        self.runner = runner
        self.fails = fails
        self.filed = {}
        self.children = []
        runner.stub("gh", does=self.answer)

    def answer(self):
        called = self.runner.calls[-1][1:]
        asked = " ".join(called)
        if self.fails and asked.startswith(self.fails):
            return Ran(1, "", "HTTP 422: refused\n")
        if called[:2] == ["issue", "create"]:
            number = str(400 + len(self.filed))
            self.filed[number] = dict(zip(called[2::2], called[3::2]))
            return Ran(0, "https://github.com/owner/repo/issues/{}\n".format(number), "")
        if asked.startswith("api repos/owner/repo/issues/") and asked.endswith("--jq .id"):
            return Ran(0, "9" + asked.split(" ")[1].rsplit("/", 1)[-1] + "\n", "")
        if asked == "api --method POST repos/owner/repo/issues/158/sub_issues -F sub_issue_id=9400":
            self.children.append("400")
            return Ran(0, "{}\n", "")
        if 'select(.state=="open")' in asked:
            return Ran(0, "".join(number + "\n" for number in self.children), "")
        return Ran(1, "", "no answer for: " + asked + "\n")


def test_a_filed_ticket_is_a_sub_issue_of_the_spec_with_its_title_body_and_label(runner):
    issues = Issues(runner)

    number = github(runner).file_ticket("158", "TICKET: Build the Gaps", "## What to build\n\nS2.\n")

    assert number == "400"
    assert issues.filed["400"] == {"--title": "TICKET: Build the Gaps",
                                   "--body": "## What to build\n\nS2.\n",
                                   "--label": "ready-for-agent"}
    assert issues.children == ["400"]


def test_a_filed_ticket_is_listed_among_the_specs_open_tickets(runner):
    Issues(runner)
    tracker = github(runner)

    number = tracker.file_ticket("158", "TICKET: Build the Gaps", "S2.\n")

    assert tracker.open_tickets("158") == [number]


@pytest.mark.parametrize("fails, reason", [
    ("issue create", "would not file"),
    ("api --method POST", "is not a sub-issue of spec #158"),
])
def test_a_ticket_github_would_not_file_under_the_spec_stops_and_says_so(runner, fails, reason):
    Issues(runner, fails=fails)

    with pytest.raises(Stop) as stopped:
        github(runner).file_ticket("158", "TICKET: Build the Gaps", "S2.\n")

    assert stopped.value.status == REFUSED
    assert reason in stopped.value.said
    assert "HTTP 422: refused" in stopped.value.said


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
