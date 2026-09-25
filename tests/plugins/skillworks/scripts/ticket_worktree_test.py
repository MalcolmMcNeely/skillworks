#
# The worktree script, run against a throwaway repository.

import io
import shutil
import subprocess
from pathlib import Path

import ticket_worktree
from conftest import SCRIPTS, Ran, git, launch

SCRIPT = (SCRIPTS / "ticket_worktree.py").as_posix()


def run_worktree(runner, *args):
    given = [a.as_posix() if isinstance(a, Path) else str(a) for a in args]
    out, err = io.StringIO(), io.StringIO()
    status = ticket_worktree.main(given, runner, out, err)
    return Ran(status, out.getvalue(), err.getvalue())


# The case under test is the run the assertions read, so the setup stays quiet.
def given_job(repo, runner, spec, job):
    assert run_worktree(runner, "open", repo.work, spec, job).status == 0


def given_kept(repo, runner, spec):
    assert run_worktree(runner, "keep", repo.work, spec).status == 0


def record(job, leaf, state):
    return "{}\tspec-loop/158/{}\t{}\n".format(job, leaf, state)


def given_sessions(tree, *sessions):
    folder = Path(git(tree, "rev-parse", "--absolute-git-dir").strip())
    (folder / ticket_worktree.SESSIONS_RECORD).write_text(
        "".join(s + "\n" for s in sessions), encoding="utf-8", newline="\n")


def given_held(tree):
    (tree / "added.txt").write_text("new\n", encoding="utf-8", newline="\n")


def sessions_named(repo, leaf):
    return git(repo.work, "log", "-1", "--format=%(trailers:key=Skillworks-Session,valueonly)",
               "spec-loop/158/" + leaf).split()


def test_a_job_is_branched_from_the_newest_origin_main(repo, runner):
    repo.advance_origin("later")
    newest = git(repo.origin, "rev-parse", "main").strip()
    tree = repo.tree(158, "ticket-164")

    ran = run_worktree(runner, "open", repo.work, 158, "ticket-164")

    assert ran.status == 0
    assert ran.out == tree.as_posix() + "\n"
    assert git(tree, "rev-parse", "HEAD").strip() == newest
    assert git(tree, "rev-parse", "--abbrev-ref", "HEAD").strip() == "spec-loop/158/ticket-164"
    # A command recorded here is a command that went through the Runner and not around it.
    assert runner.built("worktree add --quiet -b spec-loop/158/ticket-164")


def test_a_held_checkout_still_gives_a_job_its_worktree(repo, runner):
    (repo.work / "loose.txt").write_text("loose\n", encoding="utf-8", newline="\n")

    ran = run_worktree(runner, "open", repo.work, 158, "ticket-164")

    assert ran.status == 0
    assert git(repo.tree(158, "ticket-164"), "rev-parse", "--abbrev-ref", "HEAD").strip() \
        == "spec-loop/158/ticket-164"


def test_a_plan_says_where_a_job_would_go_and_makes_nothing(repo, runner):
    ran = run_worktree(runner, "plan", repo.work, 158, "ticket-168")

    assert ran.status == 0
    assert ran.out == "{}\tspec-loop/158/ticket-168\n".format(repo.tree(158, "ticket-168").as_posix())
    assert not repo.group(158).exists()
    assert not repo.has_branch(158, "ticket-168")


# A stream held in memory never gets the line ending a real one would, so this one is started.
def test_a_path_printed_by_the_program_itself_has_no_carriage_return(repo):
    printed = subprocess.run(
        ["uv", "run", SCRIPT, "plan", repo.work.as_posix(), "158", "ticket-168"],
        capture_output=True)

    assert printed.returncode == 0
    assert printed.stdout == "{}\tspec-loop/158/ticket-168\n".format(
        repo.tree(158, "ticket-168").as_posix()).encode()


def test_a_plan_for_a_spec_with_a_worktree_group_is_still_given(repo, runner):
    given_job(repo, runner, 158, "ticket-164")

    ran = run_worktree(runner, "plan", repo.work, 158, "ticket-168")

    assert ran.status == 0
    assert repo.tree(158, "ticket-168").as_posix() in ran.out


def test_a_spec_with_no_worktree_has_nothing_to_keep(repo, runner):
    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert ran.out == ""


