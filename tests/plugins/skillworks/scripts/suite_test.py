#
# The programs are made up, so a case proves the Suite runs what the file names and nothing else.

import io
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

import suite
from conftest import ROOT, Ran, check, git, write_suite
from suite import SUITE_FILE, Suite


def given_every_program_passes(runner):
    for name in ("compile", "prove", "lint", "ping", "install"):
        runner.stub(name)


def given_this_repo_s_programs_pass(runner):
    for name in ("dotnet", "uv", "node", "npm", "claude"):
        runner.stub(name)
    # One answer serves every docker verb, because these cases read the commands and not a container.
    runner.stub("docker", says="an-id\n")


def given_a_suite_file_reading(tree, text):
    write_suite(tree)
    (tree / SUITE_FILE).write_text(text, encoding="utf-8")


def by_words(calls):
    return sorted(calls, key=" ".join)


# git is how the Suite reads its inputs, so a case about the checks reads every other call.
def made_by(runner):
    return [call for call in runner.made if call.args[0] != "git"]


def run_by(runner):
    return [call.args for call in made_by(runner)]


def test_every_check_the_file_names_runs_once(tmp_path, runner):
    write_suite(tmp_path, check("compile", "all"), check("prove", "all"), check("lint"))
    given_every_program_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.passed
    assert outcome.ready
    assert by_words(run_by(runner)) == [["compile", "all"], ["lint"], ["prove", "all"]]


# The bound only turns a hang into a failure, so a slow machine can never fail the case.
NEVER_SEEN = 600


def when_started(event, then=None):
    def does():
        event.set()
        return then() if then else None
    return does


def test_the_checks_run_together(tmp_path, runner):
    write_suite(tmp_path, check("compile"), check("prove"))
    given_every_program_passes(runner)
    prove_started = threading.Event()
    saw = []
    runner.stub("compile", does=lambda: saw.append(prove_started.wait(NEVER_SEEN)))
    runner.stub("prove", does=when_started(prove_started))

    outcome = Suite(runner, tmp_path).run()

    assert saw == [True]
    assert outcome.passed


def finishing_after(before, done, says):
    def does():
        if before is not None:
            assert before.wait(NEVER_SEEN)
        done.set()
        return Ran(0, says, "")
    return does


def test_the_output_keeps_the_order_of_the_file_whatever_finished_first(tmp_path, runner):
    write_suite(tmp_path, check("compile"), check("prove"), check("lint"))
    compiled, proved, linted = threading.Event(), threading.Event(), threading.Event()
    runner.stub("compile", does=finishing_after(proved, compiled, "compile one\ncompile two\n"))
    runner.stub("prove", does=finishing_after(linted, proved, "prove one\nprove two\n"))
    runner.stub("lint", does=finishing_after(None, linted, "lint one\nlint two\n"))

    outcome = Suite(runner, tmp_path).run()

    assert outcome.passed
    assert outcome.said == ("compile one\ncompile two\n"
                            "prove one\nprove two\n"
                            "lint one\nlint two\n")


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
    assert run_by(runner)[:2] == [["ping"], ["install"]]
    assert by_words(run_by(runner)[2:]) == [["compile"], ["lint"]]


def test_the_readiness_commands_run_one_by_one(tmp_path, runner):
    write_suite(tmp_path,
                check("compile", ready=["ping"], message="ping failed"),
                check("lint", ready=["install"], message="install failed"))
    given_every_program_passes(runner)
    pinged = threading.Event()
    saw = []
    runner.stub("ping", does=when_started(pinged))
    runner.stub("install", does=lambda: saw.append(pinged.is_set()))

    Suite(runner, tmp_path).run()

    assert saw == [True]


def test_a_readiness_command_runs_in_the_folder_of_its_check(tmp_path, runner):
    write_suite(tmp_path, check("lint", folder="web", ready=["install"], message="no install"))
    given_every_program_passes(runner)

    Suite(runner, tmp_path).run()

    assert made_by(runner)[0].where == (tmp_path / "web").as_posix()


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
    assert not runner.started("compile")
    assert not runner.started("lint")
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
    assert run_by(runner) == [["lint"]]


def test_a_readiness_command_runs_when_what_it_would_make_is_missing(tmp_path, runner):
    write_suite(tmp_path, check("lint", folder="web", ready=["install"], message="no install",
                                unless="web/installed"))
    given_every_program_passes(runner)

    Suite(runner, tmp_path).run()

    assert run_by(runner) == [["install"], ["lint"]]


def test_a_failing_check_is_red_and_lets_every_other_check_finish(tmp_path, runner):
    write_suite(tmp_path, check("compile"), check("prove"), check("lint"))
    runner.stub("compile", says="the build passed\n")
    runner.stub("prove", says="a test failed\n", status=1)
    runner.stub("lint", says="the lint passed\n")

    outcome = Suite(runner, tmp_path).run()

    assert outcome.ready
    assert not outcome.passed
    assert by_words(run_by(runner)) == [["compile"], ["lint"], ["prove"]]
    assert outcome.said == "the build passed\na test failed\nthe lint passed\n"


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
    assert run_by(runner) == []


def test_a_readiness_program_missing_from_the_path_is_not_ready(tmp_path, runner):
    write_suite(tmp_path, check("compile", ready=["ping"], message="no store"))
    given_every_program_passes(runner)
    runner.hide("ping")

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert "ping" in outcome.said
    assert run_by(runner) == []


def test_a_checkout_with_no_suite_file_is_not_ready(tmp_path, runner):
    given_every_program_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert not outcome.passed
    assert SUITE_FILE in outcome.said
    assert run_by(runner) == []


def test_a_suite_file_naming_no_checks_is_not_ready(tmp_path, runner):
    write_suite(tmp_path)
    given_every_program_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert not outcome.passed
    assert SUITE_FILE in outcome.said
    assert run_by(runner) == []


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


SCRIPT_TESTS = "tests/plugins/skillworks/scripts"

SCRIPT_TESTS_IMAGE = "docs/agents/script-tests.Dockerfile"

# Tests marked this_repo read the paths the image check ignores, which its copy leaves out.
THIS_REPO = "this_repo"

SCRIPT_TESTS_COMMAND = ["uv", "run", "--with", "pytest", "--with", "pytest-xdist",
                        "--with", "filelock", "pytest", "-n", "auto", SCRIPT_TESTS, "-m", "not " + THIS_REPO]

THIS_REPO_S_SUITE_TESTS_COMMAND = ["uv", "run", "--with", "pytest", "pytest",
                                   SCRIPT_TESTS + "/suite_test.py", "-m", THIS_REPO]

ARCHITECTURE_TESTS = "tests/Skillworks.Architecture.Tests"

DOCKER_TESTS = "Skillworks.Studio.slnf"

# The test host has crashed after every test passed, and a crash with no dump cannot say why.
DOCKER_TESTS_COMMAND = ["dotnet", "test", DOCKER_TESTS, "--blame-crash", "--blame-crash-dump-type", "mini"]

PLUGIN = "plugins/skillworks"

# Claude Code drops a skill whose frontmatter does not parse, and only its own parser says so.
PLUGIN_CHECK_COMMAND = ["claude", "plugin", "validate", PLUGIN]


# Whether the front end is installed differs between checkouts, so the install is left out.
# git answers nothing, so no file is copied and no Proof of a made-up pass reaches this clone.
def test_this_repo_s_suite_file_runs_the_checks_the_contributing_page_names(runner):
    given_this_repo_s_programs_pass(runner)
    runner.stub("git")

    outcome = Suite(runner, ROOT).run()

    web = (ROOT / "src" / "Skillworks.Studio.Web").as_posix()
    assert outcome.passed
    assert run_by(runner)[0] == ["docker", "info"]
    assert sorted((" ".join(call.args), call.where) for call in made_by(runner)[1:]
                  if call.args[0] != "docker" and call.args[:2] != ["npm", "ci"]) == [
        (" ".join(PLUGIN_CHECK_COMMAND), ROOT.as_posix()),
        (" ".join(DOCKER_TESTS_COMMAND), ROOT.as_posix()),
        (f"dotnet test {ARCHITECTURE_TESTS}", ROOT.as_posix()),
        ("node --test tests/plugins/skillworks/scripts/**/*.test.mjs", ROOT.as_posix()),
        ("npm run lint", web),
        ("npm run typecheck", web),
        ("npm test", web),
        (" ".join(THIS_REPO_S_SUITE_TESTS_COMMAND), ROOT.as_posix()),
    ]
    assert ["docker", "create", "--workdir", "/repo", "an-id", *SCRIPT_TESTS_COMMAND] in runner.calls


