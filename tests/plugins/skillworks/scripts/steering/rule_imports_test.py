from steering.rule_imports import RULES_FOLDER, missing_import


def rules(top, *names):
    folder = top / RULES_FOLDER
    folder.mkdir(parents=True)
    for name in names:
        (folder / name).write_text("# A rule\n", encoding="utf-8", newline="\n")


def claude_md(top, *lines):
    (top / "CLAUDE.md").write_text("# Repo\n\n" + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def test_a_repo_where_every_rule_has_its_import_passes(tmp_path):
    rules(tmp_path, "comments.md", "words.md")
    claude_md(tmp_path, "@docs/agents/rules/comments.md", "@docs/agents/rules/words.md")

    assert missing_import(tmp_path) is None


def test_a_rule_with_no_import_names_the_rule_and_the_line_to_add(tmp_path):
    rules(tmp_path, "comments.md", "words.md")
    claude_md(tmp_path, "@docs/agents/rules/comments.md")

    assert missing_import(tmp_path) == (
        "docs/agents/rules/words.md has no import in CLAUDE.md, so it does not load into a session. "
        "Add this line to CLAUDE.md: @docs/agents/rules/words.md")


def test_a_repo_with_no_rules_folder_passes(tmp_path):
    assert missing_import(tmp_path) is None
