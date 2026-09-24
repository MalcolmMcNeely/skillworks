#
# The landing script, run against a throwaway repository.

import io
from pathlib import Path

import land_ticket
from conftest import Ran, git, launch, project_suite, write_suite
from suite import SUITE_FILE


# A fixed answer, so a case can tell what the script gathered from what it made up.
CLOSING_COMMENT = "What that ticket set out to do."


def run_land(runner, *args):
    given = [a.as_posix() if isinstance(a, Path) else str(a) for a in args]
    out, err = io.StringIO(), io.StringIO()
    status = land_ticket.main(given, runner, out, err)
    return Ran(status, out.getvalue(), err.getvalue())


# A reason on stderr and a note on stdout are one report, and a case reads it whole.
def report(ran):
    return ran.out + ran.err


def append(path, text):
    with Path(path).open("a", encoding="utf-8", newline="\n") as file:
        file.write(text + "\n")


def main_of(repo):
    return git(repo.origin, "rev-parse", "main").strip()


def head_of(repo):
    return git(repo.work, "rev-parse", "HEAD").strip()


def unmerged(repo):
    said = git(repo.work, "diff", "--name-only", "--diff-filter=U")
    return [name for name in said.split("\n") if name]


# A Suite file, so a case can say whether the suite ran.
def given_a_project(repo):
    write_suite(repo.work, *project_suite())
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "A Suite to check")
    git(repo.work, "push", "--quiet", "origin", "main")


def commit_for_ticket(repo, ticket):
    repo.write_commit(repo.work, "work.txt", "work", "Do the work\n\nTicket: #{}".format(ticket))


def commit_naming_nothing(repo):
    repo.write_commit(repo.work, "work.txt", "work", "Do the work")


def given_the_other_side_changed(repo, theirs):
    repo.write_commit(repo.work, "shared.txt", "start", "A file both sides will change")
    git(repo.work, "push", "--quiet", "origin", "main")
    repo.push_from_elsewhere(
        "shared.txt", "their line",
        "Somebody else got there first\n\nTicket: #{}".format(theirs))


def given_a_conflict(repo, mine, theirs):
    given_the_other_side_changed(repo, theirs)
    repo.write_commit(
        repo.work, "shared.txt", "my line", "Do the work\n\nTicket: #{}".format(mine))


# Two files in one commit, so dropping one still leaves a commit to replay.
def given_a_conflict_beside_other_work(repo, mine, theirs):
    given_the_other_side_changed(repo, theirs)
    append(repo.work / "shared.txt", "my line")
    append(repo.work / "work.txt", "work")
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "Do the work\n\nTicket: #{}".format(mine))


# Two files, so a count of one cannot pass for a measurement.
def given_two_conflicting_files(repo, mine, theirs):
    repo.write_commit(repo.work, "shared.txt", "start", "A file both sides will change")
    repo.write_commit(repo.work, "also.txt", "start", "Another file both sides will change")
    git(repo.work, "push", "--quiet", "origin", "main")

    other = repo.other_checkout()
    append(other / "shared.txt", "their line")
    append(other / "also.txt", "their line")
    git(other, "add", "-A")
    git(other, "commit", "--quiet", "-m",
        "Somebody else got there first\n\nTicket: #{}".format(theirs))
    git(other, "push", "--quiet", "origin", "main")

    append(repo.work / "shared.txt", "my line")
    append(repo.work / "also.txt", "my line")
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "Do the work\n\nTicket: #{}".format(mine))


# Deleted on one side and changed on the other, so the file is unmerged with no marker in it.
def given_a_conflict_with_no_marker(repo, mine, theirs):
    repo.write_commit(repo.work, "shared.txt", "start", "A file one side will delete")
    git(repo.work, "push", "--quiet", "origin", "main")

    other = repo.other_checkout()
    git(other, "rm", "--quiet", "shared.txt")
    git(other, "commit", "--quiet", "-m",
        "Somebody else deleted it\n\nTicket: #{}".format(theirs))
    git(other, "push", "--quiet", "origin", "main")

    repo.write_commit(
        repo.work, "shared.txt", "my line", "Do the work\n\nTicket: #{}".format(mine))


def given_the_suite_passes(runner):
    runner.stub("docker")
    runner.stub("dotnet")
    runner.stub("npm")


def given_the_tracker_answers(runner):
    runner.stub("gh", says=CLOSING_COMMENT)


# A session reaches each conflicting file, so a case says what it does with one.
def stub_session(repo, runner, settle, says=""):
    def resolve():
        for name in unmerged(repo):
            settle(repo.work / name)
    runner.stub("claude", says=says, does=resolve)


