import json
import os

from conftest import ROOT
from spec_loop_test import (A_BLOCKED, A_CHOICE, A_DENIED_COMMAND, FINISH, ONE_OPEN_TICKET, SPEC,
                            a_denied_command, all_of, closed, committed, full_run_tree,
                            given_a_session_that_was_denied, given_a_spec_axis_that_says,
                            given_sessions_that_report, given_the_tracker_holds, loop)


def position_of(loop):
    return json.loads((loop.records() / "position.json").read_text(encoding="utf-8"))


def read_while(sessions, mark, loop, seen):
    sessions.then[mark] = lambda: seen.append(position_of(loop))


def given_a_run_that_lands(loop):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(committed(loop.runner), closed(tracker))
    return sessions


def given_a_build_that_is_blocked(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop).says["implement"] = A_BLOCKED


def test_a_position_read_while_a_step_runs_names_that_step(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    seen = []
    read_while(sessions, "review-standards", loop, seen)

    loop.run(SPEC)

    assert (seen[0]["ticket"]["number"], seen[0]["ticket"]["step"]) == ("168", "standards")


def test_a_ticket_that_lands_shows_as_landed_in_the_next_position(loop):
    sessions = given_a_run_that_lands(loop)
    seen = []
    read_while(sessions, "spec-drift", loop, seen)

    loop.run(SPEC)

    assert [(row["number"], row["landed"]) for row in seen[0]["tickets"]] == [("168", True)]


def test_the_drift_check_shows_as_what_the_loop_does_now(loop):
    sessions = given_a_run_that_lands(loop)
    seen = []
    read_while(sessions, "spec-drift", loop, seen)

    loop.run(SPEC)

    assert seen[0]["doing"] == "drift check"


def test_the_name_check_shows_as_what_the_loop_does_now(loop):
    sessions = given_a_run_that_lands(loop)
    seen = []
    read_while(sessions, "spec-names", loop, seen)

    loop.run(SPEC)

    assert seen[0]["doing"] == "Name check"


def test_the_full_run_shows_as_what_the_loop_does_now(loop):
    given_a_run_that_lands(loop)
    seen = []

    def read_in_the_full_run():
        if loop.runner.where == full_run_tree(loop):
            seen.append(position_of(loop))
    loop.runner.stub("dotnet", says="the solution passed", does=read_in_the_full_run)

    loop.run(SPEC)

    assert seen[0]["doing"] == "full run"


def test_a_stop_leaves_a_position_that_says_stopped_with_the_stop_line_and_the_log(loop):
    given_a_build_that_is_blocked(loop)

    loop.run(SPEC)

    position = position_of(loop)
    stop = position["stop"]
    assert (position["doing"], stop["line"].split("\n")[0], stop["log"]) == (
        "stopped", "STOP  #168 step build is Blocked: " + A_BLOCKED,
        ".spec-loop/{}/loop.log".format(SPEC))


def test_the_end_leaves_a_position_that_says_finished(loop):
    given_a_run_that_lands(loop)

    ran = loop.run(SPEC)

    assert (ran.status, position_of(loop)["doing"]) == (0, "finished")


def test_two_runs_of_the_driver_on_one_spec_write_two_run_ids(loop):
    given_a_build_that_is_blocked(loop)
    loop.run(SPEC)
    first = position_of(loop)["run"]

    loop.run(SPEC)

    assert position_of(loop)["run"] != first


def test_the_counts_of_choices_and_denials_match_what_the_run_met(loop):
    sessions = given_a_run_that_lands(loop)
    given_a_spec_axis_that_says(sessions, A_CHOICE)
    given_a_session_that_was_denied(sessions, "review-standards", A_DENIED_COMMAND,
                                    a_denied_command(2))

    loop.run(SPEC)

    position = position_of(loop)
    assert (position["choices"], position["denials"]) == (1, 2)


# A file written over in place keeps its identity, and one renamed into place is a new file.
def test_each_position_is_a_new_file_renamed_into_place(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    seen = []
    path = loop.records() / "position.json"
    sessions.then["review-standards"] = lambda: seen.append(os.stat(path).st_ino)
    sessions.then["review-spec"] = lambda: seen.append(os.stat(path).st_ino)

    loop.run(SPEC)

    assert len(seen) == 2 and seen[0] != seen[1]


def test_a_run_leaves_no_part_written_file_beside_the_position(loop):
    given_a_run_that_lands(loop)

    loop.run(SPEC)

    assert sorted(path.name for path in loop.records().glob("position*")) == ["position.json"]


def test_a_dry_run_leaves_no_position(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    loop.run(SPEC, "--dry-run")

    assert not (loop.records() / "position.json").exists()


def test_reading_a_run_names_the_position_file_beside_the_log():
    page = (ROOT / "docs" / "usage" / "the-loop" / "reading-a-run.md").read_text(encoding="utf-8")

    assert "`.spec-loop/<spec>/position.json`" in page
