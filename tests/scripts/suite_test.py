#
# The shared suite, run against a checkout made of the markers it looks for.

from suite import Suite


def given_a_solution(tree):
    (tree / "Skillworks.slnx").write_text("<Solution />", encoding="utf-8")


def given_script_tests(tree):
    (tree / "tests" / "scripts").mkdir(parents=True)


def given_a_front_end(tree):
    web = tree / "src" / "Skillworks.Studio.Web"
    web.mkdir(parents=True)
    (web / "package.json").write_text("{}", encoding="utf-8")
    return web


def given_the_front_end_is_installed(tree):
    (tree / "src" / "Skillworks.Studio.Web" / "node_modules").mkdir()


def given_every_check_passes(runner):
    runner.stub("dotnet")
    runner.stub("uv")
    runner.stub("npm")


def test_a_checkout_earns_one_check_for_each_marker_it_holds(tmp_path, runner):
    given_a_solution(tmp_path)
    given_script_tests(tmp_path)
    given_a_front_end(tmp_path)
    given_every_check_passes(runner)

    passed, _ = Suite(runner, tmp_path).run()

    assert passed
    assert runner.calls == [
        ["dotnet", "test", "Skillworks.slnx"],
        ["uv", "run", "--with", "pytest", "pytest", "tests/scripts"],
        ["npm", "ci"],
        ["npm", "run", "typecheck"],
        ["npm", "run", "lint"],
        ["npm", "test"],
    ]


def test_a_marker_the_checkout_is_short_of_earns_no_check(tmp_path, runner):
    given_a_solution(tmp_path)
    given_every_check_passes(runner)

    passed, _ = Suite(runner, tmp_path).run()

    assert passed
    assert runner.calls == [["dotnet", "test", "Skillworks.slnx"]]


def test_the_front_end_checks_run_in_the_front_end_folder(tmp_path, runner):
    given_a_solution(tmp_path)
    web = given_a_front_end(tmp_path)
    given_every_check_passes(runner)

    Suite(runner, tmp_path).run()

    where = {call.args[0]: call.where for call in runner.made}
    assert where["dotnet"] == tmp_path.as_posix()
    assert where["npm"] == web.as_posix()


def test_a_front_end_with_nothing_installed_is_installed_first(tmp_path, runner):
    given_a_front_end(tmp_path)
    given_every_check_passes(runner)

    Suite(runner, tmp_path).run()

    assert runner.calls[0] == ["npm", "ci"]


def test_a_front_end_already_installed_is_not_installed_again(tmp_path, runner):
    given_a_front_end(tmp_path)
    given_the_front_end_is_installed(tmp_path)
    given_every_check_passes(runner)

    Suite(runner, tmp_path).run()

    assert not runner.built("npm ci")


def test_the_first_failing_check_stops_the_run(tmp_path, runner):
    given_a_solution(tmp_path)
    given_a_front_end(tmp_path)
    runner.stub("dotnet", says="a test failed", status=1)
    runner.stub("npm")

    passed, said = Suite(runner, tmp_path).run()

    assert not passed
    assert "a test failed" in said
    assert not runner.started("npm")


def test_a_run_that_passes_keeps_what_every_check_said(tmp_path, runner):
    given_a_solution(tmp_path)
    given_a_front_end(tmp_path)
    runner.stub("dotnet", says="the solution passed")
    runner.stub("npm", says="the front end passed")

    passed, said = Suite(runner, tmp_path).run()

    assert passed
    assert "the solution passed" in said
    assert "the front end passed" in said


def test_a_checkout_holding_no_marker_at_all_cannot_pass(tmp_path, runner):
    given_every_check_passes(runner)

    passed, said = Suite(runner, tmp_path).run()

    assert not passed
    assert "none of the checks" in said
    assert runner.calls == []
