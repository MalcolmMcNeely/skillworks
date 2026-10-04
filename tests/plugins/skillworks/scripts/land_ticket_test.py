#
# The landing script, run against a throwaway repository.

import ast
import io
import json
import re
import subprocess
import sys
import threading
import tomllib
from pathlib import Path

import pytest

import land_ticket
from conftest import (PLUGIN, SCRIPTS, Ran, RecordingRunner, Repo, check, git, launch, no_wait,
                      project_suite, write_loop, write_suite)
from steering.target_branch import LOOP_FILE
from suite import SUITE_FILE, Suite


# Committed, because a landing turns down a checkout with anything left uncommitted in it.
def landing_repo(tmp_path, target):
    made = Repo(tmp_path, target=target)
    write_loop(made.work, target)
    git(made.work, "add", "-A")
    git(made.work, "commit", "--quiet", "-m", "The loop's settings")
    git(made.work, "push", "--quiet", "origin", target)
    return made


@pytest.fixture
def repo(tmp_path):
    return landing_repo(tmp_path, "main")


@pytest.fixture
def master(tmp_path):
    return landing_repo(tmp_path, "master")


# A fixed answer, so a case can tell what the script gathered from what it made up.
CLOSING_NOTE = "What that ticket set out to do."

# git words a lost race one way when origin/main is stale, and the other when it is not.
LOST_RACE_STALE = (
    "To origin\n"
    " ! [rejected]        HEAD -> main (fetch first)\n"
    "error: failed to push some refs to 'origin'")
LOST_RACE = (
    "To origin\n"
    " ! [rejected]        HEAD -> main (non-fast-forward)\n"
    "error: failed to push some refs to 'origin'")


def run_land(runner, *args):
    given = [a.as_posix() if isinstance(a, Path) else str(a) for a in args]
    out, err = io.StringIO(), io.StringIO()
    status = land_ticket.main(given, runner, out, err, no_wait)
    return Ran(status, out.getvalue(), err.getvalue())


WAITS = "waits for the Turn"
LOST = "lost a race to main"

# Another loop is another process, and the OS hands the Turn to one process at a time.
OTHER_LOOP = """
import sys
sys.path.insert(0, sys.argv[1])
from land_ticket import Turn
from runner import Subprocess

def busy(holder):
    print("busy", flush=True)
    sys.exit(0)

turn = Turn.of(Subprocess(), sys.argv[2], sys.argv[3])
turn.take(busy if sys.argv[4] in ("try", "grab") else lambda holder: None)
print("held", flush=True)
if sys.argv[4] in ("hold", "grab"):
    sys.stdin.read()
turn.let_go()
"""


class OtherLoop:
    def __init__(self, repo, holder, how):
        self.process = subprocess.Popen(
            [sys.executable, "-c", OTHER_LOOP, str(SCRIPTS), repo.work.as_posix(), holder, how],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding="utf-8")
        self.said = self.process.stdout.readline().strip()

    def let_go(self):
        self.process.stdin.close()
        self.process.wait()


@pytest.fixture
def other_loops():
    started = []

    def start(repo, holder="spec #200 ticket #199", how="hold"):
        loop = OtherLoop(repo, holder, how)
        started.append(loop)
        return loop

    yield start
    for loop in started:
        if loop.process.poll() is None:
            loop.process.kill()
            loop.process.wait()


def the_turn_is_free(repo, other_loops):
    return other_loops(repo, how="try").said == "held"


# Each line is handed on as it is written, so a case can act at the moment a landing speaks.
class Heard(io.StringIO):
    def __init__(self, mark, cues=None):
        super().__init__()
        self.mark = mark
        self.cues = cues or {}
        self.seen = threading.Event()

    def write(self, said):
        written = super().write(said)
        for cue, then in self.cues.items():
            if cue in said:
                then()
        if self.mark in said:
            self.seen.set()
        return written


# The landing blocks on the Turn, so it runs beside the case that holds it.
class Beside:
    def __init__(self, runner, out, *args, target=None):
        given = [a.as_posix() if isinstance(a, Path) else str(a) for a in args]
        self.out = out
        self.err = io.StringIO()
        self.status = None
        self.target = target
        self.thread = threading.Thread(target=self.land, args=(runner, given), daemon=True)
        self.thread.start()

    def land(self, runner, given):
        try:
            self.status = land_ticket.main(given, runner, self.out, self.err, no_wait,
                                           target=self.target)
        finally:
            # A landing that ended without the line must fail the case, not hang it.
            self.out.seen.set()

    def heard(self):
        self.out.seen.wait()
        return self.out.getvalue()

    def ended(self):
        self.thread.join()
        return Ran(self.status, self.out.getvalue(), self.err.getvalue())


# A reason on stderr and a note on stdout are one report, and a case reads it whole.
def report(ran):
    return ran.out + ran.err


def append(path, text):
    with Path(path).open("a", encoding="utf-8", newline="\n") as file:
        file.write(text + "\n")


def target_of(repo):
    return git(repo.origin, "rev-parse", repo.target).strip()


def head_of(repo):
    return git(repo.work, "rev-parse", "HEAD").strip()


def unmerged(repo):
    said = git(repo.work, "diff", "--name-only", "--diff-filter=U")
    return [name for name in said.split("\n") if name]


# A Suite file, so a case can say whether the suite ran.
def given_a_project(repo, runs=None):
    write_suite(repo.work, *project_suite(), runs=runs)
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "A Suite to check")
    git(repo.work, "push", "--quiet", "origin", repo.target)


def commit_for_ticket(repo, ticket):
    repo.write_commit(repo.work, "work.txt", "work", "Do the work\n\nTicket: #{}".format(ticket))


def commit_naming_nothing(repo):
    repo.write_commit(repo.work, "work.txt", "work", "Do the work")


