# Driven through main on a solution of fixture files, so no case needs dotnet on the machine but the real_dotnet ones.

import io
import json
import xml.etree.ElementTree as ElementTree
from typing import NamedTuple

import pytest

from dotnet import check_maker, rerun
from runner import Subprocess

TEST_SDK = '<PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.14.1" />'


def project(root, path, references=(), test=False, packages=()):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    items = [TEST_SDK] if test else []
    items += ['<PackageReference Include="{}" Version="3.0.0" />'.format(package) for package in packages]
    items += ['<ProjectReference Include="{}" />'.format(reference) for reference in references]
    file.write_text('<Project Sdk="Microsoft.NET.Sdk">\n  <ItemGroup>\n    {}\n  </ItemGroup>\n'
                    '</Project>\n'.format("\n    ".join(items)), encoding="utf-8")


def slnx(root, name, paths):
    lines = ['    <Project Path="{}" />'.format(path) for path in paths]
    (root / name).write_text('<Solution>\n  <Folder Name="/all/">\n{}\n  </Folder>\n</Solution>\n'
                             .format("\n".join(lines)), encoding="utf-8")


def sln(root, name, paths):
    lines = ['Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{}", "{}", "{{0}}"\nEndProject'
             .format(path.rsplit("/", 1)[-1].rsplit(".", 1)[0], path.replace("/", "\\")) for path in paths]
    folder = ('Project("{2150E333-8FDC-42A3-9474-1A3956D46DE8}") = "tests", "tests", "{1}"\n'
              'EndProject')
    (root / name).write_text("Microsoft Visual Studio Solution File, Format Version 12.00\n{}\n{}\n"
                             .format(folder, "\n".join(lines)), encoding="utf-8")


def slnf(root, name, solution, paths):
    (root / name).write_text(json.dumps({"solution": {"path": solution, "projects": [
        path.replace("/", "\\") for path in paths]}}), encoding="utf-8")


def made(root, *argv):
    out, err = io.StringIO(), io.StringIO()
    status = check_maker.main(list(argv), out, err, root)
    assert status == 0, err.getvalue()
    return json.loads(out.getvalue())


def projects_checked(printed):
    return [check["command"][2] for check in printed["checks"]]


def check_for(printed, path):
    return next(check for check in printed["checks"] if check["command"][2] == path)


@pytest.fixture
def shop(tmp_path):
    project(tmp_path, "src/Shop.Core/Shop.Core.csproj")
    project(tmp_path, "src/Shop.Api/Shop.Api.csproj", [r"..\Shop.Core\Shop.Core.csproj"])
    project(tmp_path, "src/Shop.Tool/Shop.Tool.csproj")
    project(tmp_path, "tests/Shop.Api.Tests/Shop.Api.Tests.csproj",
            [r"..\..\src\Shop.Api\Shop.Api.csproj"], test=True)
    project(tmp_path, "tests/Shop.Tool.Tests/Shop.Tool.Tests.csproj",
            [r"..\..\src\Shop.Tool\Shop.Tool.csproj"], test=True)
    return tmp_path


SHOP = ["src/Shop.Core/Shop.Core.csproj", "src/Shop.Api/Shop.Api.csproj", "src/Shop.Tool/Shop.Tool.csproj",
        "tests/Shop.Api.Tests/Shop.Api.Tests.csproj", "tests/Shop.Tool.Tests/Shop.Tool.Tests.csproj"]


