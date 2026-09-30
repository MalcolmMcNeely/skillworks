from conftest import ROOT
from doc_links import broken_links


def writing(root, path, text):
    page = root / path
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(text, encoding="utf-8")


def test_a_link_to_a_page_that_is_not_there_is_broken(tmp_path):
    writing(tmp_path, "docs/usage/the-loop.md", "# The Dev loop\n\nSee [the Tracker](tracker.md).\n")

    assert broken_links(tmp_path) == ["docs/usage/the-loop.md links tracker.md"]


def test_a_link_to_a_heading_that_is_not_on_its_page_is_broken(tmp_path):
    writing(tmp_path, "docs/usage/tracker.md", "# The Tracker\n\n## The `.specs/` folder\n")
    writing(tmp_path, "docs/usage/the-loop.md",
            "# The Dev loop\n\n## Rebasing and Landing: the Turn\n\n"
            "[a](tracker.md#the-specs-folder) [b](tracker.md#the-gap-round) "
            "[c](#rebasing-and-landing-the-turn) [d](#the-dev-loops)\n")

    assert broken_links(tmp_path) == ["docs/usage/the-loop.md links tracker.md#the-gap-round",
                                      "docs/usage/the-loop.md links #the-dev-loops"]


def test_a_heading_inside_a_code_fence_is_no_target(tmp_path):
    writing(tmp_path, "docs/usage/the-loop.md",
            "# The Dev loop\n\n```markdown\n## Name report\n```\n\n~~~~\n## Verdicts\n~~~~\n\n"
            "[a](#name-report) [b](#verdicts)\n")

    assert broken_links(tmp_path) == ["docs/usage/the-loop.md links #name-report",
                                      "docs/usage/the-loop.md links #verdicts"]


def test_a_link_inside_a_code_fence_is_not_checked(tmp_path):
    writing(tmp_path, "docs/usage/the-loop.md",
            "# The Dev loop\n\n```\nSee [the spec](spec.md).\n```\n")

    assert broken_links(tmp_path) == []


def test_a_link_to_a_web_address_is_not_checked(tmp_path):
    writing(tmp_path, "docs/usage/the-loop.md",
            "# The Dev loop\n\n[issues](https://github.com/o/r/issues#nowhere) [mail](mailto:a@b.c)\n")

    assert broken_links(tmp_path) == []


def test_a_page_in_the_loop_s_folder_with_no_link_from_the_loop_page_is_lost(tmp_path):
    writing(tmp_path, "docs/usage/the-loop.md",
            "# The Dev loop\n\n[the Tracker](the-loop/tracker.md)\n\n```\n[stops](the-loop/stops.md)\n```\n")
    writing(tmp_path, "docs/usage/the-loop/tracker.md", "# The Tracker\n\n[back](../the-loop.md)\n")
    writing(tmp_path, "docs/usage/the-loop/stops.md", "# Stops\n\n[back](../the-loop.md)\n")
    writing(tmp_path, "docs/usage/setup.md", "# Setup\n\n[stops](the-loop/stops.md)\n")

    assert broken_links(tmp_path) == ["docs/usage/the-loop/stops.md has no link from docs/usage/the-loop.md"]


def test_a_link_from_a_top_level_page_into_the_user_docs_is_checked(tmp_path):
    writing(tmp_path, "docs/usage/the-loop.md", "# The Dev loop\n")
    writing(tmp_path, "README.md",
            "# Skillworks\n\n[loop](docs/usage/the-loop.md#the-tracker) [gone](./docs/usage/gone.md) "
            "[studio](docs/studio/running.md)\n")

    assert broken_links(tmp_path) == ["README.md links docs/usage/the-loop.md#the-tracker",
                                      "README.md links ./docs/usage/gone.md"]


def test_the_real_user_docs_hold_loop_pages_for_the_link_check_to_walk():
    folder = ROOT / "docs" / "usage" / "the-loop"

    assert {folder / "target-branch.md", folder / "tracker.md", folder / "the-grill.md",
            folder / "tickets.md", folder / "steps.md",
            folder / "landing.md", folder / "drift-check.md",
            folder / "name-check.md", folder / "full-run.md"} <= set(folder.glob("*.md"))


def test_every_link_in_the_user_docs_has_a_target():
    assert broken_links(ROOT) == []