def test_this_repo_s_front_end_is_installed_when_nothing_is(tmp_path, runner):
    given_a_suite_file_reading(tmp_path, (ROOT / SUITE_FILE).read_text(encoding="utf-8"))
    (tmp_path / SCRIPT_TESTS_IMAGE).write_bytes((ROOT / SCRIPT_TESTS_IMAGE).read_bytes())
    given_this_repo_s_programs_pass(runner)
    runner.stub("git")

    Suite(runner, tmp_path).run()

    assert run_by(runner)[:2] == [["docker", "info"], ["npm", "ci"]]
    assert made_by(runner)[1].where == (tmp_path / "src" / "Skillworks.Studio.Web").as_posix()


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
    assert run_by(runner) == [["prove"]]


def test_a_second_run_asked_for_passes_a_suite_red_then_green(tmp_path, runner):
    write_suite(tmp_path, check("prove"), runs=2)
    given_every_program_passes(runner)
    given_a_check_red_on_its_first_run_alone(runner)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.passed
    assert run_by(runner) == [["prove"], ["prove"]]


def test_a_second_run_asked_for_leaves_a_suite_red_twice_red(tmp_path, runner):
    write_suite(tmp_path, check("prove"), runs=2)
    given_every_program_passes(runner)
    runner.stub("prove", says="a test failed", status=1)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.ready
    assert not outcome.passed
    assert run_by(runner) == [["prove"], ["prove"]]


def test_each_run_of_a_red_suite_runs_the_red_check_again_and_not_the_green_one(repo, runner):
    write_suite(repo.work, check("compile"), check("prove"), runs=2)
    given_every_program_passes(runner)
    runner.stub("prove", says="a test failed", status=1)

    outcome = Suite(runner, repo.work).run()

    assert not outcome.passed
    assert by_words(runner.started("compile") + runner.started("prove")) == [
        ["compile"], ["prove"], ["prove"]]


def test_a_green_run_is_never_run_again(tmp_path, runner):
    write_suite(tmp_path, check("prove"), runs=3)
    given_every_program_passes(runner)

    Suite(runner, tmp_path).run()

    assert run_by(runner) == [["prove"]]


def test_each_run_is_heard_with_its_number(tmp_path, runner):
    write_suite(tmp_path, check("prove"), runs=2)
    given_every_program_passes(runner)
    given_a_check_red_on_its_first_run_alone(runner)
    heard = []

    Suite(runner, tmp_path).run(lambda outcome, at: heard.append((at, outcome.passed)))

    assert heard == [(1, False), (2, True)]


def test_a_check_red_and_then_green_is_a_flake_with_its_red_output_and_the_suite_passes(
        repo, runner):
    write_suite(repo.work, check("compile"), check("prove"), runs=2)
    given_every_program_passes(runner)
    given_a_check_red_on_its_first_run_alone(runner)

    outcome = Suite(runner, repo.work).run()

    assert outcome.passed
    assert [flake.check for flake in outcome.flakes] == ["prove"]
    assert "a test failed" in outcome.flakes[0].said
    assert by_words(runner.started("compile") + runner.started("prove")) == [
        ["compile"], ["prove"], ["prove"]]


def test_a_check_red_on_every_run_is_no_flake(tmp_path, runner):
    write_suite(tmp_path, check("prove"), runs=2)
    given_every_program_passes(runner)
    runner.stub("prove", says="a test failed", status=1)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.passed
    assert outcome.flakes == ()


def test_a_check_that_flakes_beside_one_red_on_every_run_is_still_a_flake(tmp_path, runner):
    write_suite(tmp_path, check("compile"), check("prove"), runs=2)
    given_every_program_passes(runner)
    runner.stub("compile", says="it does not compile", status=1)
    given_a_check_red_on_its_first_run_alone(runner)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.passed
    assert outcome.red == ("compile",)
    assert [flake.check for flake in outcome.flakes] == ["prove"]


def test_with_one_run_a_red_check_is_no_flake(tmp_path, runner):
    write_suite(tmp_path, check("prove"), runs=1)
    given_every_program_passes(runner)
    given_a_check_red_on_its_first_run_alone(runner)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.passed
    assert outcome.flakes == ()


def test_a_green_suite_has_no_flake(tmp_path, runner):
    write_suite(tmp_path, check("prove"), runs=2)
    given_every_program_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert outcome.passed
    assert outcome.flakes == ()


# A second run cannot make a missing tool appear, so nothing is spent proving that twice.
def test_a_machine_that_is_not_ready_is_never_run_again(tmp_path, runner):
    write_suite(tmp_path, check("prove", ready=["ping"], message="no store"), runs=2)
    given_every_program_passes(runner)
    runner.stub("ping", status=1)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert run_by(runner) == [["ping"]]


def test_a_readiness_command_runs_once_however_many_runs_there_are(tmp_path, runner):
    write_suite(tmp_path, check("prove", ready=["ping"], message="no store"), runs=2)
    given_every_program_passes(runner)
    runner.stub("prove", status=1)

    Suite(runner, tmp_path).run()

    assert run_by(runner) == [["ping"], ["prove"], ["prove"]]


def test_a_setting_that_is_not_a_count_is_not_ready(tmp_path, runner):
    for runs in (0, -1, "2", 1.5, True):
        write_suite(tmp_path, check("prove"), runs=runs)
        given_every_program_passes(runner)

        outcome = Suite(runner, tmp_path).run()

        assert not outcome.ready, runs
        assert "runs" in outcome.said, runs
    assert run_by(runner) == []


# --- Proofs ------------------------------------------------------------------

def writing(repo, name, text="changed"):
    path = repo.work / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(text + "\n")


def committing(repo, name):
    writing(repo, name)
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "Change " + name)


def at(hour):
    return lambda: datetime(2026, 9, 27, hour, 30, tzinfo=timezone.utc)


PROVED = re.compile(r"^prove did not run, because Proof ([0-9a-f]{12}), made (.+), holds its inputs\n$")


def test_an_unchanged_tree_skips_a_check_that_passed_on_it(repo, runner):
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)

    Suite(runner, repo.work).run()
    outcome = Suite(runner, repo.work).run()

    assert outcome.passed
    assert outcome.ready
    assert runner.started("prove") == [["prove"]]


def test_a_suite_in_which_every_check_is_proved_passes_having_run_nothing(repo, runner):
    write_suite(repo.work, check("compile"), check("prove"))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()
    runner.made.clear()

    outcome = Suite(runner, repo.work).run()

    assert outcome.passed
    assert outcome.ready
    assert not runner.started("compile")
    assert not runner.started("prove")


def test_a_skipped_line_names_its_proof_and_when_it_was_made(repo, runner):
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)
    Suite(runner, repo.work, now=at(9)).run()

    first = Suite(runner, repo.work, now=at(11)).run()
    second = Suite(runner, repo.work, now=at(12)).run()

    named = PROVED.match(first.said)
    assert named, first.said
    assert named.group(2) == "2026-09-27 09:30 UTC"
    assert second.said == first.said


def test_a_change_to_a_file_the_check_reads_runs_it_again(repo, runner):
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()

    writing(repo, "base.txt")
    Suite(runner, repo.work).run()

    assert len(runner.started("prove")) == 2


def test_a_committed_change_is_read_the_same_as_the_uncommitted_one(repo, runner):
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)
    writing(repo, "base.txt")
    Suite(runner, repo.work).run()

    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "The same tree, committed")
    Suite(runner, repo.work).run()

    assert len(runner.started("prove")) == 1


def test_a_change_inside_what_a_check_ignores_skips_it(repo, runner):
    write_suite(repo.work, check("prove", ignores=["docs/notes", "web/*.md"]))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()

    writing(repo, "docs/notes/today.md")
    writing(repo, "web/readme.md")
    outcome = Suite(runner, repo.work).run()

    assert outcome.passed
    assert len(runner.started("prove")) == 1