def test_it_prints_one_prebuild_that_builds_the_solution_and_one_check_per_test_project(shop):
    slnx(shop, "Shop.slnx", SHOP)

    printed = made(shop, "Shop.slnx")

    assert printed == {
        "prebuilds": {"build": {"command": ["dotnet", "build", "Shop.slnx"], "folder": "."}},
        "checks": [
            {"command": ["dotnet", "test", "tests/Shop.Api.Tests/Shop.Api.Tests.csproj", "--no-build",
                         "--logger", "trx;LogFileName=Shop.Api.Tests.trx",
                         "--results-directory", "tests/Shop.Api.Tests/TestResults"],
             "folder": ".", "prebuild": "build",
             "ignores": ["src/Shop.Tool", "tests/Shop.Tool.Tests"],
             "rerun": ["suite-dotnet-rerun", "tests/Shop.Api.Tests/TestResults/Shop.Api.Tests.trx", "--",
                       "dotnet", "test", "tests/Shop.Api.Tests/Shop.Api.Tests.csproj", "--no-build",
                       "--logger", "trx;LogFileName=Shop.Api.Tests.trx",
                       "--results-directory", "tests/Shop.Api.Tests/TestResults"]},
            {"command": ["dotnet", "test", "tests/Shop.Tool.Tests/Shop.Tool.Tests.csproj", "--no-build",
                         "--logger", "trx;LogFileName=Shop.Tool.Tests.trx",
                         "--results-directory", "tests/Shop.Tool.Tests/TestResults"],
             "folder": ".", "prebuild": "build",
             "ignores": ["src/Shop.Api", "src/Shop.Core", "tests/Shop.Api.Tests"],
             "rerun": ["suite-dotnet-rerun", "tests/Shop.Tool.Tests/TestResults/Shop.Tool.Tests.trx", "--",
                       "dotnet", "test", "tests/Shop.Tool.Tests/Shop.Tool.Tests.csproj", "--no-build",
                       "--logger", "trx;LogFileName=Shop.Tool.Tests.trx",
                       "--results-directory", "tests/Shop.Tool.Tests/TestResults"]},
        ],
    }


def test_each_check_carries_a_rerun_that_reads_the_results_file_its_command_writes(shop):
    slnx(shop, "Shop.slnx", SHOP)

    check = check_for(made(shop, "Shop.slnx"), "tests/Shop.Api.Tests/Shop.Api.Tests.csproj")

    assert check["rerun"] == ["suite-dotnet-rerun", "tests/Shop.Api.Tests/TestResults/Shop.Api.Tests.trx", "--",
                              "dotnet", "test", "tests/Shop.Api.Tests/Shop.Api.Tests.csproj", "--no-build",
                              "--logger", "trx;LogFileName=Shop.Api.Tests.trx",
                              "--results-directory", "tests/Shop.Api.Tests/TestResults"]


@pytest.mark.parametrize("solution, write", [
    ("Shop.slnx", lambda root: slnx(root, "Shop.slnx", SHOP)),
    ("Shop.sln", lambda root: sln(root, "Shop.sln", SHOP)),
    ("Shop.slnf", lambda root: (slnx(root, "Shop.slnx", SHOP), slnf(root, "Shop.slnf", "Shop.slnx", SHOP))),
], ids=["slnx", "sln", "slnf"])
def test_every_solution_format_gives_the_same_test_projects(shop, solution, write):
    write(shop)

    assert projects_checked(made(shop, solution)) == ["tests/Shop.Api.Tests/Shop.Api.Tests.csproj",
                                            "tests/Shop.Tool.Tests/Shop.Tool.Tests.csproj"]


def test_a_solution_filter_leaves_out_the_projects_it_does_not_name(shop):
    slnx(shop, "Shop.slnx", SHOP)
    slnf(shop, "Api.slnf", "Shop.slnx", SHOP[:2] + SHOP[3:4])

    printed = made(shop, "Api.slnf")

    assert (projects_checked(printed), printed["prebuilds"]["build"]["command"]) == (
        ["tests/Shop.Api.Tests/Shop.Api.Tests.csproj"], ["dotnet", "build", "Api.slnf"])


def test_a_skip_pattern_leaves_a_matching_test_project_with_no_check(shop):
    project(shop, "tests/Shop.E2E.Tests/Shop.E2E.Tests.csproj", [r"..\..\src\Shop.Api\Shop.Api.csproj"],
            test=True)
    slnx(shop, "Shop.slnx", SHOP + ["tests/Shop.E2E.Tests/Shop.E2E.Tests.csproj"])

    printed = made(shop, "Shop.slnx", "--skip", "*.E2E.Tests", "--skip", "Shop.Tool.*")

    assert projects_checked(printed) == ["tests/Shop.Api.Tests/Shop.Api.Tests.csproj"]


