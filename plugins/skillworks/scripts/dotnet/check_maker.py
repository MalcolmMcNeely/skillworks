# Files are read as text and no dotnet command runs, so it answers at once, needs no SDK and builds nothing.

import json
import os
import re
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

USAGE = "usage: suite-dotnet-checks <solution> [--skip <pattern>]... [--trx-from-build] [-- <flag>...]\n"

TRX_FROM_BUILD = "--trx-from-build"

# Matched whole, so a library that names xunit.v3.assert or xunit.v3.extensibility.core is not a test project.
TEST_PROJECT_PACKAGES = {"microsoft.net.test.sdk", "xunit.v3"}

PREBUILD = "build"

RERUN = "suite-dotnet-rerun"

XUNIT_V3 = "xunit.v3"

# Matched in the text, so a global.json that dotnet reads with comments or trailing commas still picks MTP.
MTP_RUNNER = re.compile(r'"runner"\s*:\s*"Microsoft\.Testing\.Platform"', re.IGNORECASE)

# A solution folder has a line of its own in a .sln, and only a project's path ends in a project file.
SLN_PROJECT = re.compile(r'^Project\("[^"]*"\)\s*=\s*"[^"]*",\s*"([^"]+\.[A-Za-z]+proj)"', re.MULTILINE)


class Refused(Exception):
    pass


def local_name(element):
    return element.tag.rsplit("}", 1)[-1]


def parsed_xml(path):
    try:
        return ElementTree.fromstring(path.read_text(encoding="utf-8-sig"))
    except OSError:
        raise Refused("{} is not there, or cannot be read.".format(path))
    except ElementTree.ParseError as fault:
        raise Refused("{} is not XML the Check maker can read: {}.".format(path, fault))


# A solution written on Windows spells its paths with backslashes, which mean nothing to a path elsewhere.
def joined(folder, written):
    return Path(os.path.normpath(folder / written.replace("\\", "/")))


def solution_projects(solution):
    if not solution.is_file():
        raise Refused("{} is not there.".format(solution))
    kind = solution.suffix.lower()
    if kind == ".slnx":
        return [joined(solution.parent, element.get("Path"))
                for element in parsed_xml(solution).iter()
                if local_name(element) == "Project" and element.get("Path")]
    if kind == ".sln":
        text = solution.read_text(encoding="utf-8-sig")
        return [joined(solution.parent, path) for path in SLN_PROJECT.findall(text)]
    if kind == ".slnf":
        try:
            named = json.loads(solution.read_text(encoding="utf-8-sig"))["solution"]
            base = joined(solution.parent, named["path"]).parent
            return [joined(base, path) for path in named["projects"]]
        except (ValueError, KeyError, TypeError) as fault:
            raise Refused("{} is not a solution filter the Check maker can read: {}.".format(solution, fault))
    raise Refused("{} is not a .sln, .slnx or .slnf file.".format(solution))


# Conditions are not worked out, so a conditioned value counts as unset; as in MSBuild, the last one set wins.
def is_test_project(root):
    stated = None
    for group in root:
        if local_name(group) != "PropertyGroup" or group.get("Condition") is not None:
            continue
        for element in group:
            if local_name(element) == "IsTestProject" and element.get("Condition") is None:
                value = (element.text or "").strip().lower()
                stated = {"true": True, "false": False}.get(value, stated)
    return stated


class Project:
    def __init__(self, path):
        self.path = path
        root = parsed_xml(path)
        self.references = [joined(path.parent, element.get("Include"))
                           for element in root.iter()
                           if local_name(element) == "ProjectReference" and element.get("Include")]
        packages = {(element.get("Include") or "").lower()
                    for element in root.iter() if local_name(element) == "PackageReference"}
        stated = is_test_project(root)
        self.is_test = bool(packages & TEST_PROJECT_PACKAGES) if stated is None else stated
        self.is_xunit_v3 = XUNIT_V3 in packages

    @property
    def name(self):
        return self.path.stem


def same(path):
    return os.path.normcase(str(path))


class Graph:
    def __init__(self, paths):
        self.read = {}
        self.listed = [self.project(path) for path in paths]

    def project(self, path):
        if same(path) not in self.read:
            if not path.is_file():
                raise Refused("{} is named in the solution and is not there.".format(path))
            self.read[same(path)] = Project(path)
        return self.read[same(path)]

    # A reference to a file that is not there is left for dotnet build to report, as it reads no further.
    def reached_from(self, start):
        reached, waiting = {}, [start.path]
        while waiting:
            path = waiting.pop()
            if same(path) in reached or not path.is_file():
                continue
            reached[same(path)] = self.project(path)
            waiting.extend(reached[same(path)].references)
        return reached.values()


