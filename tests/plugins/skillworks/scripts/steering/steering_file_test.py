# Driven against a bare origin that holds a skillworks/steering branch, so a read that reached for it would show.

import contextlib
import io
import json
import os
import re

import pytest

from conftest import PLUGIN, Ran, Repo, git, launch, run
from runner import Subprocess
from steering import steering_file

OLD_STEERING_BRANCH = "skillworks/steering"
SURFACES = "docs/skillworks/surfaces.md"
RULES = "docs/skillworks/rules/"


class Work:
    def __init__(self, repo):
        self.repo = repo

    def on_old_steering_branch(self, *files):
        git(self.repo.work, "switch", "--quiet", "-c", OLD_STEERING_BRANCH)
        for name, text in zip(files[::2], files[1::2]):
            (self.repo.work / name).parent.mkdir(parents=True, exist_ok=True)
            self.repo.write_commit(self.repo.work, name, text, "Steering")
        git(self.repo.work, "push", "--quiet", "-u", "origin", OLD_STEERING_BRANCH)
        git(self.repo.work, "switch", "--quiet", "main")

    def on_disk(self, name, text):
        path = self.repo.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def in_sidecar(self, name, text):
        path = self.repo.work.parent / "work-skillworks" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def nested_worktree(self):
        tree = self.repo.work / ".spec-loop" / "nested" / "job"
        git(self.repo.work, "worktree", "add", "--quiet", "-b", "job", tree.as_posix())
        return tree

    def run(self, *argv, where=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.chdir(where or self.repo.work):
            status = steering_file.main(list(argv), Subprocess(), out, err)
        return Ran(status, out.getvalue(), err.getvalue())


@pytest.fixture
def work(tmp_path):
    return Work(Repo(tmp_path))


def test_a_file_on_disk_is_printed_as_it_is_on_disk(work):
    work.on_disk(SURFACES, "# Surfaces\n\nThe disk copy.\n")

    ran = work.run(SURFACES)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe disk copy.\n"), ran.err


def test_a_file_missing_on_disk_is_missing_even_when_an_old_steering_branch_holds_it(work):
    work.on_old_steering_branch(SURFACES, "# Surfaces\n\nThe Steering copy.")

    ran = work.run(SURFACES)

    assert (ran.status != 0, ran.out, ran.err) == (True, "", "FAIL  {} is missing.\n".format(SURFACES))


def test_a_file_on_disk_is_printed_from_disk_when_an_old_steering_branch_holds_it_too(work):
    work.on_old_steering_branch(SURFACES, "# Surfaces\n\nThe Steering copy.")
    work.on_disk(SURFACES, "# Surfaces\n\nThe disk copy.\n")

    ran = work.run(SURFACES)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe disk copy.\n"), ran.err


def test_a_folder_on_disk_prints_the_path_of_each_file_in_it(work):
    work.on_disk(RULES + "words.md", "# Words")
    work.on_disk(RULES + "comments.md", "# Comments")

    ran = work.run(RULES)

    assert (ran.status, ran.out) == (0, RULES + "comments.md\n" + RULES + "words.md\n"), ran.err


def test_a_folder_missing_on_disk_is_missing_even_when_an_old_steering_branch_holds_it(work):
    work.on_old_steering_branch(RULES + "words.md", "# Words")

    ran = work.run(RULES)

    assert (ran.status != 0, ran.out, ran.err) == (True, "", "FAIL  {} is missing.\n".format(RULES))


def test_a_path_is_read_from_the_repo_root_whatever_folder_the_caller_is_in(work):
    work.on_disk(SURFACES, "# Surfaces\n\nThe disk copy.\n")
    (work.repo.work / "src").mkdir()

    ran = work.run(SURFACES, where=work.repo.work / "src")

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe disk copy.\n"), ran.err


LOOP = "docs/skillworks/loop.json"


def test_with_loop_json_in_the_sidecar_the_sidecars_copy_is_printed_from_the_main_checkout(work):
    work.on_disk(LOOP, '{"target-branch": "main"}\n')
    work.in_sidecar(LOOP, '{"target-branch": "pr"}\n')

    ran = work.run(LOOP)

    assert (ran.status, ran.out) == (0, '{"target-branch": "pr"}\n'), ran.err


def test_with_loop_json_in_the_sidecar_the_sidecars_copy_is_printed_from_a_worktree(work):
    tree = work.nested_worktree()
    work.in_sidecar(LOOP, '{"target-branch": "pr"}\n')

    ran = work.run(LOOP, where=tree)

    assert (ran.status, ran.out) == (0, '{"target-branch": "pr"}\n'), ran.err


def test_with_loop_json_in_the_sidecar_a_steering_file_is_read_from_the_sidecar_and_not_the_repo(work):
    work.on_disk(SURFACES, "# Surfaces\n\nThe repo copy.\n")
    work.in_sidecar(LOOP, '{"target-branch": "pr"}\n')
    work.in_sidecar(SURFACES, "# Surfaces\n\nThe Sidecar copy.\n")

    ran = work.run(SURFACES)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe Sidecar copy.\n"), ran.err


def test_a_sidecar_with_no_loop_json_leaves_every_read_on_the_repo(work):
    work.on_disk(SURFACES, "# Surfaces\n\nThe repo copy.\n")
    work.in_sidecar(SURFACES, "# Surfaces\n\nThe Sidecar copy.\n")

    ran = work.run(SURFACES)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe repo copy.\n"), ran.err


def test_the_command_prints_the_sidecars_copy_to_the_caller_from_a_worktree(work):
    tree = work.nested_worktree()
    work.in_sidecar(LOOP, '{"target-branch": "pr"}\n')

    ran = launch("steering-file", LOOP, where=tree)

    assert (ran.status, ran.out) == (0, '{"target-branch": "pr"}\n'), ran.err


def test_the_command_prints_the_disk_copy_to_the_caller(work):
    work.on_disk(SURFACES, "# Surfaces\n\nThe disk copy.\n")

    ran = launch("steering-file", SURFACES, where=work.repo.work)

    assert (ran.status, ran.out) == (0, "# Surfaces\n\nThe disk copy.\n"), ran.err


SESSION = "4f1c0d2e-remote-steering"


class Remote:
    def __init__(self, root):
        self.bare = root / "remote.git"
        self.work = root / "remote-work"
        run(["git", "init", "--quiet", "--bare", "--initial-branch=main", self.bare.as_posix()])
        run(["git", "init", "--quiet", "--initial-branch=main", self.work.as_posix()])
        for name, value in Repo.SETTINGS:
            git(self.work, "config", name, value)
        git(self.work, "remote", "add", "origin", self.url)

    @property
    def url(self):
        return self.bare.as_uri()

    def push(self, name, text):
        path = self.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        git(self.work, "add", "-A")
        git(self.work, "commit", "--quiet", "-m", "Method")
        git(self.work, "push", "--quiet", "origin", "main")

    def unreachable(self):
        self.bare.rename(self.bare.with_name("moved.git"))


class Named(Work):
    def __init__(self, repo, remote, home):
        super().__init__(repo)
        self.remote = remote
        self.home = home

    def user_file(self, settings):
        path = self.home / ".skillworks" / "remote-steering.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings), encoding="utf-8")

    def named(self):
        self.user_file({"url": self.remote.url, "repos": [self.repo.origin.as_posix()]})

    def run(self, *argv, where=None, session=SESSION):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.chdir(where or self.repo.work):
            status = steering_file.main(list(argv), Subprocess(), out, err, home=self.home, session=session)
        return Ran(status, out.getvalue(), err.getvalue())


@pytest.fixture
def named(tmp_path):
    work = Named(Repo(tmp_path), Remote(tmp_path), tmp_path / "home")
    work.named()
    return work


METHOD = "docs/skillworks/method.md"


def test_in_a_named_repo_a_file_only_the_remote_holds_is_given_as_it_is(named):
    named.remote.push(METHOD, "# Method\n\nThe remote's way of working.\n")

    ran = named.run(METHOD)

    assert (ran.status, ran.out, ran.err) == (0, "# Method\n\nThe remote's way of working.\n", "")


def test_in_a_named_repo_a_file_both_layers_hold_is_the_repos_text_then_the_remotes(named):
    named.on_disk(SURFACES, "# Surfaces\n\nThe repo's part.\n")
    named.remote.push(SURFACES, "## The method's Surface\n\nThe remote's part.\n")

    ran = named.run(SURFACES)

    assert (ran.status, ran.out) == (
        0, "# Surfaces\n\nThe repo's part.\n## The method's Surface\n\nThe remote's part.\n"), ran.err


def test_in_a_named_repo_a_repo_file_with_no_last_newline_still_ends_its_line_before_the_remotes_text(named):
    named.on_disk(SURFACES, "# Surfaces")
    named.remote.push(SURFACES, "The remote's part.\n")

    ran = named.run(SURFACES)

    assert (ran.status, ran.out) == (0, "# Surfaces\nThe remote's part.\n"), ran.err


def test_in_a_named_repo_a_folder_read_lists_the_files_of_both_layers(named):
    named.on_disk(RULES + "words.md", "# Words")
    named.on_disk(RULES + "testing.md", "# Testing")
    named.remote.push(RULES + "method.md", "# Method")
    named.remote.push(RULES + "testing.md", "# More testing")

    ran = named.run(RULES)

    assert (ran.status, ran.out) == (0, RULES + "method.md\n" + RULES + "testing.md\n" + RULES + "words.md\n"), ran.err


def test_in_a_named_repo_a_folder_only_the_remote_holds_lists_its_files(named):
    named.remote.push(RULES + "method.md", "# Method")

    ran = named.run(RULES)

    assert (ran.status, ran.out) == (0, RULES + "method.md\n"), ran.err


def test_a_push_to_the_remote_after_the_session_fetched_does_not_change_a_later_read_in_that_session(named):
    named.remote.push(METHOD, "# Method\n\nThe first version.\n")
    named.run(METHOD)
    named.remote.push(METHOD, "# Method\n\nThe second version.\n")

    ran = named.run(METHOD)

    assert (ran.status, ran.out) == (0, "# Method\n\nThe first version.\n"), ran.err


def test_a_new_session_reads_the_remotes_new_tip(named):
    named.remote.push(METHOD, "# Method\n\nThe first version.\n")
    named.run(METHOD)
    named.remote.push(METHOD, "# Method\n\nThe second version.\n")

    ran = named.run(METHOD, session="a-later-session")

    assert (ran.status, ran.out) == (0, "# Method\n\nThe second version.\n"), ran.err


def test_with_an_unreachable_remote_a_new_session_reads_the_last_copy_fetched(named):
    named.remote.push(METHOD, "# Method\n\nThe copy fetched.\n")
    named.run(METHOD)
    named.remote.unreachable()

    ran = named.run(METHOD, session="a-later-session")

    assert (ran.status, ran.out) == (0, "# Method\n\nThe copy fetched.\n"), ran.err


def test_with_an_unreachable_remote_the_session_is_warned_that_the_text_may_be_old(named):
    named.remote.push(METHOD, "# Method\n\nThe copy fetched.\n")
    named.run(METHOD)
    named.remote.unreachable()

    ran = named.run(METHOD, session="a-later-session")

    assert (ran.err.startswith("WARN  remote Steering at {} could not be fetched".format(named.remote.url)),
            "may be old" in ran.err) == (True, True), ran.err


def test_with_an_unreachable_remote_every_read_in_the_session_warns(named):
    named.remote.push(METHOD, "# Method")
    named.run(METHOD)
    named.remote.unreachable()
    named.run(METHOD, session="a-later-session")

    ran = named.run(METHOD, session="a-later-session")

    assert "may be old" in ran.err, ran.err


def test_with_an_unreachable_remote_and_no_copy_on_the_machine_the_read_fails_and_names_the_url(named):
    named.on_disk(SURFACES, "# Surfaces")
    named.remote.unreachable()

    ran = named.run(SURFACES)

    assert (ran.status, ran.out, ran.err.startswith("FAIL  remote Steering at {} could not be fetched, and this "
                                                    "machine holds no copy of it".format(named.remote.url))) == (
        1, "", True), ran.err


def test_a_read_outside_a_session_reads_the_remotes_tip_each_time(named):
    named.remote.push(METHOD, "# Method\n\nThe first version.\n")
    named.run(METHOD, session=None)
    named.remote.push(METHOD, "# Method\n\nThe second version.\n")

    ran = named.run(METHOD, session=None)

    assert (ran.status, ran.out) == (0, "# Method\n\nThe second version.\n"), ran.err


def test_in_a_repo_whose_origin_is_not_on_the_list_the_read_is_the_same_as_today(named):
    named.user_file({"url": named.remote.url, "repos": ["https://example.invalid/another.git"]})
    named.on_disk(SURFACES, "# Surfaces\n\nThe repo's part.\n")
    named.remote.push(SURFACES, "The remote's part.\n")

    ran = named.run(SURFACES)

    assert (ran.status, ran.out, ran.err) == (0, "# Surfaces\n\nThe repo's part.\n", "")


def test_with_no_url_set_the_read_is_the_same_as_today(named):
    named.user_file({"repos": [named.repo.origin.as_posix()]})
    named.on_disk(SURFACES, "# Surfaces\n\nThe repo's part.\n")
    named.remote.push(SURFACES, "The remote's part.\n")

    ran = named.run(SURFACES)

    assert (ran.status, ran.out, ran.err) == (0, "# Surfaces\n\nThe repo's part.\n", "")


def test_with_no_user_file_a_path_only_the_remote_holds_is_missing_and_nothing_warns(named):
    (named.home / ".skillworks" / "remote-steering.json").unlink()
    named.remote.push(METHOD, "# Method")

    ran = named.run(METHOD)

    assert (ran.status, ran.out, ran.err) == (1, "", "FAIL  {} is missing.\n".format(METHOD))


def test_under_sidecar_steering_a_named_repo_reads_the_sidecars_text_then_the_remotes(named):
    named.in_sidecar(LOOP, '{"target-branch": "pr"}\n')
    named.in_sidecar(SURFACES, "The Sidecar's part.\n")
    named.remote.push(SURFACES, "The remote's part.\n")

    ran = named.run(SURFACES)

    assert (ran.status, ran.out) == (0, "The Sidecar's part.\nThe remote's part.\n"), ran.err


def every_file(root):
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_reads_leave_no_file_url_or_commit_of_the_remote_in_the_repo_or_the_sidecar(named):
    named.in_sidecar(LOOP, '{"target-branch": "pr"}\n')
    named.remote.push(METHOD, "# Method")
    sidecar = named.repo.work.parent / "work-skillworks"
    before = (every_file(named.repo.work), every_file(sidecar))

    named.run(METHOD)
    named.run("docs/skillworks/")
    named.remote.unreachable()
    named.run(METHOD, session="a-later-session")

    assert (every_file(named.repo.work), every_file(sidecar)) == before


def test_the_command_reads_the_remote_held_for_the_session_it_runs_in(named):
    named.remote.push(METHOD, "# Method\n\nThe first version.\n")
    env = dict(os.environ, HOME=str(named.home), USERPROFILE=str(named.home), CLAUDE_CODE_SESSION_ID=SESSION)
    launch("steering-file", METHOD, where=named.repo.work, env=env)
    named.remote.push(METHOD, "# Method\n\nThe second version.\n")

    ran = launch("steering-file", METHOD, where=named.repo.work, env=env)

    assert (ran.status, ran.out) == (0, "# Method\n\nThe first version.\n"), ran.err


SKILLS = PLUGIN / "skills"

STEP_LIST = PLUGIN / "scripts" / "steering" / "steps.json"

# A file key judges that file alone, because review-changes holds one axis file per review.
SERVES = {
    "grill": ["grill"],
    "grilling": ["grill"],
    "domain-modeling": ["grill"],
    "to-spec": ["write-spec"],
    "to-tickets": ["cut"],
    "implement": ["build", "fix", "finish"],
    "tdd": ["build"],
    "codebase-design": ["build"],
    "review-standards": ["standards"],
    "review-changes/standards.md": ["standards"],
    "review-spec": ["spec"],
    "review-changes/spec.md": ["spec"],
    "review-architecture": ["architecture"],
    "review-changes/architecture.md": ["architecture"],
    "comment-sweep": ["sweep"],
}

READ = re.compile(r"steering-file\s+([^\s`'\"]+)")


def listed_steps():
    return json.loads(STEP_LIST.read_text(encoding="utf-8"))["steps"]


def fixed_reads(text):
    paths = [found.rstrip(".,;:)") for found in READ.findall(text)]
    return [path for path in paths if not re.search(r"[<>${}]", path)]


def steps_served_by(skill_file):
    folder = skill_file.split("/")[0]
    return SERVES.get(skill_file, SERVES.get(folder, []))


def is_listed(path, on_demand):
    return any(path == listed or (listed.endswith("/") and path.startswith(listed))
               for listed in on_demand)


def unlisted_reads(skills, steps):
    on_demand = {step["name"]: step["on-demand"] for step in steps}
    found = []
    for page in sorted(skills.rglob("*.md")):
        skill_file = page.relative_to(skills).as_posix()
        for step in steps_served_by(skill_file):
            for path in fixed_reads(page.read_text(encoding="utf-8")):
                if not is_listed(path, on_demand[step]) and (skill_file, step, path) not in found:
                    found.append((skill_file, step, path))
    return found


def given_a_skill(root, skill_file, text):
    page = root / skill_file
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(text, encoding="utf-8")
    return root


def test_every_fixed_path_a_step_s_skill_reads_is_listed_for_that_step():
    assert unlisted_reads(SKILLS, listed_steps()) == []


def test_every_fixed_steering_file_call_in_a_skill_is_found():
    text = ("Read `steering-file docs/skillworks/loop.json` first.\n"
            "Then steering-file docs/skillworks/rules/, and `steering-file <path>` for the rest.\n"
            "It ends with steering-file docs/skillworks/suite.json.\n")

    assert fixed_reads(text) == ["docs/skillworks/loop.json", "docs/skillworks/rules/",
                                 "docs/skillworks/suite.json"]


def test_a_path_the_step_does_not_list_is_named_with_the_skill_and_the_step(tmp_path):
    skills = given_a_skill(tmp_path, "comment-sweep/SKILL.md",
                           "Read `steering-file docs/skillworks/loop.json`.\n")

    assert unlisted_reads(skills, listed_steps()) == [
        ("comment-sweep/SKILL.md", "sweep", "docs/skillworks/loop.json")]


def test_a_skill_that_serves_several_steps_is_held_to_each_of_them(tmp_path):
    skills = given_a_skill(tmp_path, "implement/SKILL.md",
                           "Read `steering-file docs/skillworks/rules/testing.md`.\n")

    assert unlisted_reads(skills, listed_steps()) == [
        ("implement/SKILL.md", "fix", "docs/skillworks/rules/testing.md"),
        ("implement/SKILL.md", "finish", "docs/skillworks/rules/testing.md")]


def test_a_path_inside_a_folder_the_step_lists_passes(tmp_path):
    skills = given_a_skill(tmp_path, "review-changes/standards.md",
                           "Read `steering-file docs/skillworks/rules/words.md`.\n")

    assert unlisted_reads(skills, listed_steps()) == []


def test_a_placeholder_path_is_not_judged(tmp_path):
    skills = given_a_skill(tmp_path, "comment-sweep/SKILL.md", "Read each with `steering-file <path>`.\n")

    assert unlisted_reads(skills, listed_steps()) == []


def test_a_skill_that_serves_no_step_is_not_judged(tmp_path):
    skills = given_a_skill(tmp_path, "skillworks-setup/SKILL.md",
                           "Read `steering-file docs/skillworks/nowhere.md`.\n")

    assert unlisted_reads(skills, listed_steps()) == []


def test_every_skill_file_the_map_of_served_steps_names_exists():
    missing = [key for key in SERVES if not (SKILLS / key).exists()]

    assert missing == []


def test_every_step_the_map_of_served_steps_names_is_in_the_step_list():
    names = {step["name"] for step in listed_steps()}
    stray = [step for served in SERVES.values() for step in served if step not in names]

    assert stray == []