def test_a_leftover_holding_uncommitted_work_is_committed_to_a_branch(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    tree = repo.tree(158, "ticket-164")
    before = repo.head_of(158, "ticket-164")
    with (tree / "base.txt").open("a", encoding="utf-8", newline="\n") as file:
        file.write("half done\n")
    (tree / "added.txt").write_text("new\n", encoding="utf-8", newline="\n")

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert ran.out == record("ticket-164", "ticket-164-kept-1", "held")
    assert not tree.exists()
    assert repo.has_branch(158, "ticket-164-kept-1")
    assert repo.head_of(158, "ticket-164-kept-1") != before
    assert "new" in git(repo.work, "show", "spec-loop/158/ticket-164-kept-1:added.txt")
    assert "half done" in git(repo.work, "show", "spec-loop/158/ticket-164-kept-1:base.txt")


def test_a_leftover_holding_nothing_uncommitted_is_still_kept(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    before = repo.head_of(158, "ticket-164")

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert ran.out == record("ticket-164", "ticket-164-kept-1", "clean")
    assert not repo.tree(158, "ticket-164").exists()
    assert repo.head_of(158, "ticket-164-kept-1") == before


def test_a_held_keep_names_every_recorded_session_in_order(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    tree = repo.tree(158, "ticket-164")
    given_sessions(tree, "first-session", "second-session")
    given_held(tree)

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert ran.out == record("ticket-164", "ticket-164-kept-1", "held")
    assert sessions_named(repo, "ticket-164-kept-1") == ["first-session", "second-session"]


def test_a_held_keep_names_a_session_that_already_committed(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    tree = repo.tree(158, "ticket-164")
    given_sessions(tree, "first-session")
    repo.write_commit(
        tree, "early.txt", "early", "Early work\n\nSkillworks-Session: first-session")
    given_held(tree)

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert sessions_named(repo, "ticket-164-kept-1") == ["first-session"]


def test_a_held_keep_with_no_record_commits_and_warns(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    tree = repo.tree(158, "ticket-164")
    before = repo.head_of(158, "ticket-164")
    given_held(tree)

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert ran.out == record("ticket-164", "ticket-164-kept-1", "held")
    assert repo.head_of(158, "ticket-164-kept-1") != before
    assert sessions_named(repo, "ticket-164-kept-1") == []
    assert "warn  " + tree.as_posix() in ran.err


def test_a_clean_keep_with_a_record_commits_nothing_and_warns_of_nothing(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    tree = repo.tree(158, "ticket-164")
    given_sessions(tree, "first-session")
    before = repo.head_of(158, "ticket-164")

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert ran.out == record("ticket-164", "ticket-164-kept-1", "clean")
    assert repo.head_of(158, "ticket-164-kept-1") == before
    assert "warn" not in ran.err


def test_a_leftover_changed_only_in_its_line_endings_is_kept(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    tree = repo.tree(158, "ticket-164")
    before = repo.head_of(158, "ticket-164")

    # A file git holds with one line ending and the worktree has with the other stages to nothing.
    git(tree, "config", "core.autocrlf", "true")
    (tree / "base.txt").write_bytes(b"base\r\n")

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert ran.out == record("ticket-164", "ticket-164-kept-1", "clean")
    assert not tree.exists()
    assert repo.head_of(158, "ticket-164-kept-1") == before


def test_keeping_takes_the_spec_group_down(repo, runner):
    given_job(repo, runner, 158, "ticket-164")

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert not repo.group(158).exists()


def test_a_kept_job_is_free_to_be_opened_again(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    (repo.tree(158, "ticket-164") / "loose.txt").write_text(
        "half done\n", encoding="utf-8", newline="\n")
    given_kept(repo, runner, 158)

    ran = run_worktree(runner, "open", repo.work, 158, "ticket-164")

    assert ran.status == 0
    assert git(repo.tree(158, "ticket-164"), "rev-parse", "--abbrev-ref", "HEAD").strip() \
        == "spec-loop/158/ticket-164"
    assert repo.has_branch(158, "ticket-164-kept-1")


def test_a_second_attempt_is_kept_beside_the_first(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    given_kept(repo, runner, 158)
    given_job(repo, runner, 158, "ticket-164")

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert "ticket-164-kept-2" in ran.out
    assert repo.has_branch(158, "ticket-164-kept-1")
    assert repo.has_branch(158, "ticket-164-kept-2")


def test_every_leftover_in_the_group_is_kept(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    given_job(repo, runner, 158, "ticket-165")

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert "ticket-164" in ran.out
    assert "ticket-165" in ran.out
    assert repo.has_branch(158, "ticket-164-kept-1")
    assert repo.has_branch(158, "ticket-165-kept-1")


def test_a_keep_that_fails_on_a_later_job_still_records_the_one_it_kept(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    given_job(repo, runner, 158, "ticket-165")
    # Git will not make a ref where a folder of refs sits, so the name ticket-165 wants is taken.
    git(repo.work, "branch", "spec-loop/158/ticket-165-kept-1/blocker", "main")

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 1
    assert ran.out == record("ticket-164", "ticket-164-kept-1", "clean")
    assert repo.has_branch(158, "ticket-164-kept-1")
    assert "would not rename branch spec-loop/158/ticket-165" in ran.err


def test_an_empty_group_is_taken_down(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    shutil.rmtree(repo.tree(158, "ticket-164"))

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert ran.out == ""
    assert not repo.group(158).exists()


def test_a_folder_that_is_no_worktree_is_left_where_it_is(repo, runner):
    stray = repo.group(158) / "stray"
    stray.mkdir(parents=True)
    (stray / "notes.txt").write_text("notes\n", encoding="utf-8", newline="\n")

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert ran.out == ""
    assert (stray / "notes.txt").exists()
    assert "{} is no worktree of its own, so it was left where it is".format(stray.as_posix()) \
        in ran.err


def test_a_worktree_on_no_branch_is_left_where_it_is(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    tree = repo.tree(158, "ticket-164")
    git(tree, "checkout", "--quiet", "--detach")

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert ran.out == ""
    assert tree.exists()
    assert "{} is on no branch, so it was left where it is".format(tree.as_posix()) in ran.err


def test_keeping_one_spec_leaves_another_alone(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    given_job(repo, runner, 200, "ticket-201")

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert git(repo.tree(200, "ticket-201"), "rev-parse", "--abbrev-ref", "HEAD").strip() \
        == "spec-loop/200/ticket-201"


def test_keeping_with_a_job_prints_the_usage(repo, runner):
    ran = run_worktree(runner, "keep", repo.work, 158, "ticket-164")

    assert ran.status == 64
    assert "usage:" in ran.err


def test_closing_leaves_no_worktree_and_no_branch(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    (repo.tree(158, "ticket-164") / "untracked.txt").write_text(
        "build output\n", encoding="utf-8", newline="\n")

    ran = run_worktree(runner, "close", repo.work, 158, "ticket-164")

    assert ran.status == 0
    assert "ticket-164 left nothing behind" in ran.err
    assert not repo.tree(158, "ticket-164").exists()
    assert not repo.group(158).exists()
    assert not repo.has_branch(158, "ticket-164")


def test_closing_a_job_left_with_only_its_branch_still_removes_it(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    git(repo.work, "worktree", "remove", "--force", repo.tree(158, "ticket-164").as_posix())

    ran = run_worktree(runner, "close", repo.work, 158, "ticket-164")

    assert ran.status == 0
    assert "ticket-164 left nothing behind" in ran.err
    assert not repo.has_branch(158, "ticket-164")
    assert not repo.group(158).exists()


def test_closing_a_job_of_a_spec_that_has_none_is_refused(repo, runner):
    ran = run_worktree(runner, "close", repo.work, 158, "ticket-164")

    assert ran.status == 1
    assert "ticket-164" in ran.err
    assert "no worktree and no branch" in ran.err


def test_closing_a_job_under_a_name_the_spec_does_not_know_is_refused(repo, runner):
    given_job(repo, runner, 158, "ticket-164")

    ran = run_worktree(runner, "close", repo.work, 158, "164")

    assert ran.status == 1
    assert "no worktree and no branch" in ran.err
    assert repo.tree(158, "ticket-164").exists()
    assert repo.has_branch(158, "ticket-164")


def test_a_closed_job_leaves_nothing_to_keep(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    assert run_worktree(runner, "close", repo.work, 158, "ticket-164").status == 0

    ran = run_worktree(runner, "keep", repo.work, 158)

    assert ran.status == 0
    assert ran.out == ""


def test_opening_a_job_twice_is_refused(repo, runner):
    given_job(repo, runner, 158, "ticket-164")

    ran = run_worktree(runner, "open", repo.work, 158, "ticket-164")

    assert ran.status == 1
    assert "already" in ran.err


def test_a_leftover_branch_is_refused_and_names_its_removal(repo, runner):
    given_job(repo, runner, 158, "ticket-164")
    assert run_worktree(runner, "close", repo.work, 158, "ticket-164").status == 0
    git(repo.work, "branch", "spec-loop/158/ticket-164", "main")

    ran = run_worktree(runner, "open", repo.work, 158, "ticket-164")

    assert ran.status == 1
    assert SCRIPT + "' close" in ran.err


def test_a_remote_with_no_main_is_refused(repo, runner):
    git(repo.origin, "update-ref", "-d", "refs/heads/main")
    git(repo.work, "update-ref", "-d", "refs/remotes/origin/main")

    ran = run_worktree(runner, "open", repo.work, 158, "ticket-164")

    assert ran.status == 1
    assert "no main" in ran.err


def test_a_path_that_holds_no_repository_is_refused(repo, runner):
    ran = run_worktree(runner, "open", repo.root / "nowhere", 158, "ticket-164")

    assert ran.status == 1
    assert "not a git worktree" in ran.err


def test_arguments_of_the_wrong_shape_print_the_usage(repo, runner):
    ran = run_worktree(runner, "open", repo.work, 158)

    assert ran.status == 64
    assert "usage:" in ran.err


def test_an_unknown_command_prints_the_usage(repo, runner):
    ran = run_worktree(runner, "wreck", repo.work, 158, "ticket-164")

    assert ran.status == 64
    assert "usage:" in ran.err


def test_the_ticket_worktree_command_plans_from_the_top_of_the_repository(repo):
    below = repo.work / "src" / "deep"
    below.mkdir(parents=True)

    ran = launch("ticket-worktree", "plan", ".", 158, "ticket-168", where=below)

    assert ran.status == 0, ran.err
    assert ran.out == "{}\tspec-loop/158/ticket-168\n".format(repo.tree(158, "ticket-168").as_posix())