def staging(repo, text):
    def settle(path):
        path.write_text(text, encoding="utf-8", newline="")
        git(repo.work, "add", path.as_posix())
    return settle


def adding(repo):
    def settle(path):
        git(repo.work, "add", path.as_posix())
    return settle


def leaving_alone(path):
    return None


def test_a_finished_ticket_reaches_the_remote(repo, runner):
    runner.stub("claude")
    given_the_suite_passes(runner)
    given_a_project(repo)
    commit_for_ticket(repo, 163)
    head = head_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 0
    assert "#163" in report(ran)
    assert main_of(repo) == head
    assert head_of(repo) == head
    assert not runner.started("claude")
    assert not runner.started("dotnet")
    assert not runner.started("npm")


def test_a_plan_names_every_step_with_its_checks_and_lands_nothing(repo, runner):
    base = main_of(repo)

    ran = run_land(runner, "--plan")

    assert ran.status == 0
    for step in ("verify", "fetch", "rebase", "resolve", "suite", "push"):
        assert step in ran.out
    # The driver reads a name, what runs and the checks, so a line short of one says nothing.
    for line in ran.out.splitlines():
        assert len(line.split("\t")) == 3
        assert all(field for field in line.split("\t"))
    assert main_of(repo) == base
    assert runner.calls == []


def test_a_moved_base_is_rebased_and_the_suite_runs_again(repo, runner):
    given_the_suite_passes(runner)
    given_a_project(repo)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    other_side = main_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 0
    assert runner.built("dotnet test Skillworks.slnx")
    assert runner.built("npm test")
    assert main_of(repo) == head_of(repo)
    assert git(repo.work, "rev-parse", "HEAD^").strip() == other_side
    # One parent, so the other side was rebased onto rather than merged in.
    assert len(git(repo.work, "log", "-1", "--format=%P").split()) == 1
    assert git(repo.origin, "show", "main:later.txt").strip() == "later"
    assert git(repo.origin, "show", "main:work.txt").strip() == "work"


def test_a_suite_that_fails_on_the_new_base_is_not_pushed(repo, runner):
    given_the_suite_passes(runner)
    runner.stub("dotnet", status=1)
    given_a_project(repo)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 1
    assert "failed the suite" in report(ran)
    assert main_of(repo) == base


def test_a_suite_that_could_not_start_on_the_new_base_is_not_the_ticket_s_fault(repo, runner):
    given_the_suite_passes(runner)
    runner.stub("docker", says="the daemon is not running", status=1)
    given_a_project(repo)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 1
    assert "Docker" in report(ran)
    assert "failed the suite" not in report(ran)
    assert not runner.started("dotnet")
    assert main_of(repo) == base


def test_a_checkout_with_no_suite_file_is_refused(repo, runner):
    given_the_suite_passes(runner)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 1
    assert "could not start" in report(ran)
    assert SUITE_FILE in report(ran)
    assert main_of(repo) == base


def test_a_ticket_already_on_main_is_refused(repo, runner):
    given_the_suite_passes(runner)
    given_a_project(repo)
    commit_for_ticket(repo, 165)
    git(repo.work, "push", "--quiet", "origin", "main")
    repo.advance_origin("later")
    base = main_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 1
    assert "already on main" in report(ran)
    assert main_of(repo) == base
    assert not runner.started("dotnet")


def test_a_rebase_that_drops_the_ticket_is_refused(repo, runner):
    given_the_suite_passes(runner)
    given_a_project(repo)
    # The other side made the very change this ticket makes, so nothing is left to replay.
    repo.advance_origin("work")
    commit_for_ticket(repo, 165)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 1
    assert "dropped" in report(ran)
    assert main_of(repo) == base
    assert not runner.started("dotnet")


def test_a_commit_that_names_no_ticket_is_refused(repo, runner):
    commit_naming_nothing(repo)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert "Ticket: #163" in report(ran)
    assert main_of(repo) == base


def test_a_first_commit_that_names_no_ticket_is_refused(repo, runner):
    commit_naming_nothing(repo)
    first = git(repo.work, "rev-parse", "--short", "HEAD").strip()
    commit_for_ticket(repo, 163)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert "Ticket: #163" in report(ran)
    # The developer fixes the commit the message names, so the wrong one sends them nowhere.
    assert first in report(ran)
    assert main_of(repo) == base


def test_a_second_commit_that_names_no_ticket_is_refused(repo, runner):
    commit_for_ticket(repo, 163)
    commit_naming_nothing(repo)
    second = git(repo.work, "rev-parse", "--short", "HEAD").strip()
    base = main_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert "Ticket: #163" in report(ran)
    assert second in report(ran)
    assert main_of(repo) == base


