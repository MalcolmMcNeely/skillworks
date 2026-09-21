# The only set that needs either program installed, so `conftest.py` keeps it out of the fast run.
# Neither program may do what its line asks, and `real_binaries.py` says how each one is stopped.

import pytest

from real_binaries import (CLAUDE, GH, GH_FIELDS, NOWHERE, Line, listed, report,
                           usage_of)

# A line the driver stops building is the drift this set catches, so a count moves only on purpose.
GH_LINES = 13
GH_FIELD_LINES = 2
CLAUDE_LINES = 3


# A table gone short leaves the cases below silent rather than red, so it is counted before them.
def test_the_driver_builds_every_line_it_reaches_a_program_with():
    assert len(GH) == GH_LINES, "the driver built these gh lines:\n" + listed(GH)
    assert len(GH_FIELDS) == GH_FIELD_LINES, (
        "the driver built these gh lines with a --json field:\n" + listed(GH_FIELDS))
    assert len(CLAUDE) == CLAUDE_LINES, (
        "the driver built these claude lines:\n" + listed(CLAUDE))


@pytest.mark.parametrize("line", GH, ids=Line.whole)
def test_the_real_gh_accepts_a_line_the_driver_builds(line):
    # Arrange
    asked = line.helped()

    # Act
    ran = line.started(asked)

    # Assert
    assert ran.status == 0, "gh turned the line down:\n" + report(asked, ran)
    usage = usage_of(ran.out)
    assert usage, "gh printed no usage, so what it accepted cannot be read back:\n" + ran.out
    assert "<command>" not in usage, (
        "gh fell back to the group's help, so it has no such subcommand: " + usage)


@pytest.mark.parametrize("line", GH_FIELDS, ids=Line.whole)
def test_the_real_gh_still_has_the_json_field_the_driver_asks_for(line):
    # Arrange
    wanted = line.field()
    asked = line.without_the_field()

    # Act
    ran = line.started(asked)

    # Assert
    said = ran.out + ran.err
    assert ran.status != 0, "gh accepted a field it cannot have, so it lists none:\n" + said
    assert "\n  " + wanted + "\n" in said, (
        "gh no longer offers the " + wanted + " field:\n" + said)


@pytest.mark.parametrize("line", CLAUDE, ids=Line.flags)
def test_the_real_claude_accepts_a_line_the_driver_builds(line):
    # Arrange
    asked = line.resumed_from_nowhere()

    # Act
    ran = line.started(asked)

    # Assert
    assert ran.status != 0, "claude ran the line for real:\n" + report(asked, ran)
    assert NOWHERE in ran.out + ran.err, (
        "claude stopped short of the session lookup, so it turned part of the line "
        "down:\n" + report(asked, ran))