def given_the_other_side_changed(repo, theirs):
    repo.write_commit(repo.work, "shared.txt", "start", "A file both sides will change")
    git(repo.work, "push", "--quiet", "origin", repo.target)
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
    git(repo.work, "push", "--quiet", "origin", repo.target)

    other = repo.other_checkout()
    append(other / "shared.txt", "their line")
    append(other / "also.txt", "their line")
    git(other, "add", "-A")
    git(other, "commit", "--quiet", "-m",
        "Somebody else got there first\n\nTicket: #{}".format(theirs))
    git(other, "push", "--quiet", "origin", repo.target)

    append(repo.work / "shared.txt", "my line")
    append(repo.work / "also.txt", "my line")
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "Do the work\n\nTicket: #{}".format(mine))


# Deleted on one side and changed on the other, so the file is unmerged with no marker in it.
def given_a_conflict_with_no_marker(repo, mine, theirs):
    repo.write_commit(repo.work, "shared.txt", "start", "A file one side will delete")
    git(repo.work, "push", "--quiet", "origin", repo.target)

    other = repo.other_checkout()
    git(other, "rm", "--quiet", "shared.txt")
    git(other, "commit", "--quiet", "-m",
        "Somebody else deleted it\n\nTicket: #{}".format(theirs))
    git(other, "push", "--quiet", "origin", repo.target)

    repo.write_commit(
        repo.work, "shared.txt", "my line", "Do the work\n\nTicket: #{}".format(mine))


def given_the_suite_passes(runner):
    runner.stub("docker")
    runner.stub("dotnet")
    runner.stub("npm")


def given_the_tracker_answers(runner):
    runner.stub("gh", says=CLOSING_NOTE)


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
    assert target_of(repo) == head
    assert head_of(repo) == head
    assert not runner.started("claude")
    assert not runner.started("dotnet")
    assert not runner.started("npm")


def test_a_plan_names_every_step_with_its_checks_and_lands_nothing(repo, runner):
    base = target_of(repo)

    ran = run_land(runner, "--plan")

    assert ran.status == 0
    for step in ("verify", "fetch", "rebase", "resolve", "suite", "push", "tell"):
        assert step in ran.out
    # The driver reads a name, what runs and the checks, so a line short of one says nothing.
    for line in ran.out.splitlines():
        assert len(line.split("\t")) == 3
        assert all(field for field in line.split("\t"))
    # A lost race is tried again without end, so a count would tell the reader a cap that is gone.
    push = [line for line in ran.out.splitlines() if line.startswith("push\t")]
    assert push == ["push\tgit push origin HEAD:<target>, again after each lost race\tpushed"]
    assert target_of(repo) == base
    assert runner.calls == []