def test_flags_after_a_double_dash_end_each_command_and_the_command_inside_each_rerun(shop):
    slnx(shop, "Shop.slnx", SHOP)

    check = check_for(made(shop, "Shop.slnx", "--", "--blame-crash", "--blame-crash-dump-type", "mini"),
                      "tests/Shop.Api.Tests/Shop.Api.Tests.csproj")

    assert (check["command"], check["rerun"]) == (
        ["dotnet", "test", "tests/Shop.Api.Tests/Shop.Api.Tests.csproj", "--no-build",
         "--logger", "trx;LogFileName=Shop.Api.Tests.trx",
         "--results-directory", "tests/Shop.Api.Tests/TestResults",
         "--blame-crash", "--blame-crash-dump-type", "mini"],
        ["suite-dotnet-rerun", "tests/Shop.Api.Tests/TestResults/Shop.Api.Tests.trx", "--",
         "dotnet", "test", "tests/Shop.Api.Tests/Shop.Api.Tests.csproj", "--no-build",
         "--logger", "trx;LogFileName=Shop.Api.Tests.trx",
         "--results-directory", "tests/Shop.Api.Tests/TestResults",
         "--blame-crash", "--blame-crash-dump-type", "mini"])


def test_flags_after_a_double_dash_work_beside_a_skip_pattern(shop):
    slnx(shop, "Shop.slnx", SHOP)

    printed = made(shop, "Shop.slnx", "--skip", "Shop.Tool.*", "--", "--blame-crash", "--skip", "x")

    assert [check["command"][-3:] for check in printed["checks"]] == [["--blame-crash", "--skip", "x"]]


@pytest.mark.parametrize("package", ["xunit.v3", "XUnit.V3"])
def test_a_project_that_names_only_xunit_v3_gets_a_check(tmp_path, package):
    project(tmp_path, "tests/Shop.Tests/Shop.Tests.csproj", packages=[package])
    slnx(tmp_path, "Shop.slnx", ["tests/Shop.Tests/Shop.Tests.csproj"])

    assert projects_checked(made(tmp_path, "Shop.slnx")) == ["tests/Shop.Tests/Shop.Tests.csproj"]


@pytest.mark.parametrize("package", ["xunit.v3.assert", "xunit.v3.extensibility.core"])
def test_a_library_that_names_an_xunit_v3_library_gets_no_check(tmp_path, package):
    project(tmp_path, "tests/Shop.Fixtures/Shop.Fixtures.csproj", packages=[package])
    slnx(tmp_path, "Shop.slnx", ["tests/Shop.Fixtures/Shop.Fixtures.csproj"])

    assert projects_checked(made(tmp_path, "Shop.slnx")) == []


MTP_GLOBAL_JSON = '{\n  "sdk": {"version": "10.0.100"},\n  "test": {"runner": "Microsoft.Testing.Platform"}\n}\n'


def global_json(folder, text=MTP_GLOBAL_JSON):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "global.json").write_text(text, encoding="utf-8")


@pytest.fixture
def xunit_shop(tmp_path):
    (tmp_path / ".git").mkdir()
    project(tmp_path, "src/Shop.Api/Shop.Api.csproj")
    project(tmp_path, "tests/Shop.Api.Tests/Shop.Api.Tests.csproj", [r"..\..\src\Shop.Api\Shop.Api.csproj"],
            test=True, packages=["xunit.v3"])
    slnx(tmp_path, "Shop.slnx", ["src/Shop.Api/Shop.Api.csproj", "tests/Shop.Api.Tests/Shop.Api.Tests.csproj"])
    return tmp_path


MTP_COMMAND = ["dotnet", "test", "--project", "tests/Shop.Api.Tests/Shop.Api.Tests.csproj", "--no-build",
               "--results-directory", "tests/Shop.Api.Tests/TestResults", "--",
               "--report-xunit-trx", "--report-xunit-trx-filename", "Shop.Api.Tests.trx"]

