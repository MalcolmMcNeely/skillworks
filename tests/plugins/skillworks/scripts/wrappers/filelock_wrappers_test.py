from conftest import PLUGIN
from filelock_wrappers import wrappers_without_filelock


def wrapper(folder, name, uv_line):
    path = folder / name
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + uv_line + "\n", encoding="utf-8")


def test_a_wrapper_that_asks_uv_for_filelock_keeps_the_rule(tmp_path):
    wrapper(tmp_path, "tracker-show",
            'exec uv run --no-project --quiet --with "filelock>=3.16" python -m tracker.show "$here" "$@"')

    assert wrappers_without_filelock(tmp_path) == []


def test_every_wrapper_that_does_not_ask_uv_for_filelock_is_named(tmp_path):
    wrapper(tmp_path, "tracker-show", 'exec uv run --no-project --quiet python -m tracker.show "$here" "$@"')
    wrapper(tmp_path, "spec-loop", 'exec uv run --no-project --quiet "$plugin/scripts/spec_loop.py" "$@"')
    wrapper(tmp_path, "land-ticket",
            'exec uv run --no-project --quiet --with "filelock>=3.16" "$plugin/scripts/land_ticket.py" "$@"')

    assert wrappers_without_filelock(tmp_path) == ["spec-loop", "tracker-show"]


def test_a_wrapper_that_asks_for_filelock_with_no_version_breaks_the_rule(tmp_path):
    wrapper(tmp_path, "spec-commits",
            'exec uv run --no-project --quiet --with filelock python -m tracker.spec_commits "$here" "$@"')

    assert wrappers_without_filelock(tmp_path) == ["spec-commits"]


def test_every_wrapper_in_the_plugin_asks_uv_for_filelock():
    assert wrappers_without_filelock(PLUGIN / "bin") == []
