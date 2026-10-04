# spec-loop-counts reads the folder a real driver run left, so nothing stands in for either.

import shutil

from conftest import ROOT, launch
from spec_loop_test import (A_BLOCKED, A_CHOICE, A_DENIED_COMMAND, A_DEPARTURE, A_HAND_CHECK,
                            ONE_OPEN_TICKET, SPEC, a_denied_command, given_a_session_that_was_denied,
                            given_a_spec_axis_that_says, given_an_axis_that_stops_short,
                            given_sessions_that_report, given_the_tracker_holds, loop)

OPUS = "claude-opus-5-5"
HAIKU = "claude-haiku-4-5-20251001"

LOG_LINES = "\nLog lines: FAIL 0, STOP {stops}, RED 0, ABORT 0\n"


def counted(loop, *args):
    return launch("spec-loop-counts", *args, where=loop.repo.work)


def table(said, title):
    lines = said.split("\n")
    start = lines.index("## " + title)
    rows = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if line.startswith("|") and not line.startswith("|-"):
            rows.append([cell.strip() for cell in line.strip("|").split("|")])
    header, *body = rows
    return [dict(zip(header, row)) for row in body]


def row_of(said, title, key, value):
    return next(row for row in table(said, title) if row[key] == value)


def test_a_nudged_step_shows_its_results_and_the_check_its_nudge_was_for(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_stops_short(
        given_sessions_that_report(loop), "standards", "## Standards. Nothing found.")
    loop.run(SPEC)

    ran = counted(loop, SPEC)

    assert row_of(ran.out, "How steps ended", "Step", "standards") == {
        "Step": "standards", "Results": "2", "Nudges": "axis-reported 1", "Blocked": "0",
        "Departures": "0", "Choices": "0", "Hand checks": "0"}


def test_a_step_counts_each_choice_and_hand_check_its_results_made(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_spec_axis_that_says(given_sessions_that_report(loop), A_CHOICE, A_HAND_CHECK)
    loop.run(SPEC)

    row = row_of(counted(loop, SPEC).out, "How steps ended", "Step", "spec")

    assert (row["Choices"], row["Hand checks"]) == ("1", "1")


def test_a_step_counts_each_departure_its_results_wrote(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_a_spec_axis_that_says(given_sessions_that_report(loop), A_DEPARTURE, A_DEPARTURE)
    loop.run(SPEC)

    assert row_of(counted(loop, SPEC).out, "How steps ended", "Step", "spec")["Departures"] == "2"


def test_a_blocked_build_is_a_blocked_stop_of_the_build(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop).says["implement"] = A_BLOCKED
    loop.run(SPEC)

    assert row_of(counted(loop, SPEC).out, "How steps ended", "Step", "build")["Blocked"] == "1"


def test_a_stop_line_of_the_log_is_counted(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop).says["implement"] = A_BLOCKED
    loop.run(SPEC)

    assert LOG_LINES.format(stops=1) in counted(loop, SPEC).out


def test_a_nudged_step_that_then_passed_is_counted_as_passed(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_stops_short(
        given_sessions_that_report(loop), "standards", "## Standards. Nothing found.")
    loop.run(SPEC)

    assert row_of(counted(loop, SPEC).out, "What a Nudge got", "Step", "standards") == {
        "Step": "standards", "Nudged": "1", "Passed": "1", "Blocked": "0", "Failed": "0"}


def test_a_nudged_step_that_answered_blocked_is_counted_as_blocked(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_stops_short(given_sessions_that_report(loop), "standards", A_BLOCKED)
    loop.run(SPEC)

    assert row_of(counted(loop, SPEC).out, "What a Nudge got", "Step", "standards") == {
        "Step": "standards", "Nudged": "1", "Passed": "0", "Blocked": "1", "Failed": "0"}


def test_a_nudged_step_that_still_failed_after_the_last_nudge_is_counted_as_failed(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_an_axis_that_stops_short(given_sessions_that_report(loop), "standards")
    loop.run(SPEC)

    assert row_of(counted(loop, SPEC).out, "What a Nudge got", "Step", "standards") == {
        "Step": "standards", "Nudged": "1", "Passed": "0", "Blocked": "0", "Failed": "1"}


def test_the_denials_of_a_step_are_counted_by_tool_name(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    given_a_session_that_was_denied(sessions, "review-standards", A_DENIED_COMMAND,
                                    a_denied_command(1),
                                    {"tool_name": "Write", "tool_input": {"file_path": "a"}})
    loop.run(SPEC)

    assert table(counted(loop, SPEC).out, "Denials") == [
        {"Step": "standards", "Results with a Denial": "1", "Denied calls": "Bash 2, Write 1"}]


def test_each_model_a_result_names_is_a_row_of_the_model_table(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.says["implement"] = A_BLOCKED
    sessions.models["implement"] = [OPUS]
    loop.run(SPEC)

    assert table(counted(loop, SPEC).out, "Which model ran") == [{"Model": OPUS, "Results": "1"}]


def test_a_result_that_names_more_than_one_model_is_a_row_of_its_own(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    sessions = given_sessions_that_report(loop)
    sessions.models["implement"] = [OPUS]
    sessions.models["review-standards"] = [OPUS, HAIKU]
    given_an_axis_that_stops_short(sessions, "standards", A_BLOCKED)
    loop.run(SPEC)

    assert row_of(counted(loop, SPEC).out, "Which model ran", "Model", HAIKU + " + " + OPUS)[
        "Results"] == "2"


def test_a_result_that_names_no_model_is_counted_under_none_named(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop).says["implement"] = A_BLOCKED
    loop.run(SPEC)

    assert table(counted(loop, SPEC).out, "Which model ran") == [
        {"Model": "none named", "Results": "1"}]


def test_the_reading_a_run_page_gives_the_command_and_its_four_tables():
    page = (ROOT / "docs/usage/the-loop/reading-a-run.md").read_text(encoding="utf-8")

    assert all(said in page for said in (
        "spec-loop-counts", "## How steps ended", "## What a Nudge got", "## Denials",
        "## Which model ran"))


def test_with_no_spec_number_every_spec_folder_with_a_journal_is_counted_and_no_other(loop):
    given_the_tracker_holds(loop, ONE_OPEN_TICKET)
    given_sessions_that_report(loop).says["implement"] = A_BLOCKED
    loop.run(SPEC)
    records = loop.records().parent
    shutil.copytree(loop.records(), records / "159")
    (records / "160").mkdir()
    shutil.copy(loop.records() / "loop.log", records / "160" / "loop.log")

    assert counted(loop).out.startswith("Specs counted: 158, 159\n")