VSTEST_COMMAND = ["dotnet", "test", "tests/Shop.Api.Tests/Shop.Api.Tests.csproj", "--no-build",
                  "--logger", "trx;LogFileName=Shop.Api.Tests.trx",
                  "--results-directory", "tests/Shop.Api.Tests/TestResults"]

VSTEST_CHECKS = {
    "prebuilds": {"build": {"command": ["dotnet", "build", "Shop.slnx"], "folder": "."}},
    "checks": [{"command": VSTEST_COMMAND, "folder": ".", "prebuild": "build", "ignores": [],
                "rerun": ["suite-dotnet-rerun", "tests/Shop.Api.Tests/TestResults/Shop.Api.Tests.trx", "--"]
                + VSTEST_COMMAND}],
}


def test_a_repo_that_picks_mtp_in_global_json_gets_checks_and_reruns_in_the_mtp_form(xunit_shop):
    global_json(xunit_shop)

    printed = made(xunit_shop, "Shop.slnx")

    assert printed == {
        "prebuilds": {"build": {"command": ["dotnet", "build", "Shop.slnx"], "folder": "."}},
        "checks": [{"command": MTP_COMMAND, "folder": ".", "prebuild": "build", "ignores": [],
                    "rerun": ["suite-dotnet-rerun", "--mtp", "tests/Shop.Api.Tests/TestResults/Shop.Api.Tests.trx",
                              "--"] + MTP_COMMAND}],
    }


@pytest.mark.parametrize("text", [
    None,
    '{"sdk": {"version": "10.0.100"}}',
    '{"test": {"runner": "VSTest"}}',
], ids=["no global.json", "no runner", "VSTest"])
def test_a_repo_that_does_not_pick_mtp_gets_checks_in_the_vstest_form(xunit_shop, text):
    if text is not None:
        global_json(xunit_shop, text)

    assert made(xunit_shop, "Shop.slnx") == VSTEST_CHECKS


def test_a_global_json_above_the_repo_root_picks_the_runner(tmp_path):
    global_json(tmp_path)
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    project(repo, "tests/Shop.Api.Tests/Shop.Api.Tests.csproj", test=True, packages=["xunit.v3"])
    slnx(repo, "Shop.slnx", ["tests/Shop.Api.Tests/Shop.Api.Tests.csproj"])

    assert made(repo, "Shop.slnx")["checks"][0]["command"] == MTP_COMMAND


def test_the_global_json_nearest_the_repo_root_wins_over_one_above_it(tmp_path):
    global_json(tmp_path)
    repo = tmp_path / "repo"
    global_json(repo, '{"test": {"runner": "VSTest"}}')
    (repo / ".git").mkdir(parents=True)
    project(repo, "tests/Shop.Api.Tests/Shop.Api.Tests.csproj", test=True, packages=["xunit.v3"])
    slnx(repo, "Shop.slnx", ["tests/Shop.Api.Tests/Shop.Api.Tests.csproj"])

    assert made(repo, "Shop.slnx")["checks"][0]["command"] == VSTEST_COMMAND


def test_a_global_json_only_beside_a_solution_below_the_repo_root_is_not_read(tmp_path):
    (tmp_path / ".git").mkdir()
    sub = tmp_path / "app"
    global_json(sub)
    project(sub, "tests/Lib.Tests/Lib.Tests.csproj", test=True, packages=["xunit.v3"])
    slnx(sub, "App.slnx", ["tests/Lib.Tests/Lib.Tests.csproj"])

    assert made(sub, "App.slnx")["checks"][0]["command"] == [
        "dotnet", "test", "app/tests/Lib.Tests/Lib.Tests.csproj", "--no-build",
        "--logger", "trx;LogFileName=Lib.Tests.trx", "--results-directory", "app/tests/Lib.Tests/TestResults"]


