from conftest import SEEDS
from steering.readme_surface import readme_surface, readme_surface_of

README = ("## The README\n\n"
          "- **Where it lives:** `docs/START.md`\n"
          "- **The question:** Does this change rename something the README names?\n"
          "- **What to capture:** The exact line that changes.\n")


def test_the_readme_surface_is_found_by_its_heading_and_its_path_comes_from_where_it_lives():
    assert readme_surface("# Surfaces\n\n" + README) == "docs/START.md"


def test_a_readme_heading_inside_a_code_fence_is_not_the_readme_surface():
    fenced = "# Surfaces\n\n```markdown\n" + README + "```\n"

    assert readme_surface(fenced) is None


def test_a_where_it_lives_under_another_surface_is_not_the_readmes():
    text = ("# Surfaces\n\n" + README.replace("- **Where it lives:** `docs/START.md`\n", "")
            + "\n## The user docs\n\n- **Where it lives:** `docs/`\n")

    assert readme_surface(text) == ""


def test_a_surfaces_file_with_no_readme_heading_has_no_readme_surface():
    assert readme_surface("# Surfaces\n\n## The user docs\n\n- **Where it lives:** `docs/`\n") is None


def test_the_seeds_readme_surface_lives_at_the_readme(tmp_path):
    (tmp_path / "docs" / "agents").mkdir(parents=True)
    (tmp_path / "docs" / "agents" / "surfaces.md").write_text(
        (SEEDS / "surfaces.md").read_text(encoding="utf-8"), encoding="utf-8")

    assert readme_surface_of(tmp_path) == "README.md"


def test_a_repo_with_no_surfaces_file_has_no_readme_surface(tmp_path):
    assert readme_surface_of(tmp_path) is None
