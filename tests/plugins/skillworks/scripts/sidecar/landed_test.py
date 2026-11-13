# Driven through the loop and the commands that read the list, with a real bare origin and a real Sidecar.

import contextlib
import io
import json
from pathlib import Path

import pytest

import land_ticket
import spec_loop
from clock.held_clock import HeldClock
from conftest import Ran, RecordingRunner, Repo, git, project_suite, write_steering, write_suite
from runner import Subprocess
from sidecar.landed import LIST, Landed
from sidecar.locator import sidecar_of
from sidecar.sidecar import Sidecar
from spec_loop_test import Sessions, given_a_suite_that_passes
from steering.target_branch import LOOP_FILE
from tracker import close, publish

SPEC = "7"
FOLDER = ".specs/0007-sidecar-steering"
SPEC_BRANCH = "feature/sidecar-steering"

COUNTED = ("## User Stories\n\n1. As a team member, I want a list.\n\n"
           "## Implementation Decisions\n\n1. The list is in the Sidecar.\n\n## Surfaces\n\nNone\n")

DRIFT = "## Drift report\n\n### Verdicts\n\n- S1: Done\n- D1: Done\n- The README: In step\n"
NAMES = "## Name report\n\n### Renames\n\n- None\n"


def spec_file(status="open"):
    return "\n".join(["---", "status: " + status, "branch: " + SPEC_BRANCH, "---", "",
                      "# SPEC: A list of Landed commits", "", COUNTED])


def ticket_file(title, status="open"):
    return "\n".join(["---", "status: " + status, "blocked-by: []", "---", "", "# " + title, ""])


def ticket_path(name):
    return "{}/tickets/{}.md".format(FOLDER, name)


def write_files(where, files):
    for name, text in files.items():
        path = Path(where) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def write_loop(top):
    path = Path(top) / LOOP_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tracker": "files", "target-branch": "pr"}, indent=2),
                    encoding="utf-8", newline="\n")


def said(ran):
    return ran.out + ran.err