def test_a_name_that_only_begins_with_an_ignored_folder_is_still_read(repo, runner):
    write_suite(repo.work, check("prove", ignores=["web"]))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()

    writing(repo, "website/page.ts")
    Suite(runner, repo.work).run()

    assert len(runner.started("prove")) == 2


def test_an_untracked_file_is_an_input(repo, runner):
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()

    writing(repo, "web/new.ts")
    Suite(runner, repo.work).run()

    assert len(runner.started("prove")) == 2


def test_a_git_ignored_file_is_not_an_input(repo, runner):
    writing(repo, ".gitignore", "ignored.txt")
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()

    writing(repo, "ignored.txt")
    Suite(runner, repo.work).run()

    assert len(runner.started("prove")) == 1


def test_a_tracked_file_the_worktree_deleted_is_no_longer_an_input(repo, runner):
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()

    (repo.work / "base.txt").unlink()
    Suite(runner, repo.work).run()

    assert len(runner.started("prove")) == 2


# The Suite file is ignored here, so only the entry itself can make the key new.
def test_an_edit_to_the_check_s_own_entry_is_a_new_key(repo, runner):
    write_suite(repo.work, check("prove", ignores=[SUITE_FILE]))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()

    write_suite(repo.work, check("prove", ignores=[SUITE_FILE],
                                 ready=["ping"], message="no store"))
    Suite(runner, repo.work).run()

    assert len(runner.started("prove")) == 2


def test_an_edit_to_another_check_s_entry_leaves_this_one_proved(repo, runner):
    write_suite(repo.work, check("prove", ignores=[SUITE_FILE]), check("lint"))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()

    write_suite(repo.work, check("prove", ignores=[SUITE_FILE]), check("lint", "all"))
    Suite(runner, repo.work).run()

    assert len(runner.started("prove")) == 1
    assert runner.started("lint") == [["lint"], ["lint", "all"]]


def test_a_red_check_writes_no_proof_and_a_green_one_beside_it_does(repo, runner):
    write_suite(repo.work, check("compile"), check("prove"))
    given_every_program_passes(runner)
    runner.stub("prove", says="a test failed\n", status=1)
    Suite(runner, repo.work).run()

    outcome = Suite(runner, repo.work).run()

    assert not outcome.passed
    assert len(runner.started("compile")) == 1
    assert len(runner.started("prove")) == 2


def test_two_worktrees_of_one_clone_share_proofs(repo, runner):
    write_suite(repo.work, check("prove"))
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "A Suite")
    other = repo.root / "other-worktree"
    git(repo.work, "worktree", "add", "--quiet", "--detach", other.as_posix(), "HEAD")
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()

    outcome = Suite(runner, other).run()

    assert outcome.passed
    assert len(runner.started("prove")) == 1
    assert PROVED.match(outcome.said), outcome.said


def test_a_folder_git_does_not_track_keeps_no_proofs(tmp_path, runner):
    write_suite(tmp_path, check("prove"))
    given_every_program_passes(runner)

    Suite(runner, tmp_path).run()
    Suite(runner, tmp_path).run()

    assert len(runner.started("prove")) == 2


def test_readiness_runs_only_for_the_checks_that_will_run(repo, runner):
    write_suite(repo.work,
                check("compile", ready=["ping"], message="no store"),
                check("lint", ready=["install"], message="no install", ignores=["api"]))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()
    runner.made.clear()

    writing(repo, "api/handler.cs")
    Suite(runner, repo.work).run()

    assert run_by(runner) == [["ping"], ["compile"]]


def test_a_proved_check_needs_nothing_on_the_path(repo, runner):
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()
    runner.hide("prove")

    outcome = Suite(runner, repo.work).run()

    assert outcome.ready
    assert outcome.passed


# --- fresh mode --------------------------------------------------------------

def test_fresh_mode_runs_every_check_whatever_proofs_exist(repo, runner):
    write_suite(repo.work, check("compile"), check("prove"))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()

    outcome = Suite(runner, repo.work, fresh=True).run()

    assert outcome.passed
    assert len(runner.started("compile")) == 2
    assert len(runner.started("prove")) == 2
    assert not PROVED.search(outcome.said)


def test_fresh_mode_writes_no_proof(repo, runner):
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)

    Suite(runner, repo.work, fresh=True).run()
    Suite(runner, repo.work).run()

    assert len(runner.started("prove")) == 2


def test_a_check_red_in_fresh_mode_loses_its_proof_and_runs_again_next_time(repo, runner):
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()
    given_a_check_red_on_its_first_run_alone(runner)

    fresh = Suite(runner, repo.work, fresh=True).run()
    after = Suite(runner, repo.work).run()

    assert not fresh.passed
    assert after.passed
    assert len(runner.started("prove")) == 3


def test_a_check_red_in_fresh_mode_loses_the_proofs_of_other_inputs_too(repo, runner):
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()
    writing(repo, "base.txt")
    Suite(runner, repo.work).run()
    given_a_check_red_on_its_first_run_alone(runner)
    Suite(runner, repo.work, fresh=True).run()

    git(repo.work, "checkout", "--quiet", "--", "base.txt")
    Suite(runner, repo.work).run()

    assert len(runner.started("prove")) == 4


def test_a_check_green_in_fresh_mode_keeps_its_proofs_beside_a_red_one(repo, runner):
    write_suite(repo.work, check("compile"), check("prove"))
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()
    given_a_check_red_on_its_first_run_alone(runner)
    Suite(runner, repo.work, fresh=True).run()

    outcome = Suite(runner, repo.work).run()

    assert outcome.passed
    assert len(runner.started("compile")) == 2
    assert len(runner.started("prove")) == 3


def test_fresh_mode_names_the_checks_that_went_red(repo, runner):
    write_suite(repo.work, check("compile", "all"), check("prove"), check("lint"))
    given_every_program_passes(runner)
    runner.stub("compile", status=1)
    runner.stub("lint", status=1)

    outcome = Suite(runner, repo.work, fresh=True).run()

    assert not outcome.passed
    assert outcome.red == ("compile all", "lint")


def test_fresh_mode_runs_a_check_with_an_image_on_the_host(repo, runner):
    given_a_suite_in_an_image(repo.work, "lint", "all", folder="web/app")
    docker = FakeDocker(runner)
    runner.stub("lint")

    outcome = Suite(runner, repo.work, fresh=True).run()

    assert outcome.passed
    assert docker.calls() == []
    assert [(call.args, call.where) for call in made_by(runner)] == [
        (["lint", "all"], (repo.work / "web/app").as_posix())]


def test_fresh_mode_needs_the_program_of_an_image_check_on_the_host(repo, runner):
    given_a_suite_in_an_image(repo.work, "lint")
    FakeDocker(runner)
    runner.hide("lint")

    outcome = Suite(runner, repo.work, fresh=True).run()

    assert not outcome.ready
    assert "lint is not on PATH" in outcome.said


def test_fresh_mode_runs_again_only_the_checks_that_went_red(repo, runner):
    write_suite(repo.work, check("compile"), check("prove"), runs=2)
    given_every_program_passes(runner)
    runner.stub("compile", says="compiled\n")
    runner.refuse("prove", "a test flaked", times=1)
    heard = []

    outcome = Suite(runner, repo.work, fresh=True).run(lambda outcome, at: heard.append(outcome))

    assert outcome.passed
    assert len(runner.started("compile")) == 1
    assert len(runner.started("prove")) == 2
    assert "compiled" in heard[1].said


def test_a_flake_in_fresh_mode_loses_its_proof_and_runs_again_next_time(repo, runner):
    write_suite(repo.work, check("prove"), runs=2)
    given_every_program_passes(runner)
    Suite(runner, repo.work).run()
    given_a_check_red_on_its_first_run_alone(runner)

    fresh = Suite(runner, repo.work, fresh=True).run()
    after = Suite(runner, repo.work).run()

    assert fresh.passed
    assert [flake.check for flake in fresh.flakes] == ["prove"]
    assert after.passed
    assert len(runner.started("prove")) == 4


# --- the skillworks-suite command --------------------------------------------

def suite_command(runner, *args):
    out, err = io.StringIO(), io.StringIO()
    status = suite.main(list(args), runner, out, err)
    return Ran(status, out.getvalue(), err.getvalue())


