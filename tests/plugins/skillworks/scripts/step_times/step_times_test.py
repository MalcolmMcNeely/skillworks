import json

from conftest import ROOT
from spec_loop_test import (A_BLOCKED, FINISH, ONE_OPEN_TICKET, SPEC, all_of, closed, committed,
                            drift_report, given_a_cut_that_files,
                            given_a_run_that_lands_and_goes_round, given_sessions_that_report,
                            given_the_tracker_holds, loop, verdicts_alone)


def position_of(loop):
    return json.loads((loop.records() / "position.json").read_text(encoding="utf-8"))


def given_a_build_that_is_blocked(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop).says["implement"] = A_BLOCKED


def step_times_of(loop):
    path = loop.records() / "step-times.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def pieces_of(loop):
    return [(each["name"], each["ticket"]) for each in step_times_of(loop)]


def given_a_run_that_lands(loop):
    tracker = given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.then[FINISH] = all_of(committed(loop.runner), closed(tracker))
    return sessions


def test_a_run_that_lands_keeps_a_step_time_for_every_piece_in_the_order_they_ended(loop):
    given_a_run_that_lands(loop)

    loop.run(SPEC)

    assert pieces_of(loop) == [
        ("baseline", None),
        ("build", "168"), ("standards", "168"), ("spec", "168"), ("architecture", "168"),
        ("fix", "168"), ("sweep", "168"), ("suite", "168"), ("finish", "168"), ("land", "168"),
        ("deepening-check", None), ("simplify-check", None), ("drift-check", None),
        ("name-check", None),
        ("full-run", None)]


def test_a_step_s_start_and_end_are_read_off_the_clock_the_test_moved(loop):
    sessions = given_a_run_that_lands(loop)
    sessions.then["review-spec"] = lambda: loop.clock.move(100)

    loop.run(SPEC)

    spec_step = next(each for each in step_times_of(loop) if each["name"] == "spec")
    assert (spec_step["started"], spec_step["ended"]) == (
        "2026-01-01T00:00:00Z", "2026-01-01T00:01:40Z")


def test_the_cut_keeps_a_step_time_of_its_own_before_the_first_ticket_s(loop):
    tracker = given_the_tracker_holds(loop, ())
    sessions = given_sessions_that_report(loop)
    given_a_cut_that_files(sessions, tracker, ONE_OPEN_TICKET)

    loop.run(SPEC)

    assert pieces_of(loop)[1:3] == [("cut", None), ("build", "168")]


def test_a_drift_re_check_adds_to_the_drift_check_s_step_and_names_no_piece_of_its_own(loop):
    given_a_run_that_lands_and_goes_round(loop, drift_report(S1="Missing"),
                                          verdicts_alone(S1="Done"))

    loop.run(SPEC)

    names = [name for name, _ in pieces_of(loop)]
    assert (names.count("drift-check"), [name for name in names if "re-check" in name]) == (2, [])


def test_a_restarted_spec_adds_its_entries_after_the_old_ones_and_changes_none(loop):
    given_a_build_that_is_blocked(loop)
    loop.run(SPEC)
    first = step_times_of(loop)

    loop.run(SPEC)

    again = step_times_of(loop)
    old_runs = {each["run"] for each in first}
    new_runs = {each["run"] for each in again[len(first):]}
    assert (bool(first), again[:len(first)] == first, len(new_runs), new_runs & old_runs) == (
        True, True, 1, set())


def test_each_entry_names_the_run_the_position_names(loop):
    given_a_run_that_lands(loop)

    loop.run(SPEC)

    assert {each["run"] for each in step_times_of(loop)} == {position_of(loop)["run"]}


def test_a_dry_run_keeps_no_step_time(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)

    loop.run(SPEC, "--dry-run")

    assert not (loop.records() / "step-times.jsonl").exists()


def test_reading_a_run_names_the_step_times_file_in_a_section_of_its_own():
    page = (ROOT / "docs" / "usage" / "the-loop" / "reading-a-run.md").read_text(encoding="utf-8")

    _, heading, rest = page.partition("\n## Step times\n")
    section = rest.split("\n## ", 1)[0]
    assert heading and "`.spec-loop/<spec>/step-times.jsonl`" in section
