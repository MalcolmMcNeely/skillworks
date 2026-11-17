# Driven against a bare origin that holds a skillworks/steering branch, so a read that reached for it would show.

import contextlib
import io
import json
import re

import pytest

from conftest import PLUGIN, Ran, Repo, git, launch
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


SKILLS = PLUGIN / "skills"

STEP_LIST = PLUGIN / "scripts" / "steering" / "steps.json"

# A file key judges that file alone, because review-changes holds one axis file per review.
SERVES = {
    "grill": ["grill"],
    "grilling": ["grill"],
    "domain-modeling": ["grill"],
    "to-spec": ["write-spec"],
    "to-tickets": ["tickets"],
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