def test_the_command_runs_the_suite_of_the_repo_it_is_started_below(repo, runner, monkeypatch):
    write_suite(repo.work, check("prove"))
    runner.stub("prove", says="every case passed\n")
    below = repo.work / "src" / "deep"
    below.mkdir(parents=True)
    monkeypatch.chdir(below)

    ran = suite_command(runner)

    assert ran.status == 0, ran.err
    assert "every case passed" in ran.out
    assert "ok    the Suite passed" in ran.out
    assert [call.where for call in runner.made if call.args[0] == "prove"] == [repo.work.as_posix()]


def test_the_command_keeps_a_proof_the_next_suite_reads(repo, runner, monkeypatch):
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)
    monkeypatch.chdir(repo.work)

    suite_command(runner)
    outcome = Suite(runner, repo.work).run()

    assert outcome.passed
    assert runner.started("prove") == [["prove"]]
    assert PROVED.match(outcome.said), outcome.said


def test_a_red_suite_fails_the_command_and_says_what_went_red(repo, runner, monkeypatch):
    write_suite(repo.work, check("prove"))
    runner.stub("prove", says="a test failed\n", status=1)
    monkeypatch.chdir(repo.work)

    ran = suite_command(runner)

    assert ran.status == 1
    assert "a test failed" in ran.out
    assert "FAIL  the Suite went red" in ran.err


def test_the_command_names_each_flake_after_the_last_run(repo, runner, monkeypatch):
    write_suite(repo.work, check("compile", "all"), check("prove"), runs=2)
    given_every_program_passes(runner)
    given_a_check_red_on_its_first_run_alone(runner)
    monkeypatch.chdir(repo.work)

    ran = suite_command(runner)

    assert ran.status == 0, ran.err
    last_run = ran.out.rindex("--- suite run 2")
    flake = ran.out.index("FLAKE prove went red and then passed")
    assert last_run < flake < ran.out.index("ok    the Suite passed")
    assert "compile all went red" not in ran.out


def test_the_command_names_no_flake_when_none_happened(repo, runner, monkeypatch):
    write_suite(repo.work, check("prove"), runs=2)
    given_every_program_passes(runner)
    monkeypatch.chdir(repo.work)

    ran = suite_command(runner)

    assert ran.status == 0, ran.err
    assert "FLAKE" not in ran.out


def test_a_machine_short_of_what_the_suite_needs_fails_the_command_naming_it(
        repo, runner, monkeypatch):
    write_suite(repo.work, check("prove", ready=["ping"], message="the store does not answer"))
    given_every_program_passes(runner)
    runner.stub("ping", status=1)
    monkeypatch.chdir(repo.work)

    ran = suite_command(runner)

    assert ran.status == 1
    assert "FAIL  the store does not answer" in ran.err
    assert not runner.started("prove")


USAGE = "usage: skillworks-suite [--fresh | --image <Dockerfile> -- <command>]\n"


def test_the_command_takes_no_argument_but_fresh_or_a_trial(repo, runner, monkeypatch):
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)
    monkeypatch.chdir(repo.work)

    for args in (["--all"], ["--fresh", "--fresh"], ["--fresh", "now"]):
        ran = suite_command(runner, *args)

        assert ran.status == 64, args
        assert ran.err == USAGE, args
    assert not runner.started("prove")


def test_the_command_with_fresh_runs_a_check_a_proof_holds(repo, runner, monkeypatch):
    write_suite(repo.work, check("prove"))
    given_every_program_passes(runner)
    monkeypatch.chdir(repo.work)
    suite_command(runner)

    ran = suite_command(runner, "--fresh")
    Suite(runner, repo.work).run()

    assert ran.status == 0, ran.err
    assert "ok    the Suite passed" in ran.out
    assert len(runner.started("prove")) == 2


def test_the_command_prints_a_character_its_code_page_lacks():
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

    suite.speaking_any_character(stream)
    stream.write("✔ every case passed\n")
    stream.flush()

    assert stream.buffer.getvalue() == "✔ every case passed\n".encode("utf-8")


def test_the_command_outside_a_repository_runs_nothing(tmp_path, runner, monkeypatch):
    write_suite(tmp_path, check("prove"))
    given_every_program_passes(runner)
    monkeypatch.chdir(tmp_path)

    ran = suite_command(runner)

    assert ran.status == 1
    assert "is not in a git repository" in ran.err
    assert not runner.started("prove")


def test_a_suite_file_carrying_when_is_unreadable_and_says_to_use_ignores(tmp_path, runner):
    given_a_suite_file_reading(tmp_path, json.dumps(
        {"checks": [{"command": ["lint"], "folder": ".", "when": ["web"]}]}))
    given_every_program_passes(runner)

    outcome = Suite(runner, tmp_path).run()

    assert not outcome.ready
    assert not outcome.passed
    assert SUITE_FILE in outcome.said
    assert "`when`" in outcome.said
    assert "Replace it with `ignores`" in outcome.said
    assert "every file git does not ignore" in outcome.said
    assert run_by(runner) == []


def test_ignores_that_is_not_a_list_of_paths_makes_the_suite_file_unreadable(tmp_path, runner):
    for ignores in ("web", [], [""], [3], {"web": True}, None):
        given_a_suite_file_reading(tmp_path, json.dumps(
            {"checks": [{"command": ["lint"], "folder": ".", "ignores": ignores}]}))
        given_every_program_passes(runner)

        outcome = Suite(runner, tmp_path).run()

        assert not outcome.ready, ignores
        assert SUITE_FILE in outcome.said, ignores
    assert run_by(runner) == []


# --- a check that runs in an image ------------------------------------------

DOCKERFILE = "docs/agents/tests.Dockerfile"


class FakeDocker:
    def __init__(self, runner, says="", status=0, answers=True, builds=True, creates=True,
                 copies=True):
        self.runner = runner
        self.says = says
        self.status = status
        self.answers = answers
        self.builds = builds
        self.creates = creates
        self.copies = copies
        self.contents = None
        self.copied = None
        self.stage = None
        runner.stub("docker", does=self.answer)

    def answer(self):
        call = self.runner.made[-1]
        verb = call.args[1]
        if verb == "info":
            return Ran(0, "", "") if self.answers else Ran(1, "", "Cannot connect to the daemon\n")
        if verb == "build":
            return Ran(0, "the-image\n", "") if self.builds else Ran(1, "", "no such base\n")
        if verb == "create":
            return Ran(0, "the-container\n", "") if self.creates else Ran(1, "", "no such image\n")
        if verb == "cp":
            self.stage = Path(call.where)
            self.contents = {path.relative_to(self.stage).as_posix(): path.read_text(encoding="utf-8")
                             for path in self.stage.rglob("*") if path.is_file()}
            self.copied = sorted(self.contents)
            return Ran(0, "", "") if self.copies else Ran(1, "", "no space left\n")
        if verb == "start":
            return Ran(self.status, self.says, "")
        return Ran(0, "", "")

    def calls(self):
        return [call for call in self.runner.calls if call[0] == "docker"]

    def verbs(self):
        return [call[1] for call in self.calls()]


def given_a_dockerfile(tree):
    path = Path(tree) / DOCKERFILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("FROM scratch\n", encoding="utf-8", newline="\n")


def given_a_suite_in_an_image(tree, *command, folder="."):
    given_a_dockerfile(tree)
    write_suite(tree, check(*command, folder=folder, image=DOCKERFILE))


def test_a_check_with_an_image_builds_it_from_its_dockerfile(repo, runner):
    given_a_suite_in_an_image(repo.work, "prove")
    docker = FakeDocker(runner)

    outcome = Suite(runner, repo.work).run()

    assert outcome.passed
    dockerfile = repo.work / DOCKERFILE
    assert ["docker", "build", "--quiet", "--file", dockerfile.as_posix(),
            dockerfile.parent.as_posix()] in docker.calls()


def test_a_check_with_an_image_copies_exactly_the_files_git_does_not_ignore(repo, runner):
    given_a_suite_in_an_image(repo.work, "prove")
    writing(repo, ".gitignore", "ignored.txt")
    committing(repo, "web/page.ts")
    writing(repo, "ignored.txt")
    writing(repo, "untracked.txt")
    docker = FakeDocker(runner)

    Suite(runner, repo.work).run()

    assert docker.copied == sorted([".gitignore", "base.txt", DOCKERFILE, SUITE_FILE,
                                    "untracked.txt", "web/page.ts"])