def test_every_commit_naming_the_ticket_reaches_the_remote(repo, runner):
    runner.stub("claude")
    given_the_suite_passes(runner)
    given_a_project(repo)
    commit_for_ticket(repo, 163)
    commit_for_ticket(repo, 163)
    head = head_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 0
    assert main_of(repo) == head
    # Two lines of work, so a range that landed only its last commit cannot pass.
    assert git(repo.origin, "show", "main:work.txt").strip() == "work\nwork"
    assert not runner.started("claude")
    assert not runner.started("dotnet")
    assert not runner.started("npm")


def test_a_commit_that_names_another_ticket_is_refused(repo, runner):
    commit_for_ticket(repo, 999)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert "#999" in report(ran)
    assert main_of(repo) == base


def test_a_refused_push_is_tried_three_times_and_no_more(repo, runner):
    commit_for_ticket(repo, 163)
    repo.refuse_pushes()
    base = main_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert repo.push_tries() == 3
    assert "3 times" in report(ran)
    assert main_of(repo) == base


def test_uncommitted_work_is_refused(repo, runner):
    commit_for_ticket(repo, 163)
    (repo.work / "loose.txt").write_text("loose\n", encoding="utf-8", newline="\n")
    base = main_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert "uncommitted" in report(ran)
    assert main_of(repo) == base


def test_a_path_that_holds_no_repository_is_refused(repo, runner):
    base = main_of(repo)

    ran = run_land(runner, repo.root / "nowhere", 163)

    assert ran.status == 1
    assert "not a git worktree" in report(ran)
    assert main_of(repo) == base


def test_arguments_of_the_wrong_shape_print_the_usage(repo, runner):
    base = main_of(repo)

    ran = run_land(runner, repo.work)

    assert ran.status == 64
    assert "usage:" in report(ran)
    assert main_of(repo) == base


def test_a_conflict_is_handed_back_to_the_ticket_s_own_session(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    stub_session(repo, runner, staging(repo, "start\ntheir line\nmy line\n"))
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)
    theirs = git(repo.origin, "rev-parse", "--short", "main").strip()

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 0
    handed = "\n".join(" ".join(call) for call in runner.started("claude"))
    assert "/skillworks:resolve-conflict" in handed
    assert "--resume session-abc" in handed
    assert theirs in handed
    assert "Somebody else got there first" in handed
    # No answer gh gave holds the number, so only the commit message can have carried it.
    assert "#164" in handed
    assert CLOSING_COMMENT in handed
    # Both sides of a hunk count, because the size is what has to be read to settle it.
    assert "conflict #166 files=1 hunks=1 lines=2 outcome=resolved" in report(ran)
    assert main_of(repo) == head_of(repo)
    assert git(repo.origin, "show", "main:shared.txt").strip() == "start\ntheir line\nmy line"
    assert runner.built("dotnet test Skillworks.slnx")