class Steered:
    def __init__(self, repo, runner):
        self.repo = repo
        self.runner = runner
        self.sidecar = sidecar_of(Subprocess(), repo.work)

    # Written as the Tracker writes, one commit under the lock, so the loop reads it as it would its own.
    def put(self, files):
        Sidecar.of(Subprocess(), self.repo.work, HeldClock()).write(
            "Tracker state", lambda folder: write_files(folder, files))

    def run(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.chdir(self.repo.work):
            status = spec_loop.main([SPEC], self.runner, out, err, lambda seconds: None, HeldClock())
        return Ran(status, out.getvalue(), err.getvalue())

    def listed(self):
        path = self.sidecar / LIST
        if not path.is_file():
            return []
        return [line.split("\t") for line in path.read_text(encoding="utf-8").splitlines() if line]

    def on_origin(self, *args):
        return git(self.repo.origin, *args)


# The Steering sits in the Sidecar, so the mode is on and the repo holds none of it.
@pytest.fixture
def steered(tmp_path, monkeypatch):
    repo = Repo(tmp_path)
    monkeypatch.chdir(repo.work)
    monkeypatch.delenv("SPEC_LOOP_PERMISSION_MODE", raising=False)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", (tmp_path / "claude").as_posix())
    held = Steered(repo, RecordingRunner())
    write_loop(held.sidecar)
    write_steering(held.sidecar)
    return held


def recording(steered, command, report):
    def record():
        held = steered.repo.root / (command + "-report.md")
        held.write_text(report, encoding="utf-8", newline="\n")
        publish.main([command, SPEC, held.as_posix()], RecordingRunner(), io.StringIO(),
                     io.StringIO(), HeldClock(), steered.repo.work.as_posix())
    return record


def closed_by_command(tree, ticket):
    held = Path(tree).parent / "closing-note.md"
    held.write_text("Built it. Proved by its tests.\n", encoding="utf-8", newline="\n")
    close.main([ticket, held.as_posix()], RecordingRunner(), io.StringIO(), io.StringIO(),
               Path(tree).as_posix())


# What /skillworks:implement does at Finishing: commit, then close through tracker-close.
def finishing(runner, ticket, *names, trailer=True):
    def finish():
        tree = Path(runner.where)
        for name in names:
            (tree / name).write_text("{} by {}\n".format(name, ticket), encoding="utf-8",
                                     newline="\n")
            git(tree, "add", "-A")
            git(tree, "commit", "--quiet", "-m",
                "Wrote " + name + ("\n\nTicket: " + ticket if trailer else ""))
        closed_by_command(tree, ticket)
    return finish


# A file of its own, since what an earlier ticket built is already on the branch.
def building(runner, number):
    def build():
        (Path(runner.where) / "built-{}.txt".format(number)).write_text(
            "built\n", encoding="utf-8", newline="\n")
    return build


# Beside the rest of the Steering, because the Suite reads its file from wherever the Steering sits.
def given_a_suite_that_passes_where_the_steering_sits(steered):
    if not (steered.sidecar / LOOP_FILE).is_file():
        given_a_suite_that_passes(steered)
        return
    write_suite(steered.sidecar, project_suite()[0])
    steered.runner.stub("docker")
    steered.runner.stub("dotnet", says="the solution passed")


def given_tickets_that_land(steered, *tickets, trailer=True):
    given_a_suite_that_passes_where_the_steering_sits(steered)
    git(steered.repo.work, "push", "--quiet", "origin", "main:" + SPEC_BRANCH)
    files = {FOLDER + "/spec.md": spec_file()}
    sessions = Sessions(steered.repo, steered.runner)
    for number, names in tickets:
        files[ticket_path("{:02d}-ticket".format(number))] = ticket_file("Ticket {}".format(number))
        reference = "{}/{}".format(SPEC, number)
        sessions.then["implement {} --stop-after-tests".format(reference)] = building(
            steered.runner, number)
        sessions.then["implement {} --finish".format(reference)] = finishing(
            steered.runner, reference, *names, trailer=trailer)
    steered.put(files)
    sessions.then["spec-drift"] = recording(steered, "drift", DRIFT)
    sessions.then["spec-names"] = recording(steered, "names", NAMES)
    return sessions


def commits_of(steered, grep):
    return git(steered.repo.origin, "log", "--reverse", "--format=%H", "--grep=" + grep,
               SPEC_BRANCH).split()


# A person's commit on the spec's branch, made while the loop builds, with a trailer typed by hand.
def given_a_hand_commit_while_the_ticket_builds(steered, sessions, reference="7/1"):
    def push_by_hand():
        other = steered.repo.other_checkout()
        git(other, "checkout", "--quiet", SPEC_BRANCH)
        steered.repo.write_commit(other, "by-hand.txt", "by hand",
                                  "Mended by hand\n\nTicket: " + reference)
        git(other, "push", "--quiet", "origin", SPEC_BRANCH)
    sessions.then["review-spec " + reference] = push_by_hand


# --- the list a Land writes ---------------------------------------------------

def test_after_a_ticket_lands_the_list_holds_exactly_its_landed_commits(steered):
    given_tickets_that_land(steered, (1, ("one.txt", "two.txt")))

    ran = steered.run()

    landed = commits_of(steered, "Wrote ")
    assert ran.status == 0, said(ran)
    assert (len(landed), steered.listed()) == (2, [[SPEC_BRANCH, commit, "7/1"]
                                                   for commit in landed])


# The Steering moves into the repo, so the Sidecar holds the Tracker alone and the mode is off.
def test_outside_sidecar_steering_a_landed_ticket_writes_no_list_and_its_trailer_scopes_the_spec(
        steered):
    (steered.sidecar / LOOP_FILE).unlink()
    write_loop(steered.repo.work)
    write_steering(steered.repo.work)
    sessions = given_tickets_that_land(steered, (1, ("one.txt",)))
    given_a_hand_commit_while_the_ticket_builds(steered, sessions)

    ran = steered.run()

    assert ran.status == 0, said(ran)
    assert not (steered.sidecar / LIST).exists()
    assert "SCOPE the drift check reads 2 commits of spec 7" in ran.out


def land_by_hand(steered, ticket):
    out, err = io.StringIO(), io.StringIO()
    status = land_ticket.main([steered.repo.work.as_posix(), ticket, "--spec", SPEC], RecordingRunner(),
                              out, err, lambda seconds: None)
    return Ran(status, out.getvalue(), err.getvalue())


def test_a_commit_with_no_trailer_lands_and_is_listed_for_its_ticket(steered):
    given_tickets_that_land(steered, (1, ()))
    git(steered.repo.work, "checkout", "--quiet", "-b", SPEC_BRANCH, "origin/" + SPEC_BRANCH)
    steered.repo.write_commit(steered.repo.work, "plain.txt", "plain", "Wrote it with no trailer")

    ran = land_by_hand(steered, "1")

    assert ran.status == 0, said(ran)
    assert steered.listed() == [[SPEC_BRANCH, commits_of(steered, "no trailer")[0], "7/1"]]


# --- a branch rewritten under the list ------------------------------------------

# A person's force-push of a commit of their own onto where the spec's branch started, dropping what Landed.
def rewrite_the_branch(steered):
    other = steered.repo.other_checkout()
    git(other, "checkout", "--quiet", "-b", "rewritten", "origin/main")
    steered.repo.write_commit(other, "rewritten.txt", "rewritten", "Rewritten by hand")
    git(other, "push", "--quiet", "--force", "origin", "rewritten:" + SPEC_BRANCH)


def given_a_force_push_while_the_ticket_builds(steered, sessions, reference):
    sessions.then["review-spec " + reference] = lambda: rewrite_the_branch(steered)


def dropped_line(commit):
    return ("{b} on origin no longer holds commit {c}, which the Sidecar lists as Landed for "
            "ticket 7/1. {b} was rewritten under the list").format(b=SPEC_BRANCH, c=commit)


def test_a_force_push_that_drops_a_listed_commit_stops_the_land_with_a_line_naming_the_branch(
        steered):
    sessions = given_tickets_that_land(steered, (1, ("one.txt",)), (2, ("three.txt",)))
    given_a_force_push_while_the_ticket_builds(steered, sessions, "7/2")

    ran = steered.run()

    [dropped] = [line[1] for line in steered.listed() if line[2] == "7/1"]
    assert ran.status == 1
    assert dropped_line(dropped) in ran.out
    assert "three.txt" not in steered.on_origin("ls-tree", "--name-only", SPEC_BRANCH).split()


def test_a_rerun_after_a_force_push_that_dropped_a_listed_commit_stops_before_any_ticket(steered):
    given_tickets_that_land(steered, (1, ("one.txt",)), (2, ("three.txt",)))
    steered.put({ticket_path("02-ticket"): ticket_file("Ticket 2", status="closed")})
    steered.run()
    steered.put({FOLDER + "/spec.md": spec_file(), ticket_path("02-ticket"): ticket_file("Ticket 2")})
    rewrite_the_branch(steered)

    ran = steered.run()

    [dropped] = [line[1] for line in steered.listed() if line[2] == "7/1"]
    assert (ran.status, "START" in ran.out) == (1, False), said(ran)
    assert dropped_line(dropped) in ran.out


# --- the conflict's other side --------------------------------------------------

# A commit on the spec's branch that changes the file ticket 2 changes too, so its Land conflicts.
def given_the_other_side_lands_while_ticket_2_builds(steered, sessions, listed_for=None):
    def push():
        other = steered.repo.other_checkout()
        git(other, "checkout", "--quiet", SPEC_BRANCH)
        (other / "one.txt").write_text("their line\n", encoding="utf-8", newline="\n")
        # A listed commit carries no trailer, so only the list can name its ticket.
        git(other, "commit", "--quiet", "-am",
            "Their change" if listed_for else "Their change\n\nTicket: 7/1")
        git(other, "push", "--quiet", "origin", SPEC_BRANCH)
        if listed_for:
            Landed(Subprocess(), steered.repo.work).add(
                SPEC_BRANCH, listed_for, [git(other, "rev-parse", "HEAD").strip()])
    sessions.then["review-spec 7/2"] = push


def resolve_prompt(steered):
    asked = [call[-1] for call in steered.runner.started("claude")
             if call[-1].startswith("/skillworks:resolve-conflict")]
    return asked[0] if asked else ""


def test_a_commit_on_the_other_side_with_a_trailer_typed_by_hand_names_no_ticket(steered):
    sessions = given_tickets_that_land(steered, (1, ("one.txt",)), (2, ("one.txt",)))
    given_the_other_side_lands_while_ticket_2_builds(steered, sessions)

    steered.run()

    assert "Their change\n\nThis commit names no ticket." in resolve_prompt(steered)


def test_a_commit_on_the_other_side_is_named_by_the_ticket_the_list_holds_it_for(steered):
    sessions = given_tickets_that_land(steered, (1, ("one.txt",)), (2, ("one.txt",)))
    given_the_other_side_lands_while_ticket_2_builds(steered, sessions, listed_for="7/1")

    steered.run()

    assert "Their change, from ticket 7/1\n\nHow 7/1 was closed:\n\nBuilt it." in resolve_prompt(
        steered)


# --- the spec's scope ---------------------------------------------------------

def test_a_commit_made_by_hand_on_the_branch_counts_toward_no_ticket(steered):
    sessions = given_tickets_that_land(steered, (1, ("one.txt", "two.txt")))
    given_a_hand_commit_while_the_ticket_builds(steered, sessions)

    ran = steered.run()

    assert ran.status == 0, said(ran)
    assert ("SCOPE the drift check reads 2 commits of spec 7, and leaves out 1 other commit "
            "after the base commit") in ran.out


def test_a_spec_whose_tickets_the_list_holds_no_commit_for_stops_naming_the_list(steered):
    given_tickets_that_land(steered, (1, ("one.txt",)))
    steered.put({ticket_path("01-ticket"): ticket_file("Ticket 1", status="closed")})

    ran = steered.run()

    assert ran.status == 1
    assert "that the list in the Sidecar holds for one of its tickets. 7/1 is closed" in ran.out, \
        said(ran)


# --- the Sessions the loop starts -------------------------------------------------

SIDECAR_SETTINGS = ".claude/settings.json"


def given_sidecar_settings(steered):
    path = steered.sidecar / SIDECAR_SETTINGS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"includeCoAuthoredBy": false}\n', encoding="utf-8", newline="\n")