def test_under_mtp_a_test_project_that_does_not_name_xunit_v3_is_refused_by_name(xunit_shop):
    global_json(xunit_shop)
    project(xunit_shop, "tests/Shop.NUnit.Tests/Shop.NUnit.Tests.csproj", test=True, packages=["NUnit"])
    slnx(xunit_shop, "Shop.slnx", ["tests/Shop.Api.Tests/Shop.Api.Tests.csproj",
                                   "tests/Shop.NUnit.Tests/Shop.NUnit.Tests.csproj"])
    out, err = io.StringIO(), io.StringIO()

    status = check_maker.main(["Shop.slnx"], out, err, xunit_shop)

    assert (status, out.getvalue(), "Shop.NUnit.Tests" in err.getvalue(),
            "only xUnit v3 is supported under Microsoft.Testing.Platform" in err.getvalue()) == (1, "", True, True)


def test_under_mtp_extra_flags_follow_the_trx_flags_in_the_command_and_the_rerun(xunit_shop):
    global_json(xunit_shop)

    check = made(xunit_shop, "Shop.slnx", "--", "--timeout", "5m")["checks"][0]

    assert (check["command"], check["rerun"]) == (
        MTP_COMMAND + ["--timeout", "5m"],
        ["suite-dotnet-rerun", "--mtp", "tests/Shop.Api.Tests/TestResults/Shop.Api.Tests.trx", "--"]
        + MTP_COMMAND + ["--timeout", "5m"])


def test_a_project_reached_only_through_another_project_is_not_ignored(shop):
    slnx(shop, "Shop.slnx", SHOP)

    ignores = check_for(made(shop, "Shop.slnx"), "tests/Shop.Api.Tests/Shop.Api.Tests.csproj")["ignores"]

    assert "src/Shop.Core" not in ignores


def test_a_project_at_the_root_is_never_ignored_so_files_outside_every_project_stay_inputs(shop):
    project(shop, "Shop.Build.csproj")
    slnx(shop, "Shop.slnx", SHOP + ["Shop.Build.csproj"])

    ignores = check_for(made(shop, "Shop.slnx"), "tests/Shop.Api.Tests/Shop.Api.Tests.csproj")["ignores"]

    assert ignores == ["src/Shop.Tool", "tests/Shop.Tool.Tests"]


def test_a_project_folder_that_holds_a_reached_project_is_not_ignored(shop):
    project(shop, "src/Shop.Tool/Shop.Tool.Plugins/Shop.Tool.Plugins.csproj")
    project(shop, "tests/Shop.Plugins.Tests/Shop.Plugins.Tests.csproj",
            [r"..\..\src\Shop.Tool\Shop.Tool.Plugins\Shop.Tool.Plugins.csproj"], test=True)
    slnx(shop, "Shop.slnx", SHOP + ["src/Shop.Tool/Shop.Tool.Plugins/Shop.Tool.Plugins.csproj",
                                    "tests/Shop.Plugins.Tests/Shop.Plugins.Tests.csproj"])

    ignores = check_for(made(shop, "Shop.slnx"), "tests/Shop.Plugins.Tests/Shop.Plugins.Tests.csproj")["ignores"]

    assert "src/Shop.Tool" not in ignores


def test_paths_are_from_the_repo_root_when_the_solution_sits_below_it(shop):
    (shop / ".git").mkdir()
    sub = shop / "app"
    project(sub, "src/Lib/Lib.csproj")
    project(sub, "tests/Lib.Tests/Lib.Tests.csproj", [r"..\..\src\Lib\Lib.csproj"], test=True)
    project(sub, "src/Other/Other.csproj")
    slnx(sub, "App.slnx", ["src/Lib/Lib.csproj", "tests/Lib.Tests/Lib.Tests.csproj", "src/Other/Other.csproj"])

    printed = made(sub, "App.slnx")

    assert (printed["prebuilds"]["build"]["command"], printed["checks"][0]["command"][2],
            printed["checks"][0]["ignores"]) == (
        ["dotnet", "build", "app/App.slnx"], "app/tests/Lib.Tests/Lib.Tests.csproj", ["app/src/Other"])