def test_a_refusal_stops_the_run_and_names_the_rule_that_fired(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    # A refusal leaves the conflict where it stands, so this stub touches no file.
    runner.stub("claude", says="REFUSED 1: neither side says which count the tile shows.\n\n"
                               "Mine wanted a count per skill. Theirs wanted a count per session.")
    given_a_project(repo)
    given_two_conflicting_files(repo, 167, 164)
    base = main_of(repo)
    mine = git(repo.work, "rev-parse", "main").strip()

    ran = run_land(runner, repo.work, 167, "session-abc")

    assert ran.status == 1
    assert "refused under rule 1" in report(ran)
    # The developer fixes the cause from the log, so both intentions have to reach it.
    assert "Mine wanted a count per skill." in report(ran)
    assert "Theirs wanted a count per session." in report(ran)
    assert "conflict #167 files=2 hunks=2 lines=4 outcome=refused" in report(ran)
    assert main_of(repo) == base
    assert repo.work.is_dir()
    assert git(repo.work, "rev-parse", "main").strip() == mine
    assert unmerged(repo)


def test_a_refusal_that_staged_everything_still_stops_the_run(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    # Rule 2 fires after the checks fail, by which time the files can already be staged.
    stub_session(repo, runner, staging(repo, "resolved\n"),
                 says="REFUSED 2: the typecheck still fails and I cannot see why.")
    given_a_project(repo)
    given_a_conflict(repo, 167, 164)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 167, "session-abc")

    assert ran.status == 1
    assert "refused under rule 2" in report(ran)
    assert "outcome=refused" in report(ran)
    assert main_of(repo) == base
    assert not runner.started("dotnet")


def test_a_conflict_with_no_marker_in_it_is_still_measured(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    stub_session(repo, runner, adding(repo))
    given_a_project(repo)
    given_a_conflict_with_no_marker(repo, 167, 164)

    ran = run_land(runner, repo.work, 167, "session-abc")

    assert ran.status == 0
    # A file with no marker in it counts none, rather than leaving the count unmade.
    assert "conflict #167 files=1 hunks=0 lines=0 outcome=resolved" in report(ran)


def test_a_leftover_conflict_marker_is_caught(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    stub_session(repo, runner,
                 staging(repo, "<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> them\n"))
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 1
    assert "conflict marker" in report(ran)
    assert "shared.txt" in report(ran)
    assert "conflict #166 files=1 hunks=1 lines=2 outcome=caught" in report(ran)
    assert main_of(repo) == base
    assert not runner.started("dotnet")


def test_a_session_that_resolves_nothing_leaves_the_conflict_standing(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    stub_session(repo, runner, leaving_alone)
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 1
    assert "still conflicting" in report(ran)
    assert "named no rule" in report(ran)
    assert "outcome=refused" in report(ran)
    assert main_of(repo) == base
    assert unmerged(repo)


def test_a_resolution_that_drops_the_ticket_s_change_is_caught(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)

    # During a rebase "ours" is the new base, so this takes the other side wholesale.
    def settle(path):
        git(repo.work, "checkout", "--ours", "--", path.as_posix())
        git(repo.work, "add", path.as_posix())

    stub_session(repo, runner, settle)
    given_a_project(repo)
    given_a_conflict_beside_other_work(repo, 166, 164)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 1
    assert "dropped" in report(ran)
    assert "shared.txt" in report(ran)
    assert main_of(repo) == base


def test_a_conflict_with_no_session_named_is_left_standing(repo, runner):
    given_the_suite_passes(runner)
    runner.stub("claude")
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 166)

    assert ran.status == 1
    assert "rebase --abort" in report(ran)
    assert main_of(repo) == base
    assert not runner.started("claude")


def test_a_ticket_whose_closing_comment_cannot_be_read_is_still_named(repo, runner):
    given_the_suite_passes(runner)
    runner.stub("gh", status=1)
    stub_session(repo, runner, staging(repo, "start\ntheir line\nmy line\n"))
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 0
    handed = "\n".join(" ".join(call) for call in runner.started("claude"))
    assert "#164" in handed
    # A silent tracker is not a ticket with nothing to say, and a refusal turns on which it was.
    assert "would not answer for #164" in handed


def test_a_ticket_closed_with_no_comment_is_still_named(repo, runner):
    given_the_suite_passes(runner)
    runner.stub("gh")
    stub_session(repo, runner, staging(repo, "start\ntheir line\nmy line\n"))
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 0
    handed = "\n".join(" ".join(call) for call in runner.started("claude"))
    assert "#164" in handed
    assert "closed with no comment" in handed


def test_a_marker_staged_behind_a_clean_working_file_is_caught(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)

    # The marker reaches the index and never the working tree, so only the index shows it.
    def settle(path):
        path.write_text("<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> them\n",
                        encoding="utf-8", newline="")
        git(repo.work, "add", path.as_posix())
        path.write_text("clean\n", encoding="utf-8", newline="")

    stub_session(repo, runner, settle)
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 1
    assert "conflict marker" in report(ran)
    assert main_of(repo) == base


def test_a_later_commit_that_conflicts_too_stops_with_its_own_reason(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    # A resolution that keeps neither side leaves the next commit nothing to apply to.
    stub_session(repo, runner, staging(repo, "resolved\n"))
    given_a_project(repo)
    given_the_other_side_changed(repo, 164)
    repo.write_commit(repo.work, "shared.txt", "my line", "Do the first half\n\nTicket: #166")
    repo.write_commit(
        repo.work, "shared.txt", "my second line", "Do the second half\n\nTicket: #166")
    base = main_of(repo)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 1
    assert "a later commit of its own conflicted" in report(ran)
    # Two conflicts were met, so two are recorded, and neither was proved good.
    assert report(ran).count("conflict #166") == 2
    assert main_of(repo) == base


def test_a_conflict_marker_in_a_crlf_file_is_caught(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    # Only the middle marker is left, so the carriage return is what the check must see past.
    stub_session(repo, runner, staging(repo, "mine\r\n=======\r\ntheirs\r\n"))
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)
    base = main_of(repo)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 1
    assert "conflict marker" in report(ran)
    assert main_of(repo) == base


def test_the_land_ticket_command_starts_the_landing_script_in_the_plugin(repo):
    ran = launch("land-ticket", where=repo.work)

    assert ran.status == 64
    assert ran.err.startswith("usage: land-ticket <worktree> <ticket-number> [session-id]\n")