def test_a_check_with_an_image_copies_none_of_the_paths_it_ignores(repo, runner):
    given_a_dockerfile(repo.work)
    write_suite(repo.work, check("prove", image=DOCKERFILE, ignores=["web"]))
    committing(repo, "web/page.ts")
    docker = FakeDocker(runner)

    Suite(runner, repo.work).run()

    assert docker.copied == sorted(["base.txt", DOCKERFILE, SUITE_FILE])


def test_a_check_with_an_image_copies_uncommitted_work_as_it_is(repo, runner):
    given_a_suite_in_an_image(repo.work, "prove")
    writing(repo, "base.txt", "uncommitted")
    docker = FakeDocker(runner)

    Suite(runner, repo.work).run()

    assert docker.contents["base.txt"] == "base\nuncommitted\n"


def test_a_check_with_an_image_leaves_out_a_tracked_file_the_worktree_deleted(repo, runner):
    given_a_suite_in_an_image(repo.work, "prove")
    (repo.work / "base.txt").unlink()
    docker = FakeDocker(runner)

    Suite(runner, repo.work).run()

    assert "base.txt" not in docker.copied


def test_a_check_with_an_image_runs_its_command_in_the_container_from_its_folder(repo, runner):
    given_a_suite_in_an_image(repo.work, "lint", "all", folder="web/app")
    docker = FakeDocker(runner)

    Suite(runner, repo.work).run()

    assert docker.calls()[-4:] == [
        ["docker", "create", "--workdir", "/repo/web/app", "the-image", "lint", "all"],
        ["docker", "cp", "./.", "the-container:/repo"],
        ["docker", "start", "--attach", "the-container"],
        ["docker", "rm", "--force", "the-container"],
    ]
    assert not runner.started("lint")


def test_a_check_with_an_image_at_the_repo_root_runs_from_the_copy_s_root(repo, runner):
    given_a_suite_in_an_image(repo.work, "prove")
    docker = FakeDocker(runner)

    Suite(runner, repo.work).run()

    assert ["docker", "create", "--workdir", "/repo", "the-image", "prove"] in docker.calls()


def test_a_check_with_an_image_takes_the_outcome_and_the_output_of_its_container(repo, runner):
    given_a_suite_in_an_image(repo.work, "prove")
    FakeDocker(runner, says="a test failed\n", status=1)

    outcome = Suite(runner, repo.work).run()

    assert outcome.ready
    assert not outcome.passed
    assert "a test failed\n" in outcome.said


def test_a_red_container_is_still_removed(repo, runner):
    given_a_suite_in_an_image(repo.work, "prove")
    docker = FakeDocker(runner, status=1)

    Suite(runner, repo.work).run()

    assert docker.verbs()[-1] == "rm"


def test_the_copy_is_gone_once_the_check_has_run(repo, runner):
    given_a_suite_in_an_image(repo.work, "prove")
    docker = FakeDocker(runner)

    Suite(runner, repo.work).run()

    assert docker.stage is not None
    assert not docker.stage.exists()


def test_an_image_that_does_not_build_is_a_red_check_that_starts_nothing(repo, runner):
    given_a_suite_in_an_image(repo.work, "prove")
    docker = FakeDocker(runner, builds=False)

    outcome = Suite(runner, repo.work).run()

    assert outcome.ready
    assert not outcome.passed
    assert "no such base" in outcome.said
    assert "create" not in docker.verbs()


def test_a_check_with_an_image_is_not_ready_when_docker_does_not_answer(repo, runner):
    given_a_suite_in_an_image(repo.work, "prove")
    docker = FakeDocker(runner, answers=False)

    outcome = Suite(runner, repo.work).run()

    assert not outcome.ready
    assert not outcome.passed
    assert "Docker does not answer" in outcome.said
    assert DOCKERFILE in outcome.said
    assert docker.verbs() == ["info"]


def test_a_check_with_an_image_is_not_ready_when_docker_is_not_on_the_path(repo, runner):
    given_a_suite_in_an_image(repo.work, "prove")
    FakeDocker(runner)
    runner.hide("docker")

    outcome = Suite(runner, repo.work).run()

    assert not outcome.ready
    assert "docker" in outcome.said
    assert run_by(runner) == []


def test_a_check_with_an_image_needs_its_program_in_the_image_and_not_on_the_host(repo, runner):
    given_a_suite_in_an_image(repo.work, "prove")
    FakeDocker(runner)
    runner.hide("prove")

    outcome = Suite(runner, repo.work).run()

    assert outcome.passed


def test_docker_is_asked_once_however_many_checks_run_in_an_image(repo, runner):
    given_a_dockerfile(repo.work)
    write_suite(repo.work, check("prove", image=DOCKERFILE), check("lint", image=DOCKERFILE))
    # The fake reads the last call, which two checks running together would share.
    runner.stub("docker", says="an-id\n")

    Suite(runner, repo.work).run()

    assert runner.calls.count(["docker", "info"]) == 1


def test_a_suite_with_no_image_never_asks_docker(tmp_path, runner):
    write_suite(tmp_path, check("prove"))
    given_every_program_passes(runner)
    docker = FakeDocker(runner)

    Suite(runner, tmp_path).run()

    assert docker.calls() == []


def test_an_image_that_is_not_a_file_in_the_repo_makes_the_suite_file_unreadable(tmp_path, runner):
    given_a_dockerfile(tmp_path)
    for image in ("docs/agents/missing.Dockerfile", "docs/agents", "", 3, ["x"]):
        given_a_suite_file_reading(tmp_path, json.dumps(
            {"checks": [{"command": ["prove"], "folder": ".", "image": image}]}))
        FakeDocker(runner)

        outcome = Suite(runner, tmp_path).run()

        assert not outcome.ready, image
        assert SUITE_FILE in outcome.said, image
    assert run_by(runner) == []


# --- a Trial -------------------------------------------------------------------

def trial(runner, repo, *command, image=DOCKERFILE, monkeypatch, where=None):
    monkeypatch.chdir(repo.work if where is None else where)
    return suite_command(runner, "--image", image, "--", *command)


def test_a_trial_runs_its_command_from_the_folder_it_is_started_in(repo, runner, monkeypatch):
    given_a_suite_in_an_image(repo.work, "prove")
    below = repo.work / "web" / "app"
    below.mkdir(parents=True)
    docker = FakeDocker(runner)

    ran = trial(runner, repo, "prove", "page_test.py", where=below, monkeypatch=monkeypatch)

    assert ran.status == 0, ran.err
    assert ["docker", "create", "--workdir", "/repo/web/app", "the-image", "prove",
            "page_test.py"] in docker.calls()


def test_a_trial_started_outside_the_repo_is_refused_and_says_so(
        repo, runner, monkeypatch, tmp_path):
    given_a_suite_in_an_image(repo.work, "prove")
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    # Git then names the repo from a folder outside it, as it does for a caller that sets them.
    monkeypatch.setenv("GIT_DIR", (repo.work / ".git").as_posix())
    monkeypatch.setenv("GIT_WORK_TREE", repo.work.as_posix())
    docker = FakeDocker(runner)

    ran = trial(runner, repo, "prove", where=outside, monkeypatch=monkeypatch)

    assert ran.status == 1
    assert ran.err.startswith("FAIL  ")
    assert "outside the repo" in ran.err
    assert outside.name in ran.err
    assert docker.calls() == []


def test_a_trial_copies_what_any_check_of_its_image_reads(repo, runner, monkeypatch):
    given_a_dockerfile(repo.work)
    write_suite(repo.work,
                check("prove", image=DOCKERFILE, ignores=["web", "notes"]),
                check("lint", image=DOCKERFILE, ignores=["web/app", "scripts"]),
                check("compile", ignores=["web", "notes", "scripts"]))
    for name in ("web/app/page.ts", "web/api.ts", "notes/one.md", "scripts/two.sh"):
        committing(repo, name)
    docker = FakeDocker(runner)

    trial(runner, repo, "prove", monkeypatch=monkeypatch)

    assert docker.copied == sorted(["base.txt", DOCKERFILE, SUITE_FILE, "web/api.ts",
                                    "notes/one.md", "scripts/two.sh"])