def sessions_started(steered):
    return [call for call in steered.runner.made if call.args[0] == "claude"]


def given_after(call, flag):
    return call.args[call.args.index(flag) + 1] if flag in call.args else None


def what_a_session_is_given(steered, call):
    return (Path(given_after(call, "--add-dir") or "") == steered.sidecar,
            Path(given_after(call, "--settings") or "") == steered.sidecar / SIDECAR_SETTINGS,
            (call.env or {}).get("CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD"))


def test_under_sidecar_steering_every_session_gets_the_sidecar_its_claude_md_and_its_settings(
        steered):
    given_sidecar_settings(steered)
    given_tickets_that_land(steered, (1, ("one.txt",)), trailer=False)

    steered.run()

    started = sessions_started(steered)
    assert started
    assert {what_a_session_is_given(steered, call) for call in started} == {(True, True, "1")}


def test_under_sidecar_steering_the_conflict_session_gets_the_sidecar_its_claude_md_and_its_settings(
        steered):
    given_sidecar_settings(steered)
    sessions = given_tickets_that_land(steered, (1, ("one.txt",)), (2, ("one.txt",)))
    given_the_other_side_lands_while_ticket_2_builds(steered, sessions, listed_for="7/1")

    steered.run()

    [resolving] = [call for call in sessions_started(steered)
                   if call.stdin and call.stdin.startswith("/skillworks:resolve-conflict")]
    assert what_a_session_is_given(steered, resolving) == (True, True, "1")


