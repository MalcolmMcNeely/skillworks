import json
import subprocess
from pathlib import Path

import pytest

import statements
from runner import Subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

KEEP = "docs/adr/0001-keep-one-clock.md"
SPLIT = "docs/adr/0002-split-the-stores.md"


def git(where, *args):
    done = subprocess.run(["git", "-C", Path(where).as_posix()] + [str(a) for a in args],
                          capture_output=True, encoding="utf-8", errors="replace")
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


def commit(top, message, files):
    for path, text in files.items():
        file = Path(top) / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8", newline="\n")
    git(top, "add", "-A")
    git(top, "commit", "--quiet", "-m", message)
    return git(top, "rev-parse", "HEAD").strip()


@pytest.fixture(scope="module")
def history(tmp_path_factory):
    top = tmp_path_factory.mktemp("statements") / "source"
    git(top.parent, "init", "--quiet", "--initial-branch=main", top.as_posix())
    for name, value in (("user.name", "Test"), ("user.email", "test@example.invalid"),
                        ("commit.gpgsign", "false"), ("core.autocrlf", "false")):
        git(top, "config", name, value)
    clock = commit(top, "Read one Clock", {"src/clock.py": "CLOCK = 1\n"})
    commit(top, "ADR: Keep one Clock", {KEEP: "# Keep one Clock\n"})
    commit(top, "ADR: Split the stores", {SPLIT: "# Split the stores\n"})
    pin = git(top, "rev-parse", "HEAD").strip()
    later = commit(top, "After the pin", {"src/later.py": "LATER = 1\n"})
    return top, pin, clock, later


def statement_file(clock, **changed):
    said = {"split-on": "a hash", "title": "A title", "commits": [clock],
            "statements": [{"kind": "decision", "says": "Studio reads one Clock."},
                           {"kind": "reason", "says": "A test holds it still."}]}
    said.update(changed)
    return said


def given_statements(folder, files):
    folder.mkdir(parents=True, exist_ok=True)
    for stem, said in files.items():
        (folder / (stem + ".json")).write_text(json.dumps(said), encoding="utf-8")
    return folder


def problems_in(history, folder):
    top, pin, _, _ = history
    return statements.problems(Subprocess(), top, pin, folder)


def test_a_held_out_record_with_no_statement_file_is_named(history, tmp_path):
    _, _, clock, _ = history
    folder = given_statements(tmp_path / "statements", {"0001-keep-one-clock": statement_file(clock)})

    assert problems_in(history, folder) == [
        "{} has no Statement file 0002-split-the-stores.json".format(SPLIT)]


def with_split(clock, split):
    return {"0001-keep-one-clock": statement_file(clock), "0002-split-the-stores": split}


def test_a_statement_of_a_kind_not_in_the_four_is_named(history, tmp_path):
    _, _, clock, _ = history
    odd = statement_file(clock, statements=[{"kind": "decision", "says": "Two stores."},
                                            {"kind": "fact", "says": "Spans are many."}])
    folder = given_statements(tmp_path / "statements", with_split(clock, odd))

    assert problems_in(history, folder) == [
        "0002-split-the-stores.json holds a Statement of the kind fact, and a kind is one of "
        "decision, reason, rejected or status"]


def test_a_file_with_no_decision_statement_is_named(history, tmp_path):
    _, _, clock, _ = history
    reasons = statement_file(clock, statements=[{"kind": "reason", "says": "Spans are many."}])
    folder = given_statements(tmp_path / "statements", with_split(clock, reasons))

    assert problems_in(history, folder) == ["0002-split-the-stores.json holds no decision Statement"]


def test_a_statement_file_for_a_record_not_held_out_is_named(history, tmp_path):
    _, _, clock, _ = history
    files = dict(with_split(clock, statement_file(clock)), **{"0003-keep-two-clocks": statement_file(clock)})
    folder = given_statements(tmp_path / "statements", files)

    assert problems_in(history, folder) == [
        "0003-keep-two-clocks.json names docs/adr/0003-keep-two-clocks.md, which is not held out at the pin"]


def test_a_commit_after_the_pin_or_not_in_the_repo_is_named(history, tmp_path):
    _, _, clock, later = history
    never = "0" * 40
    folder = given_statements(tmp_path / "statements",
                              with_split(clock, statement_file(clock, commits=[clock, later, never])))

    assert problems_in(history, folder) == [
        "0002-split-the-stores.json names the commit {}, which is not in this repo at or before the pin".format(c)
        for c in (later, never)]


@pytest.fixture(scope="module")
def pinned():
    return json.loads((HERE / "pin.json").read_text(encoding="utf-8"))


@pytest.mark.this_repo
def test_every_held_out_record_at_the_pin_has_a_sound_statement_file(pinned):
    assert statements.problems(Subprocess(), ROOT, pinned["commit"]) == []


@pytest.mark.this_repo
def test_every_statement_file_is_split_on_the_records_the_pin_stores(pinned):
    split_on = {json.loads(file.read_text(encoding="utf-8"))["split-on"] for file in statements.FOLDER.glob("*.json")}

    assert split_on == {pinned["records"]}