def test_a_trial_builds_the_image_and_runs_its_command_from_the_copy_s_root(
        repo, runner, monkeypatch):
    given_a_suite_in_an_image(repo.work, "prove", "all", folder="web/app")
    docker = FakeDocker(runner, says="3 passed\n")

    ran = trial(runner, repo, "prove", "-k", "one case", monkeypatch=monkeypatch)

    dockerfile = repo.work / DOCKERFILE
    assert docker.calls() == [
        ["docker", "info"],
        ["docker", "build", "--quiet", "--file", dockerfile.as_posix(), dockerfile.parent.as_posix()],
        ["docker", "create", "--workdir", "/repo", "the-image", "prove", "-k", "one case"],
        ["docker", "cp", "./.", "the-container:/repo"],
        ["docker", "start", "--attach", "the-container"],
        ["docker", "rm", "--force", "the-container"],
    ]
    assert ran.out == "3 passed\n"
    assert not runner.started("prove")


def test_a_trial_exits_with_the_command_s_exit_code(repo, runner, monkeypatch):
    given_a_suite_in_an_image(repo.work, "prove")

    for status in (0, 1, 5):
        FakeDocker(runner, says="the run\n", status=status)

        ran = trial(runner, repo, "prove", monkeypatch=monkeypatch)

        assert ran.status == status
        assert ran.out == "the run\n"


def test_a_trial_copies_the_inputs_of_the_check_that_names_its_image(repo, runner, monkeypatch):
    given_a_dockerfile(repo.work)
    write_suite(repo.work, check("prove", image=DOCKERFILE, ignores=["web"]))
    writing(repo, ".gitignore", "ignored.txt")
    committing(repo, "web/page.ts")
    committing(repo, "gone.txt")
    (repo.work / "gone.txt").unlink()
    writing(repo, "ignored.txt")
    writing(repo, "untracked.txt")
    writing(repo, "base.txt", "uncommitted")
    docker = FakeDocker(runner)

    trial(runner, repo, "prove", monkeypatch=monkeypatch)

    assert docker.copied == sorted([".gitignore", "base.txt", DOCKERFILE, SUITE_FILE,
                                    "untracked.txt"])
    assert docker.contents["base.txt"] == "base\nuncommitted\n"


