#
# The programs are made up, so a case proves the Suite runs what the file names and nothing else.

import json

from conftest import ROOT, check, write_suite
from suite import SUITE_FILE, Suite


def given_every_program_passes(runner):
    for name in ("compile", "prove", "lint", "ping", "install"):
        runner.stub(name)


def given_this_repo_s_programs_pass(runner):
    for name in ("docker", "dotnet", "uv", "node", "npm"):
        runner.stub(name)


def given_a_suite_file_reading(tree, text):
    write_suite(tree)
    (tree / SUITE_FILE).write_text(text, encoding="utf-8")


def test_the_checks_run_in_the_order_the_file_names_them(tmp_path, runner):
    write_suite(tmp_path, check("compile", "all"), check("prove", "all"), check("lint"))
    given_every_program_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.passed
    assert outcome.ready
    assert runner.calls == [["compile", "all"], ["prove", "all"], ["lint"]]


def test_each_check_runs_in_its_own_folder_under_the_repo_root(tmp_path, runner):
    write_suite(tmp_path, check("compile"), check("lint", folder="web/app"))
    given_every_program_passes(runner)

    Suite(runner, tmp_path).run()

    where = {call.args[0]: call.where for call in runner.made}
    assert where["compile"] == tmp_path.as_posix()
    assert where["lint"] == (tmp_path / "web" / "app").as_posix()


def test_every_readiness_command_runs_before_the_first_check(tmp_path, runner):
    write_suite(tmp_path,
                check("compile", ready=["ping"], message="ping failed"),
                check("lint", folder="web", ready=["install"], message="install failed"))
    given_every_program_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.passed
    assert runner.calls == [["ping"], ["install"], ["compile"], ["lint"]]


def test_a_readiness_command_runs_in_the_folder_of_its_check(tmp_path, runner):
    write_suite(tmp_path, check("lint", folder="web", ready=["install"], message="no install"))
    given_every_program_passes(runner)

    Suite(runner, tmp_path).run()

    assert runner.made[0].where == (tmp_path / "web").as_posix()


def test_a_failing_readiness_command_is_not_ready_with_its_message(tmp_path, runner):
    write_suite(tmp_path,
                check("compile", ready=["ping"], message="The store does not answer."),
                check("lint"))
    given_every_program_passes(runner)
    runner.stub("ping", says="nobody home", status=1)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert not outcome.passed
    assert "The store does not answer." in outcome.said
    assert "nobody home" in outcome.said
    assert not runner.started("compile")
    assert not runner.started("lint")


def test_a_readiness_command_is_skipped_when_what_it_would_make_is_there(tmp_path, runner):
    (tmp_path / "web" / "installed").mkdir(parents=True)
    write_suite(tmp_path, check("lint", folder="web", ready=["install"], message="no install",
                                unless="web/installed"))
    given_every_program_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.passed
    assert runner.calls == [["lint"]]


def test_a_readiness_command_runs_when_what_it_would_make_is_missing(tmp_path, runner):
    write_suite(tmp_path, check("lint", folder="web", ready=["install"], message="no install",
                                unless="web/installed"))
    given_every_program_passes(runner)

    Suite(runner, tmp_path).run()

    assert runner.calls == [["install"], ["lint"]]


def test_a_failing_check_is_red_and_stops_the_run(tmp_path, runner):
    write_suite(tmp_path, check("compile"), check("prove"), check("lint"))
    given_every_program_passes(runner)
    runner.stub("prove", says="a test failed", status=1)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.ready
    assert not outcome.passed
    assert "a test failed" in outcome.said
    assert not runner.started("lint")


# Reading the output would make a passing machine look broken on the day a runner reworded itself.
def test_a_check_that_fails_saying_it_was_not_ready_is_still_red(tmp_path, runner):
    write_suite(tmp_path, check("compile", ready=["ping"], message="no store"))
    given_every_program_passes(runner)
    runner.stub("compile", says="Cannot connect to the store", status=1)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.ready
    assert not outcome.passed


def test_a_run_that_passes_keeps_what_every_check_said(tmp_path, runner):
    write_suite(tmp_path, check("compile"), check("lint"))
    given_every_program_passes(runner)
    runner.stub("compile", says="the build passed")
    runner.stub("lint", says="the lint passed")

    outcome = Suite(runner, tmp_path).run()

    assert outcome.passed
    assert "the build passed" in outcome.said
    assert "the lint passed" in outcome.said


