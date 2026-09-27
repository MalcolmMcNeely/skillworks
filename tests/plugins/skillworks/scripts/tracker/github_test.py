import ast

import pytest

from conftest import SCRIPTS, Ran
from stop import REFUSED, Stop
from tracker import files as files_tracker
from tracker import github as github_tracker
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


# Neither Tracker imports the other, so this is what holds the two headings to one.
def test_both_trackers_find_a_drift_report_by_one_heading():
    assert github_tracker.DRIFT_REPORT == files_tracker.DRIFT_REPORT


@pytest.mark.parametrize("last", ["Looks good to me.\n", ""])
def test_a_spec_whose_last_comment_is_no_drift_report_has_none(runner, last):
    runner.stub("gh", says=last)

    assert github(runner).drift_report("158") == ""


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


# --- only the Tracker asks gh about an issue ---------------------------------

# Every issue, sub-issue and dependency read goes through `gh api`, and every write through `gh issue`.
ISSUE_WORK = ("api", "issue")


def first_words_to_gh(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.List) and node.elts and getattr(node.elts[0], "value", None) == "gh":
            if len(node.elts) > 1 and isinstance(node.elts[1], ast.Constant):
                yield node.elts[1].value
        if isinstance(node, ast.Call):
            named = getattr(node.func, "attr", getattr(node.func, "id", None))
            if named == "gh" and node.args and isinstance(node.args[0], ast.Constant):
                yield node.args[0].value


def test_the_walk_finds_the_issue_work_the_tracker_itself_asks_of_gh():
    tree = ast.parse((SCRIPTS / "tracker" / "github.py").read_text(encoding="utf-8"))

    assert set(ISSUE_WORK) <= set(first_words_to_gh(tree))


def test_no_script_outside_the_tracker_asks_gh_about_an_issue():
    tracker = SCRIPTS / "tracker"
    reached = []
    for script in SCRIPTS.rglob("*.py"):
        if tracker in script.parents:
            continue
        tree = ast.parse(script.read_text(encoding="utf-8"))
        reached += ["{}: gh {}".format(script.relative_to(SCRIPTS).as_posix(), word)
                    for word in first_words_to_gh(tree) if word in ISSUE_WORK]

    assert reached == []