def test_a_moved_base_is_rebased_and_the_suite_runs_again(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    given_a_project(repo)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    other_side = target_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 0
    assert runner.built("dotnet test Skillworks.slnx")
    assert runner.built("npm test")
    assert target_of(repo) == head_of(repo)
    assert git(repo.work, "rev-parse", "HEAD^").strip() == other_side
    # One parent, so the other side was rebased onto rather than merged in.
    assert len(git(repo.work, "log", "-1", "--format=%P").split()) == 1
    assert git(repo.origin, "show", "main:later.txt").strip() == "later"
    assert git(repo.origin, "show", "main:work.txt").strip() == "work"


def comments_on(runner, ticket):
    return [call for call in runner.started("gh")
            if call[1:4] == ["issue", "comment", str(ticket)]]


def comment_body(call):
    return call[call.index("--body") + 1]


def short(repo, commit):
    return git(repo.work, "rev-parse", "--short", commit).strip()


def test_a_ticket_rebased_at_land_is_told_the_commit_that_reached_main(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    given_a_project(repo)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    before = short(repo, "HEAD")

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 0, report(ran)
    landed = short(repo, target_of(repo))
    assert landed != before
    [comment] = comments_on(runner, 165)
    assert "{} replaces {}".format(landed, before) in comment_body(comment)


def test_a_ticket_that_lands_with_no_rebase_gets_no_extra_comment(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    given_a_project(repo)
    commit_for_ticket(repo, 163)
    closed_on = short(repo, "HEAD")

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 0, report(ran)
    assert comments_on(runner, 163) == []
    # The finishing step named HEAD when it closed the ticket, and HEAD is what reached main.
    assert short(repo, target_of(repo)) == closed_on


def test_a_ticket_of_several_commits_rebased_at_land_names_each_new_one(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    given_a_project(repo)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    repo.write_commit(repo.work, "more.txt", "more", "Do more\n\nTicket: #165")
    first, second = short(repo, "HEAD~1"), short(repo, "HEAD")

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 0, report(ran)
    [comment] = comments_on(runner, 165)
    body = comment_body(comment)
    assert "{} replaces {}".format(short(repo, target_of(repo) + "~1"), first) in body
    assert "{} replaces {}".format(short(repo, target_of(repo)), second) in body


def test_a_tracker_that_will_not_take_the_comment_does_not_undo_the_landing(repo, runner):
    given_the_suite_passes(runner)
    runner.stub("gh", status=1)
    given_a_project(repo)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    before = short(repo, "HEAD")

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 0, report(ran)
    landed = short(repo, target_of(repo))
    assert "note  #165 landed, and the tracker would not take the comment" in ran.out
    assert "{} replaces {}".format(landed, before) in ran.out


# The other side changed only a file both checks ignore, so the rebased tree is one they passed on.
def test_a_landing_whose_checks_are_all_proved_runs_nothing(repo, runner):
    write_suite(repo.work, check("dotnet", "test", "Skillworks.slnx", ignores=["later.txt"]),
                check("npm", "test", ignores=["later.txt"]))
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "A Suite to check")
    git(repo.work, "push", "--quiet", "origin", repo.target)
    commit_for_ticket(repo, 165)
    earlier = RecordingRunner()
    given_the_suite_passes(earlier)
    assert Suite(earlier, repo.work).run().passed
    repo.advance_origin("later")
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 0, report(ran)
    assert git(repo.origin, "show", "main:later.txt").strip() == "later"
    assert not runner.started("dotnet")
    assert not runner.started("npm")


def test_a_landed_commit_keeps_its_session_trailers_after_the_rebase(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    given_a_project(repo)
    repo.advance_origin("later")
    repo.write_commit(
        repo.work, "work.txt", "work",
        "Do the work\n\nTicket: #165\n"
        "Skillworks-Session: first-session\nSkillworks-Session: second-session")
    before = head_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 0
    assert target_of(repo) != before
    assert git(repo.origin, "log", "-1", "--format=%(trailers:key=Skillworks-Session,valueonly)",
               "main").split() == ["first-session", "second-session"]


def test_a_suite_that_fails_on_the_new_base_is_not_pushed(repo, runner):
    given_the_suite_passes(runner)
    runner.stub("dotnet", status=1)
    given_a_project(repo)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 1
    assert "failed the suite" in report(ran)
    assert target_of(repo) == base


def test_with_no_setting_a_suite_red_once_on_the_new_base_is_not_pushed(repo, runner):
    given_the_suite_passes(runner)
    runner.refuse("dotnet test", "a test failed", times=1)
    given_a_project(repo)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 1
    assert len(runner.started("dotnet")) == 1
    assert target_of(repo) == base


def test_a_suite_red_then_green_on_the_new_base_lands_when_a_second_run_is_asked_for(
        repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    runner.refuse("dotnet test", "a test failed", times=1)
    given_a_project(repo, runs=2)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 0, report(ran)
    assert len(runner.started("dotnet")) == 2
    assert target_of(repo) == head_of(repo)


def test_a_landing_run_by_hand_names_a_flake_on_the_new_base(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    runner.refuse("dotnet test", "a test failed", times=1)
    given_a_project(repo, runs=2)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 0, report(ran)
    assert ("note  #165 met a Flake on the new base: dotnet test Skillworks.slnx went red and "
            "then passed") in ran.out


def test_a_landing_hands_each_flake_to_the_driver_that_asked_for_them(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    runner.refuse("dotnet test", "a test failed", times=1)
    given_a_project(repo, runs=2)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    flakes = []

    status = land_ticket.main([repo.work.as_posix(), "165"], runner, io.StringIO(), io.StringIO(),
                              no_wait, flaked=flakes.append)

    assert status == 0
    assert [flake.check for flake in flakes] == ["dotnet test Skillworks.slnx"]
    assert "a test failed" in flakes[0].said


def test_a_suite_red_twice_on_the_new_base_is_not_pushed_when_a_second_run_is_asked_for(
        repo, runner):
    given_the_suite_passes(runner)
    runner.stub("dotnet", says="a test failed", status=1)
    given_a_project(repo, runs=2)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 1
    assert len(runner.started("dotnet")) == 2
    assert target_of(repo) == base


def test_a_suite_that_could_not_start_on_the_new_base_is_not_the_ticket_s_fault(repo, runner):
    given_the_suite_passes(runner)
    runner.stub("docker", says="the daemon is not running", status=1)
    given_a_project(repo)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 1
    assert "Docker" in report(ran)
    assert "failed the suite" not in report(ran)
    assert not runner.started("dotnet")
    assert target_of(repo) == base


def test_a_checkout_with_no_suite_file_is_refused(repo, runner):
    given_the_suite_passes(runner)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 1
    assert "could not start" in report(ran)
    assert SUITE_FILE in report(ran)
    assert target_of(repo) == base


def test_a_ticket_already_on_main_is_refused(repo, runner):
    given_the_suite_passes(runner)
    given_a_project(repo)
    commit_for_ticket(repo, 165)
    git(repo.work, "push", "--quiet", "origin", repo.target)
    repo.advance_origin("later")
    base = target_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 1
    assert "already on main" in report(ran)
    assert target_of(repo) == base
    assert not runner.started("dotnet")


def test_a_ticket_the_new_base_already_holds_is_refused(repo, runner):
    given_the_suite_passes(runner)
    given_a_project(repo)
    # The other side made the very change this ticket makes, so nothing is left to replay.
    repo.advance_origin("work")
    commit_for_ticket(repo, 165)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert ran.status == 1
    assert target_of(repo) == base
    assert not runner.started("dotnet")


def test_a_commit_the_new_base_already_holds_stops_and_says_nothing_was_lost(repo, runner):
    given_the_suite_passes(runner)
    given_a_project(repo)
    repo.advance_origin("work")
    commit_for_ticket(repo, 165)

    ran = run_land(runner, repo.work, 165)

    said = report(ran)
    assert ("nothing was lost" in said and "reset" not in said
            and "ORIG_HEAD" not in said and "kept" not in said)


def test_a_commit_the_new_base_already_holds_with_a_git_that_turns_the_replay_down_names_git_2_38(
        repo, runner):
    given_the_suite_passes(runner)
    given_a_project(repo)
    repo.advance_origin("work")
    commit_for_ticket(repo, 165)
    # A second commit still changes the file, so the file survives without the replay.
    repo.write_commit(repo.work, "work.txt", "more", "Do more work\n\nTicket: #165")
    runner.refuse("merge-tree", "error: unknown option `write-tree'")
    base = target_of(repo)

    ran = run_land(runner, repo.work, 165)

    assert (ran.status, target_of(repo), "2.38" in report(ran)) == (1, base, True)


def test_a_commit_that_names_no_ticket_is_refused(repo, runner):
    commit_naming_nothing(repo)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert "Ticket: #163" in report(ran)
    assert target_of(repo) == base


def test_a_commit_that_names_another_ticket_is_refused(repo, runner):
    commit_for_ticket(repo, 164)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert "names ticket #164, and this is #163" in report(ran)
    assert target_of(repo) == base


def test_a_first_commit_that_names_no_ticket_is_refused(repo, runner):
    commit_naming_nothing(repo)
    first = git(repo.work, "rev-parse", "--short", "HEAD").strip()
    commit_for_ticket(repo, 163)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert "Ticket: #163" in report(ran)
    # The developer fixes the commit the message names, so the wrong one sends them nowhere.
    assert first in report(ran)
    assert target_of(repo) == base


def test_a_second_commit_that_names_no_ticket_is_refused(repo, runner):
    commit_for_ticket(repo, 163)
    commit_naming_nothing(repo)
    second = git(repo.work, "rev-parse", "--short", "HEAD").strip()
    base = target_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert "Ticket: #163" in report(ran)
    assert second in report(ran)
    assert target_of(repo) == base


def test_every_commit_naming_the_ticket_reaches_the_remote(repo, runner):
    runner.stub("claude")
    given_the_suite_passes(runner)
    given_a_project(repo)
    commit_for_ticket(repo, 163)
    commit_for_ticket(repo, 163)
    head = head_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 0
    assert target_of(repo) == head
    # Two lines of work, so a range that landed only its last commit cannot pass.
    assert git(repo.origin, "show", "main:work.txt").strip() == "work\nwork"
    assert not runner.started("claude")
    assert not runner.started("dotnet")
    assert not runner.started("npm")


def test_a_commit_that_names_another_ticket_is_refused(repo, runner):
    commit_for_ticket(repo, 999)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert "#999" in report(ran)
    assert target_of(repo) == base


def test_a_push_that_loses_the_race_again_and_again_is_tried_until_it_lands(repo, runner):
    commit_for_ticket(repo, 163)
    head = head_of(repo)
    runner.refuse("push --quiet origin HEAD:main", LOST_RACE, times=3)
    runner.refuse("push --quiet origin HEAD:main", LOST_RACE_STALE, times=2)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 0
    assert len(runner.built("push --quiet origin HEAD:main")) == 6
    assert "landed on main as {} in 6 tries".format(head[:7]) in report(ran)
    assert target_of(repo) == head


def test_a_push_the_remote_turns_down_stops_on_the_first_try(repo, runner):
    commit_for_ticket(repo, 163)
    repo.refuse_pushes()
    base = target_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert repo.push_tries() == 1
    assert "pre-receive hook declined" in report(ran)
    assert target_of(repo) == base


def test_a_landing_that_lost_a_race_waits_for_the_turn_and_lands_once_it_is_let_go(
        repo, runner, other_loops):
    commit_for_ticket(repo, 163)
    head = head_of(repo)
    base = target_of(repo)
    runner.refuse("push --quiet origin HEAD:main", LOST_RACE, times=1)
    held = []
    # Only grabbed, never waited for, so a landing that still holds the Turn fails the case, not hangs it.
    out = Heard(WAITS, {LOST: lambda: held.append(other_loops(repo, how="grab"))})

    landing = Beside(runner, out, repo.work, 163)
    heard = landing.heard()

    assert held[0].said == "held"
    assert "#163 waits for the Turn, which spec #200 ticket #199 holds" in heard
    assert target_of(repo) == base

    held[0].let_go()
    ran = landing.ended()

    assert ran.status == 0, report(ran)
    assert "landed on main as {} in 2 tries, holding the Turn from fetch to push".format(
        head[:7]) in report(ran)
    assert target_of(repo) == head


def test_a_finished_ticket_lands_on_a_target_branch_named_master_and_on_no_other(master, runner):
    commit_for_ticket(master, 163)
    head = head_of(master)

    ran = run_land(runner, master.work, 163)

    assert ran.status == 0, report(ran)
    assert "landed on master as {}".format(head[:7]) in report(ran)
    assert target_of(master) == head
    assert git(master.origin, "for-each-ref", "--format=%(refname)").split() == [
        "refs/heads/master"]


def test_a_ticket_already_on_master_is_refused_by_its_name(master, runner):
    commit_for_ticket(master, 165)
    git(master.work, "push", "--quiet", "origin", "master")
    base = target_of(master)

    ran = run_land(runner, master.work, 165)

    assert ran.status == 1
    assert "already on master" in report(ran)
    assert target_of(master) == base


def test_a_moved_master_is_rebased_onto_and_the_ticket_lands_on_top_of_it(master, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    given_a_project(master)
    master.advance_origin("later")
    commit_for_ticket(master, 165)
    other_side = target_of(master)

    ran = run_land(runner, master.work, 165)

    assert ran.status == 0, report(ran)
    assert target_of(master) == head_of(master)
    assert git(master.work, "rev-parse", "HEAD^").strip() == other_side
    assert git(master.origin, "show", "master:work.txt").strip() == "work"


def test_a_conflict_on_master_is_handed_over_naming_master(master, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    stub_session(master, runner, staging(master, "start\ntheir line\nmy line\n"))
    given_a_project(master)
    given_a_conflict(master, 166, 164)

    ran = run_land(runner, master.work, 166, "session-abc")

    assert ran.status == 0, report(ran)
    handed = "\n".join(" ".join(call) for call in runner.started("claude"))
    assert "rebased onto the newest origin/master" in handed
    assert "These landed on master" in handed
    assert git(master.origin, "show", "master:shared.txt").strip() == "start\ntheir line\nmy line"


def test_a_conflict_on_master_with_no_session_named_is_reported_naming_master(master, runner):
    given_the_suite_passes(runner)
    given_a_project(master)
    given_a_conflict(master, 166, 164)
    base = target_of(master)

    ran = run_land(runner, master.work, 166)

    assert ran.status == 1
    assert "what landed on master" in report(ran)
    assert target_of(master) == base


def test_a_landing_on_master_that_lost_a_race_waits_for_the_turn_and_then_lands_on_master(
        master, runner, other_loops):
    commit_for_ticket(master, 163)
    head = head_of(master)
    base = target_of(master)
    runner.refuse("push --quiet origin HEAD:master", LOST_RACE, times=1)
    held = []
    out = Heard(WAITS, {"lost a race to master": lambda: held.append(
        other_loops(master, how="grab"))})

    landing = Beside(runner, out, master.work, 163)
    heard = landing.heard()

    assert held[0].said == "held"
    assert "#163 waits for the Turn, which spec #200 ticket #199 holds" in heard
    assert target_of(master) == base

    held[0].let_go()
    ran = landing.ended()

    assert ran.status == 0, report(ran)
    assert "landed on master as {} in 2 tries".format(head[:7]) in report(ran)
    assert target_of(master) == head


SPEC_BRANCH = "spec/target-branch"


# The checkout says spec, and only the driver has read the spec, so the branch is handed in.
@pytest.fixture
def spec_mode(tmp_path):
    made = landing_repo(tmp_path, "main")
    write_loop(made.work, "spec")
    git(made.work, "commit", "--quiet", "-am", "The loop reviews each spec as one pull request")
    git(made.work, "push", "--quiet", "origin", "main:" + SPEC_BRANCH)
    git(made.work, "fetch", "--quiet", "origin")
    git(made.work, "checkout", "--quiet", "-B", SPEC_BRANCH, "origin/" + SPEC_BRANCH)
    return made


def spec_branch_of(repo):
    return git(repo.origin, "rev-parse", SPEC_BRANCH).strip()


def test_in_spec_mode_a_landing_that_lost_a_race_waits_for_the_turn_and_lands_on_the_spec_branch(
        spec_mode, runner, other_loops):
    commit_for_ticket(spec_mode, 163)
    head = head_of(spec_mode)
    base = spec_branch_of(spec_mode)
    main = git(spec_mode.origin, "rev-parse", "main").strip()
    runner.refuse("push --quiet origin HEAD:" + SPEC_BRANCH, LOST_RACE, times=1)
    held = []
    out = Heard(WAITS, {"lost a race to " + SPEC_BRANCH: lambda: held.append(
        other_loops(spec_mode, how="grab"))})

    landing = Beside(runner, out, spec_mode.work, 163, target=SPEC_BRANCH)
    heard = landing.heard()

    assert held[0].said == "held"
    assert "#163 waits for the Turn, which spec #200 ticket #199 holds" in heard
    assert spec_branch_of(spec_mode) == base

    held[0].let_go()
    ran = landing.ended()

    assert ran.status == 0, report(ran)
    assert "landed on {} as {} in 2 tries".format(SPEC_BRANCH, head[:7]) in report(ran)
    assert spec_branch_of(spec_mode) == head
    assert git(spec_mode.origin, "rev-parse", "main").strip() == main


SPEC_BODY = "## Problem Statement\n\nWords.\n\n## Branch\n\n`{}`\n".format(SPEC_BRANCH)


# A person landing after an early stop has only the spec's number, so the tracker is asked.
def test_by_hand_in_spec_mode_a_ticket_given_its_spec_lands_on_the_branch_the_spec_names(
        spec_mode, runner):
    runner.stub("gh", says=SPEC_BODY)
    commit_for_ticket(spec_mode, 163)
    head = head_of(spec_mode)
    main = git(spec_mode.origin, "rev-parse", "main").strip()

    ran = run_land(runner, spec_mode.work, 163, "--spec", 282)

    assert ran.status == 0, report(ran)
    assert "landed on " + SPEC_BRANCH in report(ran)
    assert spec_branch_of(spec_mode) == head
    assert git(spec_mode.origin, "rev-parse", "main").strip() == main


def test_by_hand_in_spec_mode_a_ticket_given_its_spec_and_a_session_lands(spec_mode, runner):
    runner.stub("gh", says=SPEC_BODY)
    commit_for_ticket(spec_mode, 163)
    head = head_of(spec_mode)

    ran = run_land(runner, spec_mode.work, 163, "session-abc", "--spec", 282)

    assert ran.status == 0, report(ran)
    assert spec_branch_of(spec_mode) == head


def test_by_hand_in_spec_mode_a_ticket_with_no_spec_stops_and_says_how_to_name_it(
        spec_mode, runner):
    commit_for_ticket(spec_mode, 163)
    base = spec_branch_of(spec_mode)

    ran = run_land(runner, spec_mode.work, 163)

    assert ran.status == 1
    assert "--spec <spec-number>" in report(ran)
    assert spec_branch_of(spec_mode) == base
    assert not runner.started("gh")


def test_by_hand_a_branch_name_lands_with_no_spec_and_asks_the_tracker_nothing(master, runner):
    commit_for_ticket(master, 163)
    head = head_of(master)

    ran = run_land(runner, master.work, 163)

    assert ran.status == 0, report(ran)
    assert target_of(master) == head
    assert not runner.started("gh")


def test_a_spec_that_is_not_a_number_prints_the_usage(repo, runner):
    ran = run_land(runner, repo.work, 163, "--spec", "next")

    assert ran.status == 64
    assert "--spec <spec-number>" in report(ran)


def test_a_checkout_with_no_loop_file_is_refused_and_told_how_to_write_one(repo, runner):
    git(repo.work, "rm", "--quiet", LOOP_FILE)
    git(repo.work, "commit", "--quiet", "-m", "No settings\n\nTicket: #163")
    base = target_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert "seed-steering" in report(ran)
    assert target_of(repo) == base


def test_a_landing_that_has_not_lost_runs_its_suite_and_then_waits_at_the_push(
        repo, runner, other_loops):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    given_a_project(repo)
    repo.advance_origin("later")
    commit_for_ticket(repo, 165)
    base = target_of(repo)
    other = other_loops(repo)

    landing = Beside(runner, Heard(WAITS), repo.work, 165)
    heard = landing.heard()

    assert "#165 waits for the Turn, which spec #200 ticket #199 holds" in heard
    assert runner.built("dotnet test Skillworks.slnx")
    assert heard.index("passed the suite on the new base") < heard.index(WAITS)
    assert target_of(repo) == base

    other.let_go()
    ran = landing.ended()

    assert ran.status == 0, report(ran)
    assert "in 1 try, holding the Turn for its push" in report(ran)
    assert target_of(repo) == head_of(repo)


def test_the_turn_is_let_go_when_a_landing_that_lost_a_race_lands(repo, runner, other_loops):
    commit_for_ticket(repo, 163)
    runner.refuse("push --quiet origin HEAD:main", LOST_RACE, times=2)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 0, report(ran)
    assert the_turn_is_free(repo, other_loops)


def test_the_turn_is_let_go_when_a_landing_that_lost_a_race_stops_on_a_red_suite(
        repo, runner, other_loops):
    given_the_suite_passes(runner)
    runner.stub("dotnet", status=1)
    given_a_project(repo)
    commit_for_ticket(repo, 165)
    base = target_of(repo)
    runner.refuse("push --quiet origin HEAD:main", LOST_RACE, times=1)
    # The race is lost for real, so the next try has a moved base to run the suite on.
    out = Heard(WAITS, {LOST: lambda: repo.advance_origin("later")})

    ran = Beside(runner, out, repo.work, 165).ended()

    assert ran.status == 1
    assert "failed the suite" in report(ran)
    assert "#165 lost a race to main, so it takes the Turn" in report(ran)
    assert git(repo.origin, "rev-parse", "main~1").strip() == base
    assert the_turn_is_free(repo, other_loops)


def test_the_turn_is_let_go_when_a_push_the_remote_turns_down_stops(repo, runner, other_loops):
    commit_for_ticket(repo, 163)
    repo.refuse_pushes()

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert the_turn_is_free(repo, other_loops)


def test_uncommitted_work_is_refused(repo, runner):
    commit_for_ticket(repo, 163)
    (repo.work / "loose.txt").write_text("loose\n", encoding="utf-8", newline="\n")
    base = target_of(repo)

    ran = run_land(runner, repo.work, 163)

    assert ran.status == 1
    assert "uncommitted" in report(ran)
    assert target_of(repo) == base


def test_a_path_that_holds_no_repository_is_refused(repo, runner):
    base = target_of(repo)

    ran = run_land(runner, repo.root / "nowhere", 163)

    assert ran.status == 1
    assert "not a git worktree" in report(ran)
    assert target_of(repo) == base


def test_arguments_of_the_wrong_shape_print_the_usage(repo, runner):
    base = target_of(repo)

    ran = run_land(runner, repo.work)

    assert ran.status == 64
    assert "usage:" in report(ran)
    assert target_of(repo) == base


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
    assert CLOSING_NOTE in handed
    # Both sides of a hunk count, because the size is what has to be read to settle it.
    assert "conflict #166 files=1 hunks=1 lines=2 outcome=resolved" in report(ran)
    assert target_of(repo) == head_of(repo)
    assert git(repo.origin, "show", "main:shared.txt").strip() == "start\ntheir line\nmy line"
    assert runner.built("dotnet test Skillworks.slnx")


def heading_the_resolve_skill_looks_for():
    skill = (PLUGIN / "skills" / "resolve-conflict" / "SKILL.md").read_text(encoding="utf-8")
    [heading] = set(re.findall(r"`(## [^`]+)`", skill))
    return heading


# The skill stops a Session that was handed no such heading, so a renamed one would stop every resolve.
def test_the_other_side_is_handed_over_under_the_heading_the_skill_looks_for(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    stub_session(repo, runner, staging(repo, "start\ntheir line\nmy line\n"))
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)

    run_land(runner, repo.work, 166, "session-abc")

    [resolving] = runner.started("claude")
    assert heading_the_resolve_skill_looks_for() in resolving[resolving.index("-p") + 1].split("\n")


def test_the_resolving_session_gets_the_environment_every_driver_session_gets(
        repo, runner, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "parent-session")
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "team=studio")
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    stub_session(repo, runner, staging(repo, "start\ntheir line\nmy line\n"))
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 0
    resolving = [call for call in runner.made if call.args[0] == "claude"]
    assert len(resolving) == 1
    changes = resolving[0].env
    assert "CLAUDECODE" in changes and changes["CLAUDECODE"] is None
    assert changes.get("BASH_DEFAULT_TIMEOUT_MS") == "2700000"
    assert changes.get("BASH_MAX_TIMEOUT_MS") == "2700000"
    assert "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS" not in changes
    assert changes.get("OTEL_RESOURCE_ATTRIBUTES") == (
        "team=studio,skillworks.parent.session.id=parent-session")


def test_the_resolving_session_is_handed_the_trailer_of_the_ticket_it_lands(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    stub_session(repo, runner, staging(repo, "start\ntheir line\nmy line\n"))
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 0
    resolving = [call for call in runner.made if call.args[0] == "claude"]
    # The Plugin's hook reads this name, so it is written out here and not imported.
    assert [call.env.get("SKILLWORKS_TICKET") for call in resolving] == ["#166"]


def test_a_refusal_stops_the_run_and_names_the_rule_that_fired(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    # A refusal under rule 1 leaves the conflict where it stands, so this stub touches no file.
    runner.stub("claude", says="REFUSED 1: neither side says which count the tile shows.\n\n"
                               "Mine wanted a count per skill. Theirs wanted a count per session.")
    given_a_project(repo)
    given_two_conflicting_files(repo, 167, 164)
    base = target_of(repo)
    mine = git(repo.work, "rev-parse", "main").strip()

    ran = run_land(runner, repo.work, 167, "session-abc")

    assert ran.status == 1
    assert "refused under rule 1" in report(ran)
    # The developer fixes the cause from the log, so both intentions have to reach it.
    assert "Mine wanted a count per skill." in report(ran)
    assert "Theirs wanted a count per session." in report(ran)
    assert "conflict #167 files=2 hunks=2 lines=4 outcome=refused" in report(ran)
    assert target_of(repo) == base
    assert repo.work.is_dir()
    assert git(repo.work, "rev-parse", "main").strip() == mine
    assert unmerged(repo)


def test_a_refusal_in_the_result_of_a_session_that_answers_in_json_names_its_rule(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    runner.stub("claude", says=json.dumps(
        {"session_id": "session-abc", "result": "REFUSED 1: neither side says which count."}))
    given_a_project(repo)
    given_two_conflicting_files(repo, 167, 164)

    ran = run_land(runner, repo.work, 167, "session-abc")

    assert "refused under rule 1" in report(ran)


def test_a_refusal_that_staged_everything_still_stops_the_run(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    # Rule 2 fires after the checks fail, by which time the files can already be staged.
    stub_session(repo, runner, staging(repo, "resolved\n"),
                 says="REFUSED 2: the typecheck still fails and I cannot see why.")
    given_a_project(repo)
    given_a_conflict(repo, 167, 164)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 167, "session-abc")

    assert ran.status == 1
    assert "refused under rule 2" in report(ran)
    assert "outcome=refused" in report(ran)
    assert target_of(repo) == base
    assert not runner.started("dotnet")


def test_a_refusal_below_the_first_line_of_the_answer_still_stops_the_run(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    stub_session(repo, runner, staging(repo, "resolved\n"),
                 says="The file is staged.\nREFUSED 2: the typecheck still fails.")
    given_a_project(repo)
    given_a_conflict(repo, 167, 164)

    ran = run_land(runner, repo.work, 167, "session-abc")

    assert "refused under rule 2" in report(ran)


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
    base = target_of(repo)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 1
    assert "conflict marker" in report(ran)
    assert "shared.txt" in report(ran)
    assert "conflict #166 files=1 hunks=1 lines=2 outcome=caught" in report(ran)
    assert target_of(repo) == base
    assert not runner.started("dotnet")


def test_a_session_that_resolves_nothing_leaves_the_conflict_standing(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    stub_session(repo, runner, leaving_alone)
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 1
    assert "still conflicting" in report(ran)
    assert "named no rule" in report(ran)
    assert "outcome=refused" in report(ran)
    assert target_of(repo) == base
    assert unmerged(repo)


def test_a_resolution_that_drops_the_ticket_s_change_is_caught(repo, runner):
    given_a_resolution_that_drops_the_ticket_s_change(repo, runner)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 1
    assert "dropped" in report(ran)
    assert "shared.txt" in report(ran)
    assert target_of(repo) == base


def given_a_resolution_that_drops_the_ticket_s_change(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)

    # During a rebase "ours" is the new base, so this takes the other side wholesale.
    def settle(path):
        git(repo.work, "checkout", "--ours", "--", path.as_posix())
        git(repo.work, "add", path.as_posix())

    stub_session(repo, runner, settle)
    given_a_project(repo)
    given_a_conflict_beside_other_work(repo, 166, 164)


def test_a_stop_for_a_lost_file_shows_what_was_dropped_with_a_diff_of_both_commits(repo, runner):
    given_a_resolution_that_drops_the_ticket_s_change(repo, runner)
    before = git(repo.work, "rev-parse", "--short", "HEAD").strip()

    ran = run_land(runner, repo.work, 166, "session-abc")

    now = git(repo.work, "rev-parse", "--short", "HEAD").strip()
    assert "git -C {} diff {} {} -- shared.txt".format(
        repo.work.as_posix(), now, before) in report(ran)


def test_a_stop_for_a_lost_file_never_says_to_reset(repo, runner):
    given_a_resolution_that_drops_the_ticket_s_change(repo, runner)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert "reset" not in report(ran) and "ORIG_HEAD" not in report(ran)


def write(path, text):
    Path(path).write_text(text, encoding="utf-8", newline="\n")


# The ticket also changes work.txt, so git keeps its commit when the new base holds the rest.
def given_the_other_side_made_the_same_change(repo, runner, theirs_end="five"):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    given_a_project(repo)
    write(repo.work / "shared.txt", "one\ntwo\nthree\nfour\nfive\n")
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "A file both sides will change")
    git(repo.work, "push", "--quiet", "origin", repo.target)

    other = repo.other_checkout()
    write(other / "shared.txt", "one\nsame change\nthree\nfour\n{}\n".format(theirs_end))
    git(other, "add", "-A")
    git(other, "commit", "--quiet", "-m", "Somebody else got there first\n\nTicket: #164")
    git(other, "push", "--quiet", "origin", repo.target)

    write(repo.work / "shared.txt", "one\nsame change\nthree\nfour\nfive\n")
    append(repo.work / "work.txt", "work")
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "Do the work\n\nTicket: #167")


def test_a_ticket_lands_when_the_new_base_already_holds_its_change_to_a_file(repo, runner):
    given_the_other_side_made_the_same_change(repo, runner)

    ran = run_land(runner, repo.work, 167)

    assert (ran.status, target_of(repo)) == (0, head_of(repo))


def test_a_ticket_lands_when_the_new_base_holds_its_change_and_one_more_in_that_file(
        repo, runner):
    given_the_other_side_made_the_same_change(repo, runner, theirs_end="their last line")

    ran = run_land(runner, repo.work, 167)

    assert (ran.status, target_of(repo)) == (0, head_of(repo))


# Lines enough that git still pairs the two paths after one of them changes.
NOTE_REQUEST = "namespace Shop.Orders;\n\npublic record AddNoteRequest(\n    string Text,\n    string Author);\n"


def test_a_ticket_lands_when_the_other_side_renamed_a_file_it_changed(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    given_a_project(repo)
    write(repo.work / "notes.txt", "one\ntwo\nthree\nfour\nfive\n")
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "A file the other side will move")
    git(repo.work, "push", "--quiet", "origin", repo.target)

    other = repo.other_checkout()
    (other / "moved").mkdir()
    git(other, "mv", "notes.txt", "moved/notes.txt")
    git(other, "commit", "--quiet", "-m", "Somebody else moved it\n\nTicket: #164")
    git(other, "push", "--quiet", "origin", repo.target)

    write(repo.work / "notes.txt", "one\ntwo\nmy line\nfour\nfive\n")
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "Do the work\n\nTicket: #168")

    ran = run_land(runner, repo.work, 168)

    assert (ran.status, target_of(repo)) == (0, head_of(repo))


def given_a_resolution_that_moves_a_file_the_ticket_added(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)

    def settle(path):
        if path.name != "shared.txt":
            return
        path.write_text("start\ntheir line\nmy line\n", encoding="utf-8", newline="")
        git(repo.work, "add", path.as_posix())
        (repo.work / "Requests").mkdir()
        git(repo.work, "mv", "AddNoteRequest.cs", "Requests/AddNoteRequest.cs")
        write(repo.work / "Requests" / "AddNoteRequest.cs",
              NOTE_REQUEST.replace("Shop.Orders;", "Shop.Orders.Requests;"))
        git(repo.work, "add", "-A")

    stub_session(repo, runner, settle)
    given_a_project(repo)
    given_the_other_side_changed(repo, 164)
    append(repo.work / "shared.txt", "my line")
    write(repo.work / "AddNoteRequest.cs", NOTE_REQUEST)
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "Do the work\n\nTicket: #169")


def test_a_ticket_lands_when_its_resolution_moved_a_file_it_added(repo, runner):
    given_a_resolution_that_moves_a_file_the_ticket_added(repo, runner)

    ran = run_land(runner, repo.work, 169, "session-abc")

    assert (ran.status, target_of(repo)) == (0, head_of(repo))


def test_a_file_a_resolution_moved_is_named_in_a_note_with_both_paths(repo, runner):
    given_a_resolution_that_moves_a_file_the_ticket_added(repo, runner)

    ran = run_land(runner, repo.work, 169, "session-abc")

    assert "note  #169 moved AddNoteRequest.cs to Requests/AddNoteRequest.cs\n" in ran.out


def test_a_resolution_that_moved_a_file_reads_resolved(repo, runner):
    given_a_resolution_that_moves_a_file_the_ticket_added(repo, runner)

    ran = run_land(runner, repo.work, 169, "session-abc")

    assert "outcome=resolved" in ran.out


def test_a_git_that_turns_the_replay_down_stops_the_landing_and_names_git_2_38(repo, runner):
    given_the_other_side_made_the_same_change(repo, runner)
    runner.refuse("merge-tree", "error: unknown option `write-tree'")
    base = target_of(repo)

    ran = run_land(runner, repo.work, 167)

    assert (ran.status, target_of(repo), "2.38" in report(ran)) == (1, base, True)


def test_a_conflict_with_no_session_named_is_left_standing(repo, runner):
    given_the_suite_passes(runner)
    runner.stub("claude")
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 166)

    assert ran.status == 1
    assert "rebase --abort" in report(ran)
    assert target_of(repo) == base
    assert not runner.started("claude")


def test_a_ticket_whose_closing_note_cannot_be_read_is_still_named(repo, runner):
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
    base = target_of(repo)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 1
    assert "conflict marker" in report(ran)
    assert target_of(repo) == base


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
    base = target_of(repo)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 1
    assert "a later commit of its own conflicted" in report(ran)
    # Two conflicts were met, so two are recorded, and neither was proved good.
    assert report(ran).count("conflict #166") == 2
    assert target_of(repo) == base


def test_a_conflict_marker_in_a_crlf_file_is_caught(repo, runner):
    given_the_suite_passes(runner)
    given_the_tracker_answers(runner)
    # Only the middle marker is left, so the carriage return is what the check must see past.
    stub_session(repo, runner, staging(repo, "mine\r\n=======\r\ntheirs\r\n"))
    given_a_project(repo)
    given_a_conflict(repo, 166, 164)
    base = target_of(repo)

    ran = run_land(runner, repo.work, 166, "session-abc")

    assert ran.status == 1
    assert "conflict marker" in report(ran)
    assert target_of(repo) == base


def test_the_land_ticket_command_starts_the_landing_script_in_the_plugin(repo):
    ran = launch("land-ticket", where=repo.work)

    assert ran.status == 64
    assert ran.err.startswith(
        "usage: land-ticket <worktree> <ticket-number> [session-id] [--spec <spec-number>]\n")


# uv reads a script's dependencies from this block, so each script that reaches the Turn names the lock.
INLINE_METADATA = re.compile(
    r"^# /// script$\s(?P<content>(^#(| .*)$\s)+)^# ///$", re.MULTILINE)


def inline_dependencies(script):
    block = INLINE_METADATA.search((SCRIPTS / script).read_text(encoding="utf-8"))
    assert block is not None, script + " declares nothing for uv"
    toml = "".join(line[2:] for line in block.group("content").splitlines(keepends=True))
    return tomllib.loads(toml)["dependencies"]


@pytest.mark.parametrize("script", ["land_ticket.py", "spec_loop.py"])
def test_a_script_that_takes_the_turn_declares_the_lock_for_uv(script):
    assert [d for d in inline_dependencies(script) if d.startswith("filelock")]


def imported(source):
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


# A lock with a branch per OS is proved only on the OS the tests run on.
def test_no_plugin_script_locks_through_one_os_alone():
    reached = {path.name: imported(path.read_text(encoding="utf-8")) & {"msvcrt", "fcntl"}
               for path in SCRIPTS.rglob("*.py")}

    assert "land_ticket.py" in reached
    assert {name: names for name, names in reached.items() if names} == {}
