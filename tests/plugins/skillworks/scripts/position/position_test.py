import json
import os
from datetime import timedelta
from pathlib import Path

from conftest import ROOT
from spec_loop_test import (A_BLOCKED, A_CHOICE, A_DENIED_COMMAND, DEEPENED_BEFORE, FINISH,
                            FIRST_DEEPENING, FOLDED,
                            ONE_CLOSED_TICKET, ONE_OPEN_TICKET, SPEC, TWO_OPEN_TICKETS,
                            a_denied_command, all_of, baseline_tree, closed, committed,
                            deepening_report, drift_report, full_run_tree, given_a_cut_that_files,
                            given_a_deepening_limit, given_a_filed_ticket_that_lands,
                            given_a_session_that_was_denied, given_a_spec_axis_that_says,
                            given_drift_reports, given_sessions_that_report, given_simplify_enabled,
                            given_the_closed_ticket_landed_after_the_base, given_the_tracker_holds,
                            loop, rerun_holding, verdicts_alone)


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
    read_while(sessions, "spec-drift-check", loop, seen)

    loop.run(SPEC)

    assert [(row["number"], row["landed"]) for row in seen[0]["tickets"]] == [("168", True)]


def test_the_drift_check_shows_as_what_the_loop_does_now(loop):
    sessions = given_a_run_that_lands(loop)
    seen = []
    read_while(sessions, "spec-drift-check", loop, seen)

    loop.run(SPEC)

    assert seen[0]["doing"] == "drift check"


def test_the_name_check_shows_as_what_the_loop_does_now(loop):
    sessions = given_a_run_that_lands(loop)
    seen = []
    read_while(sessions, "spec-name-check", loop, seen)

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


def test_the_baseline_shows_as_what_the_loop_does_now(loop):
    given_a_run_that_lands(loop)
    seen = []

    def read_in_the_baseline():
        if loop.runner.where == baseline_tree(loop).as_posix():
            seen.append(position_of(loop))
    loop.runner.stub("docker", does=read_in_the_baseline)

    loop.run(SPEC)

    assert seen[0]["doing"] == "baseline"


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


HEARTBEAT = 30


def given_two_tickets_that_land(loop):
    tracker = given_the_tracker_holds(loop, TWO_OPEN_TICKETS)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(committed(loop.runner), closed(tracker))
    sessions.then["implement 169 --finish"] = all_of(
        committed(loop.runner, "169"), closed(tracker, "169"))
    # The first build's file is already on the Target branch, so the second build writes its own.
    sessions.then["implement 169 --stop-after-tests"] = lambda: (
        Path(loop.runner.where) / "built-169.txt").write_text("built\n", encoding="utf-8")
    return sessions


