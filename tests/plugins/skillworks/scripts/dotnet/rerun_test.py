# A stand-in Runner and hand-written TRX files, so no case needs dotnet on the machine.

import io

from dotnet import rerun
from runner import Ran

COMMAND = ["dotnet", "test", "tests/Shop.Api.Tests/Shop.Api.Tests.csproj", "--no-build",
           "--logger", "trx;LogFileName=Shop.Api.Tests.trx",
           "--results-directory", "tests/Shop.Api.Tests/TestResults"]

TRX = "tests/Shop.Api.Tests/TestResults/Shop.Api.Tests.trx"


class Runner:
    def __init__(self, status=0):
        self.status = status
        self.ran = []

    def run(self, args, where=None, env=None, stdin=None):
        self.ran.append(list(args))
        return Ran(self.status, "dotnet said this\n", "")


def trx(root, results):
    rows, definitions = [], []
    for index, (class_name, method, display, outcome) in enumerate(results):
        rows.append('    <UnitTestResult testId="id-{0}" testName="{1}" outcome="{2}" />'
                    .format(index, display, outcome))
        definitions.append('    <UnitTest name="{1}" id="id-{0}">\n'
                           '      <TestMethod className="{2}" name="{3}" />\n'
                           '    </UnitTest>'.format(index, display, class_name, method))
    file = root / TRX
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('<?xml version="1.0" encoding="utf-8"?>\n'
                    '<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">\n'
                    '  <Results>\n{}\n  </Results>\n'
                    '  <TestDefinitions>\n{}\n  </TestDefinitions>\n'
                    '</TestRun>\n'.format("\n".join(rows), "\n".join(definitions)), encoding="utf-8-sig")


def rerun_in(root, runner):
    out, err = io.StringIO(), io.StringIO()
    status = rerun.main([TRX, "--"] + COMMAND, out, err, runner, root)
    return status, out.getvalue(), err.getvalue()


def test_only_the_tests_that_went_red_run_again_through_a_filter(tmp_path):
    trx(tmp_path, [
        ("Shop.Api.Tests.CartTests", "Checkout", "Shop.Api.Tests.CartTests.Checkout", "Failed"),
        ("Shop.Api.Tests.CartTests", "Empty", "Shop.Api.Tests.CartTests.Empty", "Passed"),
        ("Shop.Api.Tests.PriceTests", "Rounds", "Shop.Api.Tests.PriceTests.Rounds(value: 2.5)", "Failed"),
        ("Shop.Api.Tests.PriceTests", "Rounds", "Shop.Api.Tests.PriceTests.Rounds(value: 3.5)", "Failed"),
    ])
    runner = Runner()

    rerun_in(tmp_path, runner)

    assert runner.ran == [COMMAND + [
        "--filter",
        "FullyQualifiedName=Shop.Api.Tests.CartTests.Checkout|FullyQualifiedName=Shop.Api.Tests.PriceTests.Rounds"]]


def test_a_test_name_that_holds_a_filter_mark_is_written_so_the_filter_reads_it_as_a_name(tmp_path):
    trx(tmp_path, [("Shop.Api.Tests.Generic`1", "Holds!", "Shop.Api.Tests.Generic`1.Holds!", "Failed")])
    runner = Runner()

    rerun_in(tmp_path, runner)

    assert runner.ran[0][-1] == r"FullyQualifiedName=Shop.Api.Tests.Generic`1.Holds\!"


def test_the_rerun_answers_with_the_status_and_output_of_the_tests_it_ran(tmp_path):
    trx(tmp_path, [("Shop.Api.Tests.CartTests", "Checkout", "Shop.Api.Tests.CartTests.Checkout", "Failed")])

    status, out, _ = rerun_in(tmp_path, Runner(status=1))

    assert (status, "dotnet said this" in out) == (1, True)


def test_a_missing_results_file_runs_the_whole_command(tmp_path):
    runner = Runner()

    rerun_in(tmp_path, runner)

    assert runner.ran == [COMMAND]


def test_a_results_file_with_no_red_test_runs_the_whole_command(tmp_path):
    trx(tmp_path, [("Shop.Api.Tests.CartTests", "Checkout", "Shop.Api.Tests.CartTests.Checkout", "Passed")])
    runner = Runner()

    rerun_in(tmp_path, runner)

    assert runner.ran == [COMMAND]


