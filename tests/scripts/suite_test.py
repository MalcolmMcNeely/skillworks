#
# The shared suite, run against a checkout made of the markers it looks for.

from suite import Suite


def given_a_solution(tree):
    (tree / "Skillworks.slnx").write_text("<Solution />", encoding="utf-8")


def given_script_tests(tree):
    (tree / "tests" / "scripts").mkdir(parents=True)


def given_node_tests(tree):
    scripts = tree / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "hook.test.mjs").write_text("", encoding="utf-8")


def given_a_front_end(tree):
    web = tree / "src" / "Skillworks.Studio.Web"
    web.mkdir(parents=True)
    (web / "package.json").write_text("{}", encoding="utf-8")
    return web


def given_the_front_end_is_installed(tree):
    (tree / "src" / "Skillworks.Studio.Web" / "node_modules").mkdir()


def given_every_check_passes(runner):
    runner.stub("docker")
    runner.stub("dotnet")
    runner.stub("uv")
    runner.stub("node")
    runner.stub("npm")


def test_a_checkout_earns_one_check_for_each_marker_it_holds(tmp_path, runner):
    given_a_solution(tmp_path)
    given_script_tests(tmp_path)
    given_node_tests(tmp_path)
    given_a_front_end(tmp_path)
    given_every_check_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.passed
    assert runner.calls == [
        ["docker", "info"],
        ["npm", "ci"],
        ["dotnet", "test", "Skillworks.slnx"],
        ["uv", "run", "--with", "pytest", "pytest", "tests/scripts"],
        ["node", "--test", "scripts/*.test.mjs"],
        ["npm", "run", "typecheck"],
        ["npm", "run", "lint"],
        ["npm", "test"],
    ]


def test_a_marker_the_checkout_is_short_of_earns_no_check(tmp_path, runner):
    given_a_solution(tmp_path)
    given_every_check_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.passed
    assert runner.built("dotnet test Skillworks.slnx")
    assert not runner.started("uv")
    assert not runner.started("node")
    assert not runner.started("npm")


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
    given_every_check_passes(runner)
    runner.stub("dotnet", says="a test failed", status=1)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.passed
    assert "a test failed" in outcome.said
    assert not runner.built("npm test")


def test_a_run_that_passes_keeps_what_every_check_said(tmp_path, runner):
    given_a_solution(tmp_path)
    given_a_front_end(tmp_path)
    given_every_check_passes(runner)
    runner.stub("dotnet", says="the solution passed")
    runner.stub("npm", says="the front end passed")

    outcome = Suite(runner, tmp_path).run()

    assert outcome.passed
    assert "the solution passed" in outcome.said
    assert "the front end passed" in outcome.said


def test_a_checkout_holding_no_marker_at_all_cannot_pass(tmp_path, runner):
    given_every_check_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.passed
    assert not outcome.ready
    assert "none of the checks" in outcome.said
    assert runner.calls == []


def test_docker_is_asked_before_any_check_runs(tmp_path, runner):
    given_a_solution(tmp_path)
    given_script_tests(tmp_path)
    given_every_check_passes(runner)

    Suite(runner, tmp_path).run()

    assert runner.calls[0] == ["docker", "info"]


def test_a_docker_that_does_not_answer_stops_before_any_check(tmp_path, runner):
    given_a_solution(tmp_path)
    given_every_check_passes(runner)
    runner.stub("docker", says="the daemon is not running", status=1)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert not outcome.passed
    assert "Docker" in outcome.said
    assert "the daemon is not running" in outcome.said
    assert not runner.started("dotnet")


def test_a_checkout_with_no_solution_is_never_asked_about_docker(tmp_path, runner):
    given_script_tests(tmp_path)
    given_every_check_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.passed
    assert not runner.started("docker")


def test_uv_missing_from_the_path_stops_before_any_check(tmp_path, runner):
    given_a_solution(tmp_path)
    given_script_tests(tmp_path)
    given_every_check_passes(runner)
    runner.hide("uv")

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert not outcome.passed
    assert "uv" in outcome.said
    assert not runner.started("dotnet")


def test_a_checkout_with_no_script_tests_needs_no_uv(tmp_path, runner):
    given_a_solution(tmp_path)
    given_every_check_passes(runner)
    runner.hide("uv")

    outcome = Suite(runner, tmp_path).run()

    assert outcome.ready
    assert outcome.passed


def test_node_missing_from_the_path_stops_before_any_check(tmp_path, runner):
    given_a_solution(tmp_path)
    given_node_tests(tmp_path)
    given_every_check_passes(runner)
    runner.hide("node")

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert not outcome.passed
    assert "node" in outcome.said
    assert not runner.started("dotnet")


def test_a_checkout_with_no_node_tests_needs_no_node(tmp_path, runner):
    given_a_solution(tmp_path)
    given_every_check_passes(runner)
    runner.hide("node")

    outcome = Suite(runner, tmp_path).run()

    assert outcome.ready
    assert outcome.passed


def test_a_front_end_that_will_not_install_stops_rather_than_failing(tmp_path, runner):
    given_a_front_end(tmp_path)
    given_every_check_passes(runner)
    runner.refuse("npm ci", says="the registry would not answer")

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert not outcome.passed
    assert "the registry would not answer" in outcome.said
    assert not runner.built("npm test")


def test_a_failing_check_is_a_red_suite_and_not_a_machine_short_of_something(tmp_path, runner):
    given_a_solution(tmp_path)
    given_every_check_passes(runner)
    runner.stub("dotnet", says="a test failed", status=1)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.ready
    assert not outcome.passed


# Reading the output would make a passing machine look broken on the day a runner reworded itself.
def test_a_check_that_fails_naming_docker_is_still_a_red_suite(tmp_path, runner):
    given_a_solution(tmp_path)
    given_every_check_passes(runner)
    runner.stub("dotnet", says="Cannot connect to the Docker daemon", status=1)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.ready
    assert not outcome.passed
