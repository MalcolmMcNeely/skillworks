# The Suite reads no test runner output, so the red tests come from the TRX file the check's last run wrote.

import os
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runner import Subprocess

USAGE = "usage: suite-dotnet-rerun [--mtp] <trx file> -- <the check's command>...\n"

MTP = "--mtp"

RED = {"failed", "error", "timeout", "aborted"}

# The marks that dotnet test's --filter reads as syntax and not as part of a name.
FILTER_MARKS = set("\\()&|=!~")


def local_name(element):
    return element.tag.rsplit("}", 1)[-1]


def escaped(name):
    return "".join("\\" + mark if mark in FILTER_MARKS else mark for mark in name)


# A missing or half-written TRX runs the whole command, so no red test is lost.
def red_tests(trx):
    try:
        root = ElementTree.fromstring(trx.read_text(encoding="utf-8-sig"))
    except (OSError, ElementTree.ParseError):
        return []
    red_ids = {element.get("testId") for element in root.iter()
               if local_name(element) == "UnitTestResult" and (element.get("outcome") or "").lower() in RED}
    names = []
    for test in root.iter():
        if local_name(test) != "UnitTest" or test.get("id") not in red_ids:
            continue
        for method in test.iter():
            if local_name(method) == "TestMethod":
                # An older logger writes the class with its assembly after a comma, which no filter matches.
                name = "{}.{}".format(method.get("className", "").split(",")[0].strip(), method.get("name", ""))
                if name not in names:
                    names.append(name)
    return names


def command_for(trx, command, mtp):
    red = red_tests(trx)
    if not red:
        return command
    # Only the test app reads --filter-method, and dotnet test hands it only what follows a --.
    if mtp:
        opening = [] if "--" in command else ["--"]
        return command + opening + [word for name in red for word in ("--filter-method", name)]
    return command + ["--filter", "|".join("FullyQualifiedName=" + escaped(name) for name in red)]


def arguments(argv):
    mtp = bool(argv) and argv[0] == MTP
    if mtp:
        argv = argv[1:]
    if len(argv) < 3 or argv[1] != "--":
        return None
    return argv[0], argv[2:], mtp


def main(argv, out, err, runner, where=None):
    where = Path(where or os.getcwd())
    given = arguments(list(argv))
    if given is None:
        err.write(USAGE)
        return 2
    trx, command, mtp = given
    ran = runner.run(command_for(where / trx, command, mtp), str(where))
    out.write(ran.out)
    err.write(ran.err)
    return ran.status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr, Subprocess()))