def test_under_sidecar_steering_no_session_is_handed_a_ticket_for_the_hook(steered):
    given_tickets_that_land(steered, (1, ("one.txt",)), trailer=False)

    steered.run()

    started = sessions_started(steered)
    assert started
    assert [call for call in started if (call.env or {}).get("SKILLWORKS_TICKET")] == []


def test_outside_sidecar_steering_no_session_is_given_the_sidecar(steered):
    (steered.sidecar / LOOP_FILE).unlink()
    write_loop(steered.repo.work)
    write_steering(steered.repo.work)
    given_tickets_that_land(steered, (1, ("one.txt",)))

    steered.run()

    started = sessions_started(steered)
    assert started
    assert [call for call in started if "--add-dir" in call.args] == []


def test_under_sidecar_steering_a_finish_that_did_not_commit_is_nudged_to_commit_with_no_trailer(
        steered):
    sessions = given_tickets_that_land(steered, (1, ("one.txt",)), trailer=False)
    finish = "implement 7/1 --finish"
    sessions.when_nudged[finish] = sessions.then[finish]
    sessions.then[finish] = lambda: closed_by_command(steered.runner.where, "7/1")

    ran = steered.run()

    [nudge] = [call.stdin for call in sessions_started(steered)
               if call.stdin and call.stdin.startswith("You have not committed the work")]
    assert ran.status == 0, said(ran)
    assert "Ticket:" not in nudge


def test_under_sidecar_steering_tickets_whose_commits_carry_no_trailer_land_on_the_named_branch(
        steered):
    given_tickets_that_land(steered, (1, ("one.txt",)), (2, ("two.txt",)), trailer=False)

    ran = steered.run()

    assert ran.status == 0, said(ran)
    assert steered.on_origin("log", "--format=%(trailers:only)", "main.." + SPEC_BRANCH).strip() == ""
    assert {"one.txt", "two.txt"} <= set(
        steered.on_origin("ls-tree", "--name-only", SPEC_BRANCH).split())