def test_a_program_missing_from_the_path_is_not_ready_before_any_check(tmp_path, runner):
    write_suite(tmp_path, check("compile"), check("prove"))
    given_every_program_passes(runner)
    runner.hide("prove")

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert not outcome.passed
    assert "prove" in outcome.said
    assert runner.calls == []


def test_a_readiness_program_missing_from_the_path_is_not_ready(tmp_path, runner):
    write_suite(tmp_path, check("compile", ready=["ping"], message="no store"))
    given_every_program_passes(runner)
    runner.hide("ping")

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert "ping" in outcome.said
    assert runner.calls == []


def test_a_checkout_with_no_suite_file_is_not_ready(tmp_path, runner):
    given_every_program_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert not outcome.passed
    assert SUITE_FILE in outcome.said
    assert runner.calls == []


def test_a_suite_file_naming_no_checks_is_not_ready(tmp_path, runner):
    write_suite(tmp_path)
    given_every_program_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert not outcome.passed
    assert SUITE_FILE in outcome.said
    assert runner.calls == []


def test_an_empty_suite_file_is_not_ready(tmp_path, runner):
    given_a_suite_file_reading(tmp_path, "")

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert SUITE_FILE in outcome.said


def test_a_suite_file_that_does_not_parse_is_not_ready(tmp_path, runner):
    given_a_suite_file_reading(tmp_path, "{ checks: ")

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert SUITE_FILE in outcome.said


# Whether the front end is installed differs between checkouts, so the install is left out.
def test_this_repo_s_suite_file_runs_the_checks_the_readme_names(runner):
    given_this_repo_s_programs_pass(runner)

    outcome = Suite(runner, ROOT).run()

    web = (ROOT / "src" / "Skillworks.Studio.Web").as_posix()
    assert outcome.passed
    assert runner.calls[0] == ["docker", "info"]
    assert [(call.args, call.where) for call in runner.made if call.args[:2] != ["npm", "ci"]][1:] == [
        (["dotnet", "test", "Skillworks.slnx"], ROOT.as_posix()),
        (["uv", "run", "--with", "pytest", "pytest", "tests/plugins/skillworks/scripts"], ROOT.as_posix()),
        (["node", "--test", "tests/plugins/skillworks/scripts/**/*.test.mjs"], ROOT.as_posix()),
        (["npm", "run", "typecheck"], web),
        (["npm", "run", "lint"], web),
        (["npm", "test"], web),
    ]


def test_this_repo_s_front_end_is_installed_when_nothing_is(tmp_path, runner):
    given_a_suite_file_reading(tmp_path, (ROOT / SUITE_FILE).read_text(encoding="utf-8"))
    given_this_repo_s_programs_pass(runner)

    Suite(runner, tmp_path).run()

    assert runner.calls[:2] == [["docker", "info"], ["npm", "ci"]]
    assert runner.made[1].where == (tmp_path / "src" / "Skillworks.Studio.Web").as_posix()


def test_a_check_with_no_command_is_not_ready(tmp_path, runner):
    given_a_suite_file_reading(
        tmp_path, json.dumps({"checks": [{"command": [], "folder": "."}]}))

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert SUITE_FILE in outcome.said


# --- how many times a red Suite runs -----------------------------------------

def given_a_check_red_on_its_first_run_alone(runner):
    runner.refuse("prove", "a test failed", times=1)


def test_with_no_setting_one_red_run_is_red(tmp_path, runner):
    write_suite(tmp_path, check("prove"))
    given_every_program_passes(runner)
    given_a_check_red_on_its_first_run_alone(runner)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.ready
    assert not outcome.passed
    assert runner.calls == [["prove"]]


def test_a_second_run_asked_for_passes_a_suite_red_then_green(tmp_path, runner):
    write_suite(tmp_path, check("prove"), runs=2)
    given_every_program_passes(runner)
    given_a_check_red_on_its_first_run_alone(runner)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.passed
    assert runner.calls == [["prove"], ["prove"]]