def test_a_trial_refuses_an_image_no_check_names(repo, runner, monkeypatch):
    given_a_suite_in_an_image(repo.work, "prove")
    (repo.work / "docs/agents/other.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    docker = FakeDocker(runner)

    ran = trial(runner, repo, "prove", image="docs/agents/other.Dockerfile",
                monkeypatch=monkeypatch)

    assert ran.status == 1
    assert ran.err.startswith("FAIL  ")
    assert "docs/agents/other.Dockerfile" in ran.err
    assert docker.calls() == []


def test_a_trial_refuses_a_suite_file_it_cannot_read_naming_the_fault(repo, runner, monkeypatch):
    given_a_dockerfile(repo.work)
    given_a_suite_file_reading(repo.work, "{ not json")
    docker = FakeDocker(runner)

    ran = trial(runner, repo, "prove", monkeypatch=monkeypatch)

    assert ran.status == 1
    assert SUITE_FILE in ran.err
    assert "it is not JSON" in ran.err
    assert docker.calls() == []


def test_a_trial_with_no_command_or_no_separator_is_refused_with_the_usage(
        repo, runner, monkeypatch):
    given_a_suite_in_an_image(repo.work, "prove")
    docker = FakeDocker(runner)
    monkeypatch.chdir(repo.work)

    for args in (["--image"], ["--image", DOCKERFILE], ["--image", DOCKERFILE, "--"],
                 ["--image", DOCKERFILE, "prove"], ["--image", "--", "prove"],
                 ["--fresh", "--image", DOCKERFILE, "--", "prove"]):
        ran = suite_command(runner, *args)

        assert ran.status == 64, args
        assert ran.err == USAGE, args
    assert docker.calls() == []


def test_a_trial_is_refused_with_the_suite_s_message_when_docker_does_not_answer(
        repo, runner, monkeypatch):
    given_a_suite_in_an_image(repo.work, "prove")
    docker = FakeDocker(runner, answers=False)
    said = Suite(runner, repo.work).run().said

    ran = trial(runner, repo, "prove", monkeypatch=monkeypatch)

    assert ran.status == 1
    assert ran.err == "FAIL  " + said
    assert docker.verbs() == ["info", "info"]


def test_a_trial_says_which_step_failed_before_the_command(repo, runner, monkeypatch):
    given_a_suite_in_an_image(repo.work, "prove")

    for failing, says, word in (({"builds": False}, "no such base", "build"),
                                ({"creates": False}, "no such image", "create"),
                                ({"copies": False}, "no space left", "copy")):
        FakeDocker(runner, **failing)

        ran = trial(runner, repo, "prove", monkeypatch=monkeypatch)

        assert ran.status != 0, word
        assert word in ran.err, ran.err
        assert says in ran.err, ran.err


def test_a_trial_removes_its_container_however_it_ends(repo, runner, monkeypatch):
    given_a_suite_in_an_image(repo.work, "prove")

    for ending in ({"status": 1}, {"copies": False}):
        docker = FakeDocker(runner, **ending)
        runner.made.clear()

        trial(runner, repo, "prove", monkeypatch=monkeypatch)

        assert docker.verbs()[-1] == "rm", ending


def test_a_trial_keeps_no_proof_reads_none_and_forgets_none(repo, runner, monkeypatch):
    given_a_suite_in_an_image(repo.work, "prove")
    FakeDocker(runner)
    Suite(runner, repo.work).run()
    proofs = Path(git(repo.work, "rev-parse", "--path-format=absolute",
                      "--git-common-dir").strip()) / suite.PROOFS
    kept = proofs.read_bytes()

    for status in (0, 1):
        docker = FakeDocker(runner, status=status)
        runner.made.clear()

        trial(runner, repo, "prove", monkeypatch=monkeypatch)

        assert "start" in docker.verbs(), status
        assert proofs.read_bytes() == kept, status


def test_this_repo_s_suite_file_runs_a_red_suite_twice():
    assert json.loads((ROOT / SUITE_FILE).read_text(encoding="utf-8"))["runs"] == 2


STEPS_PAGE = "docs/usage/the-loop/steps.md"

LANDING_PAGE = "docs/usage/the-loop/landing.md"

DRIFT_CHECK_PAGE = "docs/usage/the-loop/drift-check.md"

NAME_CHECK_PAGE = "docs/usage/the-loop/name-check.md"

FULL_RUN_PAGE = "docs/usage/the-loop/full-run.md"


def test_the_loop_docs_say_the_checks_run_together():
    for doc in (STEPS_PAGE, "docs/usage/suite.md"):
        text = " ".join((ROOT / doc).read_text(encoding="utf-8").split())
        assert "the checks run together" in text, doc


SUITE_PAGE = "docs/usage/suite.md"


def test_the_loop_docs_and_the_setup_docs_say_a_check_names_what_it_ignores():
    for doc in (STEPS_PAGE, SUITE_PAGE,
                "plugins/skillworks/skills/skillworks-setup/SKILL.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        assert "`ignores`" in text, doc
        assert '"when"' not in text, doc


LOOP_PAGES = ["docs/usage/the-loop.md"] + sorted(
    page.relative_to(ROOT).as_posix() for page in (ROOT / "docs" / "usage" / "the-loop").glob("*.md"))


def test_the_loop_s_pages_are_the_overview_and_each_page_in_its_folder():
    assert {"docs/usage/the-loop.md", "docs/usage/the-loop/target-branch.md",
            "docs/usage/the-loop/tracker.md", "docs/usage/the-loop/the-grill.md",
            "docs/usage/the-loop/tickets.md", STEPS_PAGE, LANDING_PAGE, DRIFT_CHECK_PAGE,
            NAME_CHECK_PAGE, FULL_RUN_PAGE, "docs/usage/the-loop/stops.md",
            "docs/usage/the-loop/reading-a-run.md", "docs/usage/the-loop/stage-map.md"} <= set(LOOP_PAGES)


@pytest.mark.parametrize("doc", LOOP_PAGES)
def test_no_page_of_the_loop_names_the_suite_setting_when(doc):
    text = (ROOT / doc).read_text(encoding="utf-8")

    assert "`when`" not in text
    assert '"when"' not in text


def test_only_the_suite_page_names_when_and_only_to_say_it_is_turned_down():
    assert "`when`" not in (ROOT / "plugins/skillworks/skills/skillworks-setup/SKILL.md").read_text(
        encoding="utf-8")

    paragraphs = (ROOT / SUITE_PAGE).read_text(encoding="utf-8").split("\n\n")
    naming = [paragraph for paragraph in paragraphs if "`when`" in paragraph]
    assert naming
    for paragraph in naming:
        assert "turned down" in paragraph and "`ignores`" in paragraph, paragraph


def test_the_suite_page_tells_a_team_how_to_run_the_suite_itself():
    text = " ".join((ROOT / SUITE_PAGE).read_text(encoding="utf-8").split())

    for words in ("`skillworks-suite`", "`skillworks-suite --fresh`", "Proof", "full run",
                  "`image`", "`runs`"):
        assert words in text, words


def test_the_suite_page_says_what_a_flake_is_where_it_says_what_runs_does():
    paragraphs = (ROOT / SUITE_PAGE).read_text(encoding="utf-8").split("\n\n")
    naming = [" ".join(paragraph.split()) for paragraph in paragraphs if "**Flake**" in paragraph]

    assert len(naming) == 1
    for words in ("`runs`", "counts as green", "always reported", "`runs: 2`"):
        assert words in naming[0], words


def test_the_suite_page_says_what_a_trial_is_after_running_the_suite_yourself():
    headings = re.findall(r"^## (.+)$", (ROOT / SUITE_PAGE).read_text(encoding="utf-8"), re.M)
    at = headings.index("Running the Suite yourself")
    assert "Trial" in headings[at + 1]

    section = " ".join((ROOT / SUITE_PAGE).read_text(encoding="utf-8")
                       .split("## " + headings[at + 1])[1].split("\n## ")[0].split())
    for words in ("`skillworks-suite --image <Dockerfile> -- <command>`", "keeps no Proof",
                  "no check", "Docker", "from the folder you are in"):
        assert words in section, words


def test_the_seeded_suite_file_shows_the_setting_at_its_default():
    seed = ROOT / "plugins/skillworks/skills/skillworks-setup/seeds/suite.json"

    assert json.loads(seed.read_text(encoding="utf-8"))["runs"] == 1


REVIEW_PAGES = (
    "plugins/skillworks/skills/review-changes/SKILL.md",
    "plugins/skillworks/skills/review-changes/standards.md",
    "plugins/skillworks/skills/review-changes/spec.md",
    "plugins/skillworks/skills/review-changes/architecture.md",
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


def pytest_checks():
    return [entry for entry in this_repo_s_checks()
            if "pytest" in entry["command"] and entry["command"] != THIS_REPO_S_SUITE_TESTS_COMMAND]


# On Windows every git and bash process the script tests start is slow to start, and in Linux it is not.
def test_this_repo_s_script_tests_are_one_check_with_parallel_workers_in_the_linux_image():
    scripts = pytest_checks()

    assert len(scripts) == 1
    assert scripts[0]["command"] == SCRIPT_TESTS_COMMAND
    assert scripts[0]["image"] == SCRIPT_TESTS_IMAGE
    assert (ROOT / SCRIPT_TESTS_IMAGE).is_file()


def test_this_repo_s_script_test_image_holds_what_the_script_tests_start():
    text = (ROOT / SCRIPT_TESTS_IMAGE).read_text(encoding="utf-8")

    # bash comes with the Debian base, so only a Debian base is asked for.
    assert re.search(r"^FROM python:\S+-bookworm$", text, re.MULTILINE)
    for program in ("/uv", "/usr/local/bin/node", "install --yes --no-install-recommends git"):
        assert program in text, program


# Each entry is a path the check cannot read. A path left off costs a run, and one wrongly on lets red pass.
SCRIPT_TESTS_IGNORE = {
    ".claude": "the tests build every .claude folder they read in a throwaway repo",
    "tools": "the seeded Studio is a Studio tool",
    "docs/adr": "no test reads a decision record",
    "docs/studio": "no test reads Studio's own docs",
    "docs/assets": "no test reads a picture",
    "src/*.cs": "the tests check that the projects exist, and never read their code",
    "src/Skillworks.AppHost": "the AppHost is in no solution filter the tests read",
    "src/Skillworks.Studio.Web/src": "of the front end the tests read only package.json",
    "tests/Skillworks.Core.Tests/*.cs": "the tests check that the project exists, and never read its code",
    "tests/Skillworks.Architecture.Tests/*.cs": "the tests check that the folder exists, and never read its code",
    "tests/plugins/skillworks/scripts/*.mjs": "pytest collects only Python, and node --test runs these",
    "plugins/skillworks/scripts/*.mjs": "the hooks and the session watch are Node, and no Python test opens them",
}

# The API tests read session-watch.mjs, and the AppHost image tags and the Core harness they link.
DOCKER_TESTS_IGNORE = {
    ".claude": "the team settings test reads its own bin folder and never the repo's",
    "docs": "no C# project or test opens a doc",
    "tools": "the seeded Studio starts the app and is no part of a test",
    "README.md": "prose",
    "CLAUDE.md": "prose",
    "CONTEXT-MAP.md": "prose",
    "LICENSE": "prose",
    "NOTICE": "prose",
    "THIRD-PARTY-NOTICES.md": "prose",
    "aspire.config.json": "only the Aspire CLI reads it",
    "src/Skillworks.Architecture": "it is in no project of the filter",
    "src/Skillworks.Studio.Web": "no API project or test reaches the front end",
    "src/Skillworks.AppHost/Program.cs": "of the AppHost the tests link only the image tag files",
    "src/Skillworks.AppHost/Skillworks.AppHost.csproj": "of the AppHost the tests link only the image tag files",
    "src/Skillworks.AppHost/Properties": "of the AppHost the tests link only the image tag files",
    "src/Skillworks.AppHost/*.json": "of the AppHost the tests link only the image tag files",
    "src/Skillworks.AppHost/*.yaml": "the tests start Tempo with the Core tests' own settings",
    "tests/Skillworks.Architecture.Tests": "it is in no project of the filter",
    "tests/plugins": "the Python and Node tests are no part of the filter",
    "plugins/.claude-plugin": "the API tests read a test Marketplace of their own",
    "plugins/skillworks/.claude-plugin": "the API tests read a test Marketplace of their own",
    "plugins/skillworks/bin": "of the Plugin the tests read only session-watch.mjs",
    "plugins/skillworks/hooks": "of the Plugin the tests read only session-watch.mjs",
    "plugins/skillworks/output-styles": "of the Plugin the tests read only session-watch.mjs",
    "plugins/skillworks/skills": "the API tests read a test Marketplace of their own",
    "plugins/skillworks/scripts/hooks": "of the Plugin the tests read only session-watch.mjs",
    "plugins/skillworks/scripts/*.py": "of the Plugin the tests read only session-watch.mjs",
}


# claude plugin validate reads the Plugin's folder alone.
PLUGIN_CHECK_IGNORE = {
    ".claude": "the Plugin is not read from the team settings",
    "docs": "the Plugin holds no doc of the repo's",
    "src": "Studio is no part of the Plugin",
    "tests": "the Plugin holds no test",
    "tools": "the seeded Studio is no part of the Plugin",
    "README.md": "prose",
    "CLAUDE.md": "prose",
    "CONTEXT-MAP.md": "prose",
    "LICENSE": "prose",
    "NOTICE": "prose",
    "THIRD-PARTY-NOTICES.md": "prose",
    "aspire.config.json": "only the Aspire CLI reads it",
    "Skillworks.slnx": "the Plugin builds no C#",
    "Skillworks.Studio.slnf": "the Plugin builds no C#",
    "plugins/.claude-plugin": "the Marketplace sits beside the Plugin's folder, not in it",
}


def ignored_by(checks):
    assert len(checks) == 1
    return checks[0].get("ignores", [])


def test_this_repo_s_script_tests_ignore_only_what_they_cannot_read():
    assert sorted(ignored_by(pytest_checks())) == sorted(SCRIPT_TESTS_IGNORE)


def test_this_repo_s_docker_tests_ignore_only_what_they_cannot_read():
    assert sorted(ignored_by([dotnet_checks()[DOCKER_TESTS]])) == sorted(DOCKER_TESTS_IGNORE)


@pytest.mark.this_repo
def test_what_the_docker_tests_ignore_leaves_the_files_they_read():
    for read in ("plugins/skillworks/scripts/session-watch.mjs", "src/Skillworks.AppHost/LokiImage.cs",
                 "src/Skillworks.AppHost/TempoImage.cs", "Skillworks.slnx", DOCKER_TESTS):
        assert (ROOT / read).is_file(), read
        assert not any(read == path or read.startswith(path + "/") for path in DOCKER_TESTS_IGNORE), read


def plugin_checks():
    return [entry for entry in this_repo_s_checks() if entry["command"] == PLUGIN_CHECK_COMMAND]


def test_this_repo_s_suite_validates_the_plugin_with_claude_code_on_the_host():
    checks = plugin_checks()

    assert len(checks) == 1
    assert checks[0]["folder"] == "."
    assert "image" not in checks[0]


def test_this_repo_s_plugin_check_ignores_only_what_it_cannot_read():
    assert sorted(ignored_by(plugin_checks())) == sorted(PLUGIN_CHECK_IGNORE)


def test_what_the_plugin_check_ignores_leaves_the_plugin():
    assert not any(PLUGIN == path or PLUGIN.startswith(path + "/") for path in PLUGIN_CHECK_IGNORE)


def test_only_the_docker_script_and_plugin_checks_ignore_anything():
    ignoring = [entry["command"] for entry in this_repo_s_checks() if "ignores" in entry]

    assert sorted(ignoring, key=" ".join) == sorted(
        [DOCKER_TESTS_COMMAND, SCRIPT_TESTS_COMMAND, PLUGIN_CHECK_COMMAND], key=" ".join)


@pytest.mark.this_repo
def test_every_path_this_repo_s_suite_ignores_is_there():
    for path in [*SCRIPT_TESTS_IGNORE, *DOCKER_TESTS_IGNORE, *PLUGIN_CHECK_IGNORE]:
        if "*" not in path:
            assert (ROOT / path).exists(), path


def test_the_this_repo_tests_run_on_the_host_in_a_check_that_ignores_nothing():
    checks = [entry for entry in this_repo_s_checks() if entry["command"] == THIS_REPO_S_SUITE_TESTS_COMMAND]

    assert len(checks) == 1
    assert "image" not in checks[0]
    assert "ignores" not in checks[0]


def dotnet_checks():
    return {entry["command"][2]: entry for entry in this_repo_s_checks() if entry["command"][0] == "dotnet"}


# The Architecture tests take seconds, so they run alone and never wait on Docker.
def test_this_repo_s_dotnet_tests_are_the_architecture_tests_alone_and_the_docker_tests_over_one_filter():
    checks = dotnet_checks()

    assert sorted(checks) == sorted([ARCHITECTURE_TESTS, DOCKER_TESTS])
    assert checks[ARCHITECTURE_TESTS]["command"] == ["dotnet", "test", ARCHITECTURE_TESTS]
    assert "ready" not in checks[ARCHITECTURE_TESTS]
    assert checks[DOCKER_TESTS]["command"] == DOCKER_TESTS_COMMAND
    assert checks[DOCKER_TESTS]["ready"]["command"] == ["docker", "info"]


# One filter builds each project once, so the Core and API tests never fight over build output.
def test_this_repo_s_docker_filter_holds_the_core_and_api_tests_and_what_they_build():
    solution = json.loads((ROOT / DOCKER_TESTS).read_text(encoding="utf-8"))["solution"]

    assert solution["path"] == "Skillworks.slnx"
    assert sorted(solution["projects"]) == [
        "src/Skillworks.Core/Skillworks.Core.csproj",
        "src/Skillworks.ServiceDefaults/Skillworks.ServiceDefaults.csproj",
        "src/Skillworks.Studio.Api/Skillworks.Studio.Api.csproj",
        "tests/Skillworks.Core.Tests/Skillworks.Core.Tests.csproj",
        "tests/Skillworks.Studio.Api.Tests/Skillworks.Studio.Api.Tests.csproj",
    ]
    assert all((ROOT / project).is_file() for project in solution["projects"])


# A skill edit must not change what the Docker check reads.
def test_no_api_test_reads_the_plugin_s_skill_folders():
    codes = list((ROOT / "tests/Skillworks.Studio.Api.Tests").rglob("*.cs"))

    assert codes
    for code in codes:
        text = code.read_text(encoding="utf-8")
        assert not ("RepositoryRoot()" in text and '"skills"' in text), code


def checks_section(doc, heading):
    text = (ROOT / doc).read_text(encoding="utf-8")
    return text[text.index(heading + "\n"):]


def test_the_contributing_page_lists_every_check_of_this_repo_s_suite():
    assert len(this_repo_s_checks()) == 9
    checks = checks_section("docs/CONTRIBUTING.md", "## Checks").split("```")[1].replace('"', "")

    for entry in this_repo_s_checks():
        assert " ".join(entry["command"]) in checks, entry["command"]


# An agent reads CLAUDE.md, and a raw command there is one it would run in place of the cheap one.
def test_claude_md_names_skillworks_suite_in_place_of_the_checks():
    section = checks_section("CLAUDE.md", "### Checks").split("\n### ")[0]

    assert section.split("```")[1].strip() == "skillworks-suite"
    assert "In a loop the driver runs the Suite" in section
    for entry in this_repo_s_checks():
        assert " ".join(entry["command"]) not in section.replace('"', ""), entry["command"]


def test_review_changes_and_its_axis_files_never_name_the_suite_file():
    for page in REVIEW_PAGES:
        assert SUITE_FILE not in (ROOT / page).read_text(encoding="utf-8"), page


def test_the_architecture_review_runs_the_placement_checks():
    assert PLACEMENT_CHECKS in (ROOT / "plugins/skillworks/skills/review-changes/architecture.md").read_text(encoding="utf-8")


def test_review_changes_and_its_axis_files_name_no_fact_of_this_repo_s_suite():
    facts = this_repo_s_facts()
    assert {"dotnet", DOCKER_TESTS, "src/Skillworks.Studio.Web"} <= facts

    for page in REVIEW_PAGES:
        text = (ROOT / page).read_text(encoding="utf-8")
        assert [fact for fact in sorted(facts) if fact in text] == [], page


def placement_commands(path):
    rows = re.findall(r"^\| `([^`]+)` \| `([^`]+)` \|", path.read_text(encoding="utf-8"), re.MULTILINE)
    return {(command, folder) for command, folder in rows}


def test_the_placement_checks_name_the_architecture_tests_and_the_front_end_lint_here():
    named = placement_commands(ROOT / PLACEMENT_CHECKS)

    assert named == {
        ("dotnet test tests/Skillworks.Architecture.Tests", "."),
        ("npm run lint", "src/Skillworks.Studio.Web"),
    }
    assert (ROOT / "tests/Skillworks.Architecture.Tests").is_dir()
    package = json.loads((ROOT / "src/Skillworks.Studio.Web/package.json").read_text(encoding="utf-8"))
    assert "lint" in package["scripts"]


def test_the_placement_checks_install_the_front_end_before_its_lint():
    text = (ROOT / PLACEMENT_CHECKS).read_text(encoding="utf-8")

    assert "| `npm run lint` | `src/Skillworks.Studio.Web` | `npm ci`, unless `node_modules` is there |" in text


def test_the_contributing_page_names_every_command_the_plugin_puts_on_path():
    text = (ROOT / "docs/CONTRIBUTING.md").read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| `plugins/skillworks/bin/` |"))

    for command in (ROOT / "plugins/skillworks/bin").iterdir():
        assert "`{}`".format(command.name) in row, command.name


def test_the_seeded_placement_checks_show_a_repo_how_to_name_its_commands():
    seed = ROOT / "plugins/skillworks/skills/skillworks-setup/seeds/placement-checks.md"

    assert "| Command | Folder | Run first |" in seed.read_text(encoding="utf-8")
    assert placement_commands(seed) == set()