def test_with_time_held_still_the_heartbeat_does_not_move_while_a_step_runs(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    seen = []
    read_while(sessions, "review-standards", loop, seen)
    read_while(sessions, "review-spec", loop, seen)

    loop.run(SPEC)

    assert {each["heartbeat"] for each in seen} == {"2026-01-01T00:00:00Z"}


def test_with_time_moved_past_the_heartbeat_while_a_step_runs_the_position_holds_a_later_heartbeat_and_the_same_step(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    seen = []

    def moved_on_while_held():
        seen.append(position_of(loop))
        loop.clock.move(HEARTBEAT + 1)
        seen.append(position_of(loop))
    sessions.then["review-standards"] = moved_on_while_held

    loop.run(SPEC)

    before, after = seen
    assert {**after, "heartbeat": before["heartbeat"]} == before and (
        after["heartbeat"] == "2026-01-01T00:00:30Z")


def test_the_step_started_time_is_read_off_the_clock(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    seen = []
    sessions.then["review-standards"] = lambda: loop.clock.move(100)
    read_while(sessions, "review-spec", loop, seen)

    loop.run(SPEC)

    assert seen[0]["ticket"]["step_started"] == "2026-01-01T00:01:40Z"


def test_the_time_left_is_measured_on_the_clock(loop):
    sessions = given_two_tickets_that_land(loop)
    seen = []
    sessions.then["review-standards 168"] = lambda: loop.clock.move(600)
    read_while(sessions, "review-standards 169", loop, seen)

    loop.run(SPEC)

    assert seen[0]["seconds_left"] == 600


def test_after_a_finished_run_the_heartbeat_is_no_longer_written(loop):
    given_a_run_that_lands(loop)
    loop.run(SPEC)
    last = position_of(loop)

    loop.clock.move(HEARTBEAT * 3)

    assert position_of(loop) == last and last["doing"] == "finished"


def test_after_a_stopped_run_the_heartbeat_is_no_longer_written(loop):
    given_a_build_that_is_blocked(loop)
    loop.run(SPEC)
    last = position_of(loop)

    loop.clock.move(HEARTBEAT * 3)

    assert position_of(loop) == last and last["doing"] == "stopped"


HELD = PermissionError(13, "Access is denied")


def held_by_a_reader(source, target):
    raise HELD


def test_a_heartbeat_whose_write_fails_for_one_beat_writes_the_position_at_the_next_beat(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    seen = []

    def one_beat_held():
        beat_once_with(loop, held_by_a_reader)
        loop.clock.move(HEARTBEAT)
        seen.append(position_of(loop))
    sessions.then["review-standards"] = one_beat_held

    loop.run(SPEC)

    assert seen[0]["heartbeat"] == "2026-01-01T00:01:00Z"


def test_a_step_change_whose_write_fails_leaves_the_run_going_and_the_next_beat_writes_the_new_step(loop):
    sessions = given_a_run_that_lands(loop)
    seen = []

    def held_from_the_build_on():
        loop.replace = held_by_a_reader

    def beat_once_let_go():
        loop.replace = os.replace
        loop.clock.move(HEARTBEAT)
        seen.append(position_of(loop))
    sessions.then["implement 168 --stop-after-tests"] = held_from_the_build_on
    sessions.then["review-standards"] = beat_once_let_go

    ran = loop.run(SPEC)

    assert (ran.status, seen[0]["ticket"]["step"]) == (0, "standards")


def test_a_write_that_fails_puts_one_line_in_the_log_that_names_the_error(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then["review-standards"] = lambda: beat_once_with(loop, held_by_a_reader)

    loop.run(SPEC)

    assert position_lines(loop) == [
        "WARN  the Position was not written, PermissionError: [Errno 13] Access is denied"]


def failing_for(tries, error):
    failures = iter(range(tries))

    def replace(source, target):
        if next(failures, None) is not None:
            raise error
        os.replace(source, target)
    return replace


def position_lines(loop):
    return [line[line.index("WARN"):] for line in loop.log().splitlines() if "Position" in line]


def test_a_replace_held_a_few_times_within_the_second_lands_the_position_and_logs_nothing(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    seen = []

    def beat_held_three_times():
        beat_once_with(loop, failing_for(3, HELD))
        seen.append((position_of(loop)["heartbeat"], position_lines(loop)))
    sessions.then["review-standards"] = beat_held_three_times

    loop.run(SPEC)

    assert seen[0] == ("2026-01-01T00:00:30Z", [])


def test_a_replace_held_every_time_gives_up_after_one_second_of_clock_time(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    spent = []

    def beat_held_throughout():
        before = loop.clock.now()
        beat_once_with(loop, held_by_a_reader)
        spent.append(loop.clock.now() - before)
    sessions.then["review-standards"] = beat_held_throughout

    loop.run(SPEC)

    assert spent[0] == timedelta(seconds=HEARTBEAT + 1)


def test_a_write_that_fails_for_another_reason_is_not_tried_again_and_logs_its_line(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    seen = []

    def beat_on_a_full_disk_once():
        before = position_of(loop)
        beat_once_with(loop, failing_for(1, OSError(28, "No space left on device")))
        seen.append((position_of(loop) == before, position_lines(loop)))
    sessions.then["review-standards"] = beat_on_a_full_disk_once

    loop.run(SPEC)

    assert seen[0] == (True, ["WARN  the Position was not written, OSError: [Errno 28] No space left on device"])


def held_at_the_end_for(loop, seconds):
    began = []

    def replace(source, target):
        if json.loads(Path(source).read_text(encoding="utf-8"))["doing"] in ("finished", "stopped"):
            if not began:
                began.append(loop.clock.now())
            if loop.clock.now() - began[0] < timedelta(seconds=seconds):
                raise HELD
        os.replace(source, target)
    return replace


def test_an_end_write_held_for_longer_than_a_second_still_leaves_finished(loop):
    given_a_run_that_lands(loop)
    loop.replace = held_at_the_end_for(loop, 5)

    loop.run(SPEC)

    assert position_of(loop)["doing"] == "finished"


def test_an_end_write_held_for_longer_than_a_second_still_leaves_stopped(loop):
    given_a_build_that_is_blocked(loop)
    loop.replace = held_at_the_end_for(loop, 5)

    loop.run(SPEC)

    assert position_of(loop)["doing"] == "stopped"


def test_an_end_write_held_past_thirty_seconds_gives_up_with_one_line_and_the_run_ends_as_it_would(loop):
    given_a_run_that_lands(loop)
    loop.replace = held_at_the_end_for(loop, 60)

    ran = loop.run(SPEC)

    assert (ran.status, position_lines(loop)) == (
        0, ["WARN  the Position was not written, PermissionError: [Errno 13] Access is denied"])


def beat_once_with(loop, replace):
    loop.replace = replace
    loop.clock.move(HEARTBEAT)
    loop.replace = os.replace


def judges_of(position):
    return [(judge["name"], judge["state"]) for judge in position["judges"]]


def test_before_the_judges_run_every_judge_is_to_come_in_the_loop_s_order(loop):
    sessions = given_a_run_that_lands(loop)
    seen = []
    read_while(sessions, "implement 168 --stop-after-tests", loop, seen)

    loop.run(SPEC)

    assert judges_of(seen[0]) == [
        ("deepening-check", "to come"), ("simplify-check", "to come"),
        ("drift-check", "to come"), ("name-check", "to come")]


def judge_in(position, name):
    return next(judge for judge in position["judges"] if judge["name"] == name)


def given_a_deepening_check_that_files(loop, *strong):
    tracker = given_the_tracker_holds(loop, ONE_CLOSED_TICKET)
    sessions = given_sessions_that_report(loop)
    given_the_closed_ticket_landed_after_the_base(loop)
    given_a_filed_ticket_that_lands(loop, tracker, sessions, FIRST_DEEPENING)
    tracker.deepening_report = deepening_report(*strong)
    return sessions


def test_a_judge_reads_now_while_its_session_runs(loop):
    sessions = given_a_run_that_lands(loop)
    seen = []
    read_while(sessions, "spec-simplify-check", loop, seen)

    loop.run(SPEC)

    assert judge_in(seen[0], "simplify-check")["state"] == "now"


def test_a_judge_that_ended_reads_done_with_its_count_and_the_tickets_it_filed(loop):
    given_a_deepening_check_that_files(loop, FOLDED)

    loop.run(SPEC)

    assert judge_in(position_of(loop), "deepening-check") == {
        "name": "deepening-check", "state": "done", "found": 1, "word": "Strong",
        "filed": [FIRST_DEEPENING]}


def test_judges_the_team_turned_off_read_off_from_the_first_position(loop):
    sessions = given_a_run_that_lands(loop)
    given_a_deepening_limit(loop, "0")
    given_simplify_enabled(loop, "false")
    seen = []
    read_while(sessions, "implement 168 --stop-after-tests", loop, seen)

    loop.run(SPEC)

    assert judges_of(seen[0])[:2] == [("deepening-check", "off"), ("simplify-check", "off")]


def test_a_judge_a_rerun_found_already_filed_reads_done_with_its_count_and_its_tickets(loop):
    tracker, _ = rerun_holding(loop, DEEPENED_BEFORE)
    tracker.posted_before = [deepening_report(FOLDED)]

    loop.run(SPEC)

    assert judge_in(position_of(loop), "deepening-check") == {
        "name": "deepening-check", "state": "done", "found": 1, "word": "Strong",
        "filed": ["162"]}


def test_a_judge_that_found_nothing_reads_done_with_a_count_of_0_and_no_tickets(loop):
    given_a_run_that_lands(loop)

    loop.run(SPEC)

    assert judge_in(position_of(loop), "drift-check") == {
        "name": "drift-check", "state": "done", "found": 0, "word": "Gaps", "filed": []}


def test_a_judge_whose_re_check_is_still_to_run_reads_now_while_its_ticket_builds(loop):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(committed(loop.runner), closed(tracker))
    given_a_filed_ticket_that_lands(loop, tracker, sessions, "169")
    given_drift_reports(sessions, tracker, drift_report(S1="Missing"), verdicts_alone(S1="Done"))
    seen = []
    read_while(sessions, "implement 169 --stop-after-tests", loop, seen)

    loop.run(SPEC)

    assert judge_in(seen[0], "drift-check")["state"] == "now"


def judge_of_each_ticket(position):
    return [(row["number"], row["judge"]) for row in position["tickets"]]


def test_a_ticket_from_the_cut_names_no_judge(loop):
    tracker = given_the_tracker_holds(loop, ())
    sessions = given_sessions_that_report(loop)
    given_a_cut_that_files(sessions, tracker, ONE_OPEN_TICKET)
    sessions.then[FINISH] = all_of(committed(loop.runner), closed(tracker))

    loop.run(SPEC)

    assert judge_of_each_ticket(position_of(loop)) == [("168", None)]


def test_a_ticket_a_judge_filed_names_that_judge_s_step(loop):
    given_a_deepening_check_that_files(loop, FOLDED)

    loop.run(SPEC)

    assert judge_of_each_ticket(position_of(loop)) == [
        ("161", None), (FIRST_DEEPENING, "deepening-check")]


def test_a_ticket_a_judge_files_is_not_in_the_position_while_the_judge_runs(loop):
    sessions = given_a_deepening_check_that_files(loop, FOLDED)
    seen = []
    read_while(sessions, "spec-deepening-check", loop, seen)

    loop.run(SPEC)

    assert judge_of_each_ticket(seen[0]) == [("161", None)]


def test_reading_a_run_names_the_position_file_beside_the_log():
    page = (ROOT / "docs" / "usage" / "the-loop" / "reading-a-run.md").read_text(encoding="utf-8")

    assert "`.spec-loop/<spec>/position.json`" in page