def test_a_second_run_asked_for_leaves_a_suite_red_twice_red(tmp_path, runner):
    write_suite(tmp_path, check("prove"), runs=2)
    given_every_program_passes(runner)
    runner.stub("prove", says="a test failed", status=1)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.ready
    assert not outcome.passed
    assert runner.calls == [["prove"], ["prove"]]


def test_a_green_run_is_never_run_again(tmp_path, runner):
    write_suite(tmp_path, check("prove"), runs=3)
    given_every_program_passes(runner)

    Suite(runner, tmp_path).run()

    assert runner.calls == [["prove"]]


def test_each_run_is_heard_with_its_number(tmp_path, runner):
    write_suite(tmp_path, check("prove"), runs=2)
    given_every_program_passes(runner)
    given_a_check_red_on_its_first_run_alone(runner)
    heard = []

    Suite(runner, tmp_path).run(lambda outcome, at: heard.append((at, outcome.passed)))

    assert heard == [(1, False), (2, True)]


# A second run cannot make a missing tool appear, so nothing is spent proving that twice.
def test_a_machine_that_is_not_ready_is_never_run_again(tmp_path, runner):
    write_suite(tmp_path, check("prove", ready=["ping"], message="no store"), runs=2)
    given_every_program_passes(runner)
    runner.stub("ping", status=1)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert runner.calls == [["ping"]]


def test_a_readiness_command_runs_once_however_many_runs_there_are(tmp_path, runner):
    write_suite(tmp_path, check("prove", ready=["ping"], message="no store"), runs=2)
    given_every_program_passes(runner)
    runner.stub("prove", status=1)

    Suite(runner, tmp_path).run()

    assert runner.calls == [["ping"], ["prove"], ["prove"]]


def test_a_setting_that_is_not_a_count_is_not_ready(tmp_path, runner):
    for runs in (0, -1, "2", 1.5, True):
        write_suite(tmp_path, check("prove"), runs=runs)
        given_every_program_passes(runner)

        outcome = Suite(runner, tmp_path).run()

        assert not outcome.ready, runs
        assert "runs" in outcome.said, runs
    assert runner.calls == []


def test_this_repo_s_suite_file_asks_for_a_second_run():
    assert json.loads((ROOT / SUITE_FILE).read_text(encoding="utf-8"))["runs"] == 2


def test_the_seeded_suite_file_shows_the_setting_at_its_default():
    seed = ROOT / "plugins/skillworks/skills/skillworks-setup/seeds/suite.json"

    assert json.loads(seed.read_text(encoding="utf-8"))["runs"] == 1


REVIEW_SKILLS = (
    "plugins/skillworks/skills/code-review/SKILL.md",
    "plugins/skillworks/skills/review-architecture/SKILL.md",
)

PLACEMENT_CHECKS = "docs/agents/placement-checks.md"


def this_repo_s_checks():
    return json.loads((ROOT / SUITE_FILE).read_text(encoding="utf-8"))["checks"]


# A skill that names a program, folder or path from this repo's Suite works in no other repo.
def this_repo_s_facts():
    facts = set()
    for entry in this_repo_s_checks():
        facts.add(entry["command"][0])
        facts.update(word for word in entry["command"][1:] if "." in word or "/" in word)
        if entry["folder"] != ".":
            facts.add(entry["folder"])
    return facts


def test_the_review_skills_run_the_suite_file():
    for skill in REVIEW_SKILLS:
        assert SUITE_FILE in (ROOT / skill).read_text(encoding="utf-8"), skill


def test_the_review_skills_name_no_fact_of_this_repo_s_suite():
    facts = this_repo_s_facts()
    assert {"dotnet", "Skillworks.slnx", "src/Skillworks.Studio.Web"} <= facts

    for skill in REVIEW_SKILLS:
        text = (ROOT / skill).read_text(encoding="utf-8")
        assert [fact for fact in sorted(facts) if fact in text] == [], skill


def test_the_placement_checks_name_the_suite_checks_that_prove_placement_here():
    text = (ROOT / PLACEMENT_CHECKS).read_text(encoding="utf-8")

    named = {" ".join(entry["command"]) for entry in this_repo_s_checks()
             if "`{}`".format(" ".join(entry["command"])) in text}

    assert named == {"dotnet test Skillworks.slnx", "npm run lint"}
