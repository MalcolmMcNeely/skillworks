# The spec's items read from its text alone, so each fault in its shape costs one string.

import pytest

from conftest import PLUGIN
from count.items import read_items

TO_SPEC = PLUGIN / "skills" / "to-spec" / "SKILL.md"

STORIES = "## User Stories\n\n1. As a team member, I want a count.\n2. As a team member, I want a stop.\n"

DECISIONS = "## Implementation Decisions\n\n1. The reader is pure.\n2. The driver runs it first.\n"

SURFACES = "## Surfaces\n\n- **The user docs** (`docs/usage/`): the shape is described.\n"

TESTING = "## Testing Decisions\n\n1. A test reads the text.\n2. Another reads the log.\n"


def spec(*sections):
    return "## Problem Statement\n\nWords.\n\n" + "\n".join(sections) + "\n## Out of Scope\n\nNone.\n"


def names(items):
    return [item.name for item in items.every()]


def test_a_counted_spec_names_its_stories_decisions_and_surfaces():
    items = read_items(spec(STORIES, DECISIONS, SURFACES))

    assert items.faults == []
    assert names(items) == ["S1", "S2", "D1", "D2", "The user docs"]


def test_each_item_keeps_its_own_text():
    items = read_items(spec(STORIES, DECISIONS, SURFACES))

    assert items.stories[1].text == "As a team member, I want a stop."
    assert items.surfaces[0].text == "**The user docs** (`docs/usage/`): the shape is described."


def test_the_items_narrowed_to_some_names_keep_those_alone_in_the_specs_order():
    items = read_items(spec(STORIES, DECISIONS, SURFACES)).only(["The user docs", "S2", "D9"])

    assert names(items) == ["S2", "The user docs"]
    assert items.stories[0].text == "As a team member, I want a stop."


def test_an_item_that_runs_over_several_lines_keeps_them_all():
    wrapped = "## User Stories\n\n1. As a team member,\n   I want a count.\n2. Another.\n"

    items = read_items(spec(wrapped, DECISIONS, SURFACES))

    assert items.faults == []
    assert items.stories[0].text == "As a team member, I want a count."


def test_testing_decisions_are_not_counted():
    items = read_items(spec(STORIES, DECISIONS, SURFACES, TESTING))

    assert items.faults == []
    assert names(items) == ["S1", "S2", "D1", "D2", "The user docs"]


@pytest.mark.parametrize("said", ["None", "None.", "None\n"])
def test_a_surfaces_section_that_says_none_has_no_surface_items(said):
    items = read_items(spec(STORIES, DECISIONS, "## Surfaces\n\n" + said + "\n"))

    assert items.faults == []
    assert items.surfaces == []


@pytest.mark.parametrize("heading", ["## User Stories", "## Implementation Decisions", "## Surfaces"])
def test_a_missing_heading_is_named(heading):
    sections = [section for section in (STORIES, DECISIONS, SURFACES)
                if not section.startswith(heading + "\n")]

    items = read_items(spec(*sections))

    assert items.faults == ["the spec has no {} heading".format(heading)]


def test_a_heading_inside_a_fence_is_not_the_section():
    fenced = "## Further Notes\n\n```markdown\n## User Stories\n\n1. An example.\n```\n"

    items = read_items(spec(DECISIONS, SURFACES, fenced))

    assert items.faults == ["the spec has no ## User Stories heading"]


def test_a_section_of_bullets_is_a_section_with_no_numbered_list():
    bullets = "## Implementation Decisions\n\n- The reader is pure.\n- The driver runs it first.\n"

    items = read_items(spec(STORIES, bullets, SURFACES))

    assert items.faults == ["## Implementation Decisions holds no numbered list"]


def test_a_skipped_number_is_named_with_the_numbers_either_side():
    skipped = "## User Stories\n\n1. One.\n2. Two.\n4. Four.\n"

    items = read_items(spec(skipped, DECISIONS, SURFACES))

    assert items.faults == ["## User Stories skips 3: it goes from 2 to 4"]


def test_a_list_that_starts_after_1_skips_1():
    late = "## User Stories\n\n2. Two.\n3. Three.\n"

    items = read_items(spec(late, DECISIONS, SURFACES))

    assert items.faults == ["## User Stories starts at 2, not 1"]


def test_a_repeated_number_is_named():
    repeated = "## Implementation Decisions\n\n1. One.\n2. Two.\n2. Two again.\n3. Three.\n"

    items = read_items(spec(STORIES, repeated, SURFACES))

    assert items.faults == ["## Implementation Decisions repeats 2"]


def test_a_nested_list_is_part_of_its_item_and_not_counted():
    nested = "## User Stories\n\n1. One:\n   1. a detail\n   2. another\n2. Two.\n"

    items = read_items(spec(nested, DECISIONS, SURFACES))

    assert items.faults == []
    assert names(items)[:2] == ["S1", "S2"]


def test_a_surface_item_with_no_bold_name_is_named():
    plain = "## Surfaces\n\n- **The user docs**: described.\n- The README: says so.\n"

    items = read_items(spec(STORIES, DECISIONS, plain))

    assert items.faults == ["a Surface item under ## Surfaces opens with no bold name: "
                            "- The README: says so."]


def test_a_surfaces_section_with_no_items_that_does_not_say_none_is_named():
    prose = "## Surfaces\n\nThe user docs change.\n"

    items = read_items(spec(STORIES, DECISIONS, prose))

    assert items.faults == ["## Surfaces holds no Surface item and does not say None"]


def test_a_surface_named_twice_is_named():
    twice = "## Surfaces\n\n- **The user docs**: one.\n- **The user docs**: two.\n"

    items = read_items(spec(STORIES, DECISIONS, twice))

    assert items.faults == ["## Surfaces names The user docs twice"]


def test_every_fault_in_the_spec_is_named_at_once():
    items = read_items(spec("## User Stories\n\n1. One.\n3. Three.\n", SURFACES))

    assert items.faults == ["## User Stories skips 2: it goes from 1 to 3",
                            "the spec has no ## Implementation Decisions heading"]


def test_a_spec_with_windows_line_endings_reads_the_same():
    items = read_items(spec(STORIES, DECISIONS, SURFACES).replace("\n", "\r\n"))

    assert items.faults == []
    assert names(items) == ["S1", "S2", "D1", "D2", "The user docs"]


# The template is what every spec starts from, so the reader reads it as a spec.
def test_the_to_spec_template_writes_every_counted_section_in_the_shape_the_reader_counts():
    template = TO_SPEC.read_text(encoding="utf-8").split("<spec-template>", 1)[1].split(
        "</spec-template>", 1)[0]

    items = read_items(template)

    assert items.faults == []
    assert [item.name for item in items.stories] == ["S1", "S2"]
    assert [item.name for item in items.decisions] == ["D1", "D2"]
    assert [item.name for item in items.surfaces] == ["The user docs"]
