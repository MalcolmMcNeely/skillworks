# Files are read as text and no dotnet command runs, so it answers at once, needs no SDK and builds nothing.

import json
import os
import re
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

USAGE = "usage: suite-dotnet-checks <solution> [--skip <pattern>]...\n"

TEST_SDK_PACKAGES = {"microsoft.net.test.sdk"}

PREBUILD = "build"

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


class Project:
    def __init__(self, path):
        self.path = path
        root = parsed_xml(path)
        self.references = [joined(path.parent, element.get("Include"))
                           for element in root.iter()
                           if local_name(element) == "ProjectReference" and element.get("Include")]
        self.is_test = any(local_name(element) == "PackageReference"
                           and (element.get("Include") or "").lower() in TEST_SDK_PACKAGES
                           for element in root.iter())

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


def made_checks(where, solution_given, skips):
    root = repo_root(where)
    solution = joined(where, solution_given)
    graph = Graph(solution_projects(solution))
    skipped = skip_matcher(skips)
    checks = []
    for project in graph.listed:
        if not project.is_test or skipped(project.name):
            continue
        folder = from_root(root, project.path.parent)
        # A results folder of its own, so the Rerun reads this project's red tests and no other's.
        checks.append({
            "command": ["dotnet", "test", from_root(root, project.path), "--no-build",
                        "--logger", "trx;LogFileName={}.trx".format(project.name),
                        "--results-directory", folder + "/TestResults"],
            "folder": ".",
            "prebuild": PREBUILD,
            "ignores": ignores_for(root, graph, graph.reached_from(project)),
        })
    return {
        "prebuilds": {PREBUILD: {"command": ["dotnet", "build", from_root(root, solution)], "folder": "."}},
        "checks": checks,
    }


def arguments(argv):
    solution, skips, given = None, [], list(argv)
    while given:
        word = given.pop(0)
        if word == "--skip" and given:
            skips.append(given.pop(0))
        elif solution is None and not word.startswith("--"):
            solution = word
        else:
            raise Refused(USAGE.rstrip("\n"))
    if solution is None:
        raise Refused(USAGE.rstrip("\n"))
    return solution, skips


def main(argv, out, err, where=None):
    where = Path(where or os.getcwd()).resolve()
    try:
        solution, skips = arguments(argv)
        printed = made_checks(where, solution, skips)
    except Refused as refused:
        err.write(str(refused) + "\n")
        return 1
    out.write(json.dumps(printed, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))
