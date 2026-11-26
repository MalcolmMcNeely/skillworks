from count.deepenings import filed_within, limit_in, read_strong

FOLDED = "The order intake module: three shallow modules parse one order. Fold them into one."
PRICED = "The pricing adapter: one implementation behind a seam. Make it a plain module."
LEDGER = "`The ledger writer`: it leaks its rows. Hide them behind its interface."


def report(*strong, prose="### Worth exploring\n\nThe cache is shallow.\n"):
    return "## Deepening report\n\n### Strong\n\n" + "".join(
        "- {}\n".format(line) for line in strong) + "\n" + prose


def test_each_strong_line_is_read_in_its_order():
    assert read_strong(report(FOLDED, PRICED)) == [FOLDED, PRICED]


def test_a_strong_list_that_says_none_holds_nothing():
    assert read_strong(report("None")) == []


def test_a_report_with_no_strong_list_is_told_apart_from_an_empty_one():
    assert read_strong("## Deepening report\n\n### Worth exploring\n\n- A guess.\n") is None


def test_the_lines_under_a_later_heading_are_not_strong():
    assert read_strong(report(FOLDED, prose="### Over the limit\n\n- " + LEDGER + "\n")) == [FOLDED]


def test_a_list_within_the_limit_is_filed_whole():
    assert filed_within([FOLDED, PRICED], 3) == ([FOLDED, PRICED], [])


def test_a_list_longer_than_the_limit_files_only_its_first_lines():
    assert filed_within([FOLDED, PRICED, LEDGER], 2) == ([FOLDED, PRICED], [LEDGER])


def test_the_limit_is_read_from_the_yaml_block_at_the_end():
    assert limit_in("# Deepening check\n\n```yaml\nlimit: 9\n```\n\n```yaml\nlimit: 3\n```\n") == 3


def test_a_file_whose_block_names_no_whole_limit_holds_none():
    assert limit_in("```yaml\nlimit: many\n```\n") is None
    assert limit_in("```yaml\nenabled: true\n```\n") is None
    assert limit_in("No block at all.\n") is None