def test_a_results_file_that_is_not_xml_runs_the_whole_command(tmp_path):
    (tmp_path / TRX).parent.mkdir(parents=True)
    (tmp_path / TRX).write_text("half a file", encoding="utf-8")
    runner = Runner()

    rerun_in(tmp_path, runner)

    assert runner.ran == [COMMAND]


MTP_COMMAND = ["dotnet", "test", "--project", "tests/Shop.Api.Tests/Shop.Api.Tests.csproj", "--no-build",
               "--results-directory", "tests/Shop.Api.Tests/TestResults", "--",
               "--report-xunit-trx", "--report-xunit-trx-filename", "Shop.Api.Tests.trx"]


def mtp_rerun_in(root, runner, command=MTP_COMMAND):
    out, err = io.StringIO(), io.StringIO()
    status = rerun.main(["--mtp", TRX, "--"] + command, out, err, runner, root)
    return status, out.getvalue(), err.getvalue()


def test_under_mtp_each_red_test_runs_again_through_a_filter_method_after_the_double_dash(tmp_path):
    trx(tmp_path, [
        ("Shop.Api.Tests.CartTests", "Checkout", "Shop.Api.Tests.CartTests.Checkout", "Failed"),
        ("Shop.Api.Tests.CartTests", "Empty", "Shop.Api.Tests.CartTests.Empty", "Passed"),
        ("Shop.Api.Tests.PriceTests", "Rounds", "Shop.Api.Tests.PriceTests.Rounds(value: 2.5)", "Failed"),
        ("Shop.Api.Tests.PriceTests", "Rounds", "Shop.Api.Tests.PriceTests.Rounds(value: 3.5)", "Failed"),
    ])
    runner = Runner()

    mtp_rerun_in(tmp_path, runner)

    assert runner.ran == [MTP_COMMAND + ["--filter-method", "Shop.Api.Tests.CartTests.Checkout",
                                         "--filter-method", "Shop.Api.Tests.PriceTests.Rounds"]]


def test_under_mtp_a_missing_results_file_runs_the_whole_command(tmp_path):
    runner = Runner()

    mtp_rerun_in(tmp_path, runner)

    assert runner.ran == [MTP_COMMAND]


def test_under_mtp_a_results_file_with_no_red_test_runs_the_whole_command(tmp_path):
    trx(tmp_path, [("Shop.Api.Tests.CartTests", "Checkout", "Shop.Api.Tests.CartTests.Checkout", "Passed")])
    runner = Runner()

    mtp_rerun_in(tmp_path, runner)

    assert runner.ran == [MTP_COMMAND]


MTP_COMMAND_WITH_NO_DOUBLE_DASH = ["dotnet", "test", "--project", "tests/Shop.Api.Tests/Shop.Api.Tests.csproj",
                                   "--no-build", "--results-directory", "tests/Shop.Api.Tests/TestResults"]


def test_under_mtp_a_command_with_no_double_dash_gets_one_so_the_filter_reaches_the_test_app(tmp_path):
    trx(tmp_path, [
        ("Shop.Api.Tests.CartTests", "Checkout", "Shop.Api.Tests.CartTests.Checkout", "Failed"),
        ("Shop.Api.Tests.PriceTests", "Rounds", "Shop.Api.Tests.PriceTests.Rounds", "Failed"),
    ])
    runner = Runner()

    mtp_rerun_in(tmp_path, runner, MTP_COMMAND_WITH_NO_DOUBLE_DASH)

    assert runner.ran == [MTP_COMMAND_WITH_NO_DOUBLE_DASH + ["--", "--filter-method", "Shop.Api.Tests.CartTests.Checkout",
                                                             "--filter-method", "Shop.Api.Tests.PriceTests.Rounds"]]


def test_under_mtp_a_command_with_no_double_dash_and_no_red_test_runs_as_given(tmp_path):
    trx(tmp_path, [("Shop.Api.Tests.CartTests", "Checkout", "Shop.Api.Tests.CartTests.Checkout", "Passed")])
    runner = Runner()

    mtp_rerun_in(tmp_path, runner, MTP_COMMAND_WITH_NO_DOUBLE_DASH)

    assert runner.ran == [MTP_COMMAND_WITH_NO_DOUBLE_DASH]


def test_a_rerun_with_no_command_is_turned_down(tmp_path):
    out, err = io.StringIO(), io.StringIO()

    status = rerun.main([TRX], out, err, Runner(), tmp_path)

    assert (status, "usage" in err.getvalue()) == (2, True)
