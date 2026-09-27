import ast

from conftest import SCRIPTS
from tracker.reading import listed

ONE_COPY = {"listed", "DRIFT_REPORT"}


def defined_in(tree):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            yield node.name
        if isinstance(node, ast.Assign):
            yield from (target.id for target in node.targets if isinstance(target, ast.Name))


def test_listed_keeps_each_line_and_drops_the_empty_ones():
    assert listed("a\n\nb\n") == ["a", "b"]


def test_listed_finds_nothing_in_nothing():
    assert listed("") == []


def test_each_fact_the_tracker_package_keeps_is_defined_once():
    homes = {}
    for script in SCRIPTS.rglob("*.py"):
        tree = ast.parse(script.read_text(encoding="utf-8"))
        for name in ONE_COPY & set(defined_in(tree)):
            homes.setdefault(name, []).append(script.relative_to(SCRIPTS).as_posix())

    assert homes == {"listed": ["tracker/reading.py"], "DRIFT_REPORT": ["tracker/reading.py"]}