# Only `*` is a wildcard, so a project name with brackets or a question mark matches as written.
def skip_matcher(patterns):
    compiled = [re.compile(".*".join(re.escape(part) for part in pattern.split("*"))) for pattern in patterns]
    return lambda name: any(pattern.fullmatch(name) for pattern in compiled)


# The Suite reads a check's folder and ignores from the repo root, wherever the Check maker ran.
def repo_root(where):
    for folder in [where] + list(where.parents):
        if (folder / ".git").exists():
            return folder
    return where


def from_root(root, path):
    try:
        return Path(os.path.relpath(path, root)).as_posix()
    except ValueError:
        raise Refused("{} is outside the repo at {}.".format(path, root))


def holds(folder, inner):
    return folder == "." or inner == folder or inner.startswith(folder + "/")


# A folder that holds a reached project, or the root itself, is never ignored, so no input of the check is lost.
def ignores_for(root, graph, reached):
    reached_folders = {from_root(root, project.path.parent) for project in reached}
    unreached = {from_root(root, project.path.parent) for project in graph.listed
                 if same(project.path) not in {same(each.path) for each in reached}}
    return sorted(folder for folder in unreached
                  if not any(holds(folder, inner) for inner in reached_folders))


# Every made check runs from the repo root, so dotnet reads the global.json there or above it, never one further down.
def picks_mtp(root):
    for folder in [root] + list(root.parents):
        file = folder / "global.json"
        if file.is_file():
            try:
                return bool(MTP_RUNNER.search(file.read_text(encoding="utf-8-sig")))
            except OSError:
                raise Refused("{} cannot be read.".format(file))
    return False


def vstest_check(project, results, trx, flags, trx_from_build):
    logger = [] if trx_from_build else ["--logger", "trx;LogFileName=" + trx]
    command = ["dotnet", "test", project, "--no-build"] + logger + ["--results-directory", results] + flags
    return command, [RERUN, results + "/" + trx, "--"] + command


# --results-directory is read by dotnet, and everything after -- by the test app.
# The test app refuses a one-value option given twice, so a build that names the file gets no second name.
def mtp_check(project, results, trx, flags, trx_from_build):
    for_app = ([] if trx_from_build else ["--report-xunit-trx", "--report-xunit-trx-filename", trx]) + flags
    command = ["dotnet", "test", "--project", project, "--no-build", "--results-directory", results]
    if for_app:
        command += ["--"] + for_app
    return command, [RERUN, "--mtp", results + "/" + trx, "--"] + command


def made_checks(where, solution_given, skips, flags, trx_from_build):
    root = repo_root(where)
    solution = joined(where, solution_given)
    graph = Graph(solution_projects(solution))
    skipped = skip_matcher(skips)
    mtp = picks_mtp(root)
    checks = []
    for project in graph.listed:
        if not project.is_test or skipped(project.name):
            continue
        if mtp and not project.is_xunit_v3:
            raise Refused("{} does not name xunit.v3, and only xUnit v3 is supported under "
                          "Microsoft.Testing.Platform.".format(from_root(root, project.path)))
        # A results folder of its own, so the Rerun reads this project's red tests and no other's.
        results = from_root(root, project.path.parent) + "/TestResults"
        trx = "{}.trx".format(project.name)
        command, rerun = (mtp_check if mtp else vstest_check)(
            from_root(root, project.path), results, trx, flags, trx_from_build)
        checks.append({
            "command": command,
            "folder": ".",
            "prebuild": PREBUILD,
            "ignores": ignores_for(root, graph, graph.reached_from(project)),
            "rerun": rerun,
        })
    return {
        "prebuilds": {PREBUILD: {"command": ["dotnet", "build", from_root(root, solution)], "folder": "."}},
        "checks": checks,
    }


def arguments(argv):
    solution, skips, flags, trx_from_build, given = None, [], [], False, list(argv)
    while given:
        word = given.pop(0)
        if word == "--":
            flags, given = given, []
        elif word == "--skip" and given:
            skips.append(given.pop(0))
        elif word == TRX_FROM_BUILD:
            trx_from_build = True
        elif solution is None and not word.startswith("--"):
            solution = word
        else:
            raise Refused(USAGE.rstrip("\n"))
    if solution is None:
        raise Refused(USAGE.rstrip("\n"))
    return solution, skips, flags, trx_from_build


def main(argv, out, err, where=None):
    where = Path(where or os.getcwd()).resolve()
    try:
        solution, skips, flags, trx_from_build = arguments(argv)
        printed = made_checks(where, solution, skips, flags, trx_from_build)
    except Refused as refused:
        err.write(str(refused) + "\n")
        return 1
    out.write(json.dumps(printed, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))
