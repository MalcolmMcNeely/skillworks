from count.findings import enabled_in, read_findings

PARSED = ("`src/orders/intake.py`, `parse_lines`, reuse: it splits each line by hand. Call the CSV "
          "reader.")
TAXED = "`src/orders/totals.py`, efficiency: the tax rate is read for every line. Read it once."


def report(*findings):
    return "## Simplify report\n\n### Findings\n\n" + "".join(
        "- {}\n".format(line) for line in findings)


def test_each_finding_is_read_in_its_order():
    assert read_findings(report(PARSED, TAXED)) == [PARSED, TAXED]


def test_a_findings_list_that_says_none_holds_nothing():
    assert read_findings(report("None")) == []


def test_a_report_with_no_findings_list_is_told_apart_from_an_empty_one():
    assert read_findings("## Simplify report\n\nThe code is as simple as it gets.\n") is None


def settings(enabled):
    return "## Settings\n\n```yaml\nenabled: {}\n```\n".format(enabled)


def test_enabled_false_turns_the_check_off():
    assert enabled_in(settings("false")) is False


def test_an_enabled_that_is_neither_true_nor_false_is_not_read():
    assert enabled_in(settings("maybe")) is None