def test_a_solution_that_is_not_there_is_named_and_makes_no_checks(tmp_path):
    out, err = io.StringIO(), io.StringIO()

    status = check_maker.main(["Missing.slnx"], out, err, tmp_path)

    assert (status, out.getvalue(), "Missing.slnx" in err.getvalue()) == (1, "", True)


def test_a_project_file_the_solution_names_and_that_is_not_there_is_named(tmp_path):
    slnx(tmp_path, "Shop.slnx", ["src/Gone/Gone.csproj"])
    out, err = io.StringIO(), io.StringIO()

    status = check_maker.main(["Shop.slnx"], out, err, tmp_path)

    assert (status, "Gone.csproj" in err.getvalue()) == (1, True)


# Only the runner, because a pinned SDK version fails on a machine that has another feature band.
MTP_RUNNER_ONLY = '{\n  "test": {"runner": "Microsoft.Testing.Platform"}\n}\n'

REAL_XUNIT_V3_PROJECT = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <OutputType>Exe</OutputType>
    <UseMicrosoftTestingPlatformRunner>true</UseMicrosoftTestingPlatformRunner>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="xunit.v3" Version="3.2.0" />
  </ItemGroup>
</Project>
"""

REAL_TESTS = """namespace Shop.Tests;

public sealed class Checkout
{
    [Xunit.Fact]
    public void Green() => Xunit.Assert.True(true);

    [Xunit.Fact]
    public void Red() => Xunit.Assert.True(false);
}
"""


def trx_outcomes(trx):
    root = ElementTree.fromstring(trx.read_text(encoding="utf-8-sig"))
    return sorted((element.get("testName"), element.get("outcome")) for element in root.iter()
                  if check_maker.local_name(element) == "UnitTestResult")


class RealRun(NamedTuple):
    check_status: int
    after_check: list
    after_rerun: list
    said: str


# One build serves every case, because a NuGet restore and a build take most of a minute.
@pytest.fixture(scope="module")
def real_mtp_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("real-mtp")
    (root / ".git").mkdir()
    global_json(root, MTP_RUNNER_ONLY)
    tests = root / "tests" / "Shop.Tests"
    tests.mkdir(parents=True)
    (tests / "Shop.Tests.csproj").write_text(REAL_XUNIT_V3_PROJECT, encoding="utf-8")
    (tests / "Checkout.cs").write_text(REAL_TESTS, encoding="utf-8")
    slnx(root, "Shop.slnx", ["tests/Shop.Tests/Shop.Tests.csproj"])
    printed = made(root, "Shop.slnx")
    check = printed["checks"][0]
    real = Subprocess()

    built = real.run(printed["prebuilds"][check["prebuild"]]["command"], str(root))
    assert built.status == 0, built.out + built.err
    ran = real.run(check["command"], str(root))
    # The Rerun names its TRX file as the word after its own flags and before the check's --.
    trx = root / check["rerun"][check["rerun"].index("--") - 1]
    after_check = trx_outcomes(trx) if trx.is_file() else []
    out, err = io.StringIO(), io.StringIO()
    rerun.main(check["rerun"][1:], out, err, real, root)
    after_rerun = trx_outcomes(trx) if trx.is_file() else []
    return RealRun(ran.status, after_check, after_rerun, ran.out + ran.err + out.getvalue() + err.getvalue())


@pytest.mark.real_dotnet
def test_a_check_in_the_mtp_form_writes_its_trx_file_where_its_rerun_reads_it(real_mtp_run):
    assert (real_mtp_run.check_status != 0, real_mtp_run.after_check) == (True, [
        ("Shop.Tests.Checkout.Green", "Passed"), ("Shop.Tests.Checkout.Red", "Failed")]), real_mtp_run.said


@pytest.mark.real_dotnet
def test_a_rerun_in_the_mtp_form_runs_only_the_red_test(real_mtp_run):
    assert real_mtp_run.after_rerun == [("Shop.Tests.Checkout.Red", "Failed")], real_mtp_run.said
