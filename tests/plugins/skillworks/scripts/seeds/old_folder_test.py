import io
import json

import seed_steering
from conftest import ROOT, Ran, git
from export.export_branch import PREFIX, STEERING as STEERING_BRANCH, export
from seed_steering import PLACES, SEEDS
from steering.steering_file import STEERING_FOLDER
from tracker.files import Files

OLD_FOLDER = "docs/agents"

OTHER_TOOLS_FILE = OLD_FOLDER + "/notes.md"

DOCKERFILE = "script-tests.Dockerfile"


def old(place):
    return OLD_FOLDER + place[len(STEERING_FOLDER):]


def write(top, place, text):
    path = top / place
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def suite_naming(dockerfile):
    return json.dumps({"runs": 1, "checks": [{"command": ["pytest"], "folder": ".", "image": dockerfile}]},
                      indent=2) + "\n"


def set_up_in_the_old_layout(repo, committed=True):
    for name, place in PLACES.items():
        text = (SEEDS / name).read_text(encoding="utf-8").replace(seed_steering.DEFAULT_BRANCH_PLACEHOLDER, "main")
        write(repo.work, old(place), text)
        write(repo.work, "{}/.seeds/{}".format(OLD_FOLDER, name), text)
    write(repo.work, "{}/.seeds/README.md".format(OLD_FOLDER),
          seed_steering.BASES_README.replace(STEERING_FOLDER, OLD_FOLDER))
    write(repo.work, "{}/.seeds/agent-skills.md".format(OLD_FOLDER), "## Agent skills\n")
    write(repo.work, "{}/{}".format(OLD_FOLDER, DOCKERFILE), "FROM python:3.12\n")
    write(repo.work, "{}/suite.json".format(OLD_FOLDER), suite_naming("{}/{}".format(OLD_FOLDER, DOCKERFILE)))
    write(repo.work, OTHER_TOOLS_FILE, "# Another tool's notes\n")
    write(repo.work, "CLAUDE.md", "# Repo\n\n## Agent skills\n\n@{0}/rules/comments.md\n@{0}/rules/words.md\n\n"
                                  "## Other notes\n\n@{1}\n".format(OLD_FOLDER, OTHER_TOOLS_FILE))
    if committed:
        git(repo.work, "add", "-A")
        git(repo.work, "commit", "--quiet", "-m", "Set up in the old layout")


def run_seed(runner, repo, *flags):
    out, err = io.StringIO(), io.StringIO()
    status = seed_steering.main([repo.work.as_posix(), *flags], runner, out, err)
    return Ran(status, out.getvalue(), err.getvalue())


def files_under(top, folder):
    return sorted(path.relative_to(top).as_posix() for path in (top / folder).rglob("*") if path.is_file())


def test_the_skillworks_files_the_bases_and_the_suites_own_file_move_to_the_steering_folder(repo, runner):
    set_up_in_the_old_layout(repo)

    ran = run_seed(runner, repo)

    assert ran.status == 0, ran.err
    expected = sorted(list(PLACES.values())
                      + ["{}/.seeds/{}".format(STEERING_FOLDER, name) for name in PLACES]
                      + ["{}/.seeds/README.md".format(STEERING_FOLDER), "{}/.seeds/agent-skills.md".format(STEERING_FOLDER),
                         "{}/{}".format(STEERING_FOLDER, DOCKERFILE)])
    assert files_under(repo.work, STEERING_FOLDER) == expected


def test_another_tools_file_stays_in_the_old_folder(repo, runner):
    set_up_in_the_old_layout(repo)

    ran = run_seed(runner, repo)

    assert (ran.status, files_under(repo.work, OLD_FOLDER)) == (0, [OTHER_TOOLS_FILE]), ran.err


def test_the_suite_file_names_the_new_path_of_the_file_it_names(repo, runner):
    set_up_in_the_old_layout(repo)

    ran = run_seed(runner, repo)

    suite = json.loads((repo.work / STEERING_FOLDER / "suite.json").read_text(encoding="utf-8"))
    assert (ran.status, suite["checks"][0]["image"]) == (0, "{}/{}".format(STEERING_FOLDER, DOCKERFILE)), ran.err


def test_claude_md_imports_each_moved_file_from_its_new_path_and_another_tools_file_from_its_old_one(repo, runner):
    set_up_in_the_old_layout(repo)

    ran = run_seed(runner, repo)

    imports = [line for line in (repo.work / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
               if line.startswith("@")]
    assert (ran.status, imports) == (0, ["@{}/rules/comments.md".format(STEERING_FOLDER),
                                         "@{}/rules/words.md".format(STEERING_FOLDER),
                                         "@" + OTHER_TOOLS_FILE]), ran.err


def test_each_move_is_listed_by_its_old_and_its_new_path(repo, runner):
    set_up_in_the_old_layout(repo)

    ran = run_seed(runner, repo)

    moved = sorted(line for line in ran.out.splitlines() if line.startswith("moved "))
    expected = sorted(["moved {} to {}".format(old(place), place) for place in PLACES.values()]
                      + ["moved {0}/.seeds/{2} to {1}/.seeds/{2}".format(OLD_FOLDER, STEERING_FOLDER, name)
                         for name in list(PLACES) + ["README.md", "agent-skills.md"]]
                      + ["moved {0}/{2} to {1}/{2}".format(OLD_FOLDER, STEERING_FOLDER, DOCKERFILE)])
    assert moved == expected


def test_a_committed_file_moves_as_a_rename_git_records(repo, runner):
    set_up_in_the_old_layout(repo)

    run_seed(runner, repo)

    staged = git(repo.work, "status", "--porcelain").splitlines()
    assert "R  {} -> {}".format(old(PLACES["words.md"]), PLACES["words.md"]) in staged


def test_files_never_committed_move_as_well(repo, runner):
    set_up_in_the_old_layout(repo, committed=False)

    ran = run_seed(runner, repo)

    assert (ran.status, files_under(repo.work, OLD_FOLDER)) == (0, [OTHER_TOOLS_FILE]), ran.err


def test_the_moved_base_folder_readme_keeps_the_teams_note_and_names_the_new_folder(repo, runner):
    set_up_in_the_old_layout(repo)
    with (repo.work / OLD_FOLDER / ".seeds" / "README.md").open("a", encoding="utf-8", newline="\n") as readme:
        readme.write("\nOur note.\n")

    run_seed(runner, repo)

    readme = (repo.work / STEERING_FOLDER / ".seeds" / "README.md").read_text(encoding="utf-8")
    assert readme == seed_steering.BASES_README + "\nOur note.\n"


def test_a_repo_with_skillworks_files_already_in_the_steering_folder_is_not_moved(repo, runner):
    set_up_in_the_old_layout(repo)
    write(repo.work, PLACES["domain.md"], "# Our domain\n")
    before = files_under(repo.work, OLD_FOLDER)

    ran = run_seed(runner, repo)

    assert (ran.status, files_under(repo.work, OLD_FOLDER), "moved " in ran.out) == (0, before, False), ran.err


# The team's edit and the newer Seed both touch the heading, so setup has a question to ask.
def with_a_question_to_ask(repo):
    seeded = (SEEDS / "domain.md").read_text(encoding="utf-8")
    write(repo.work, "{}/.seeds/domain.md".format(OLD_FOLDER), seeded.replace("# Domain Docs\n", "# Domain docs\n"))
    write(repo.work, old(PLACES["domain.md"]), seeded.replace("# Domain Docs\n", "# Our domain\n"))


def test_a_run_that_asks_a_question_moves_nothing_and_says_what_it_would_move(repo, runner):
    set_up_in_the_old_layout(repo)
    with_a_question_to_ask(repo)
    before = files_under(repo.work, OLD_FOLDER)

    ran = run_seed(runner, repo)

    said = "would move {} to {}\n".format(old(PLACES["domain.md"]), PLACES["domain.md"])
    assert (ran.status, files_under(repo.work, OLD_FOLDER), said in ran.out) == (0, before, True), ran.err


def test_an_answer_to_the_question_weighs_the_moved_file(repo, runner):
    set_up_in_the_old_layout(repo)
    with_a_question_to_ask(repo)

    ran = run_seed(runner, repo, "--keep", "{}:1=yours".format(PLACES["domain.md"]))

    held = (repo.work / PLACES["domain.md"]).read_text(encoding="utf-8")
    assert (ran.status, held.startswith("# Our domain\n")) == (0, True), ran.err


TEAMS_TRACKER = "# Our tracker\n\nWe file bugs in Jira.\n"

ISSUE_TRACKER = PLACES["issue-tracker.md"]


# The team's default branch held its own issue tracker file before setup merged a Seed into it.
def set_up_with_the_export(repo):
    write(repo.work, old(ISSUE_TRACKER), TEAMS_TRACKER)
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "The team's tracker")
    git(repo.work, "push", "--quiet", "origin", repo.target)
    git(repo.work, "switch", "--quiet", "-c", STEERING_BRANCH)
    set_up_in_the_old_layout(repo, committed=False)
    seeded = (repo.work / old(ISSUE_TRACKER)).read_text(encoding="utf-8")
    write(repo.work, old(ISSUE_TRACKER), TEAMS_TRACKER + "\n" + seeded)
    loop = json.loads((repo.work / old(PLACES["loop.json"])).read_text(encoding="utf-8"))
    write(repo.work, old(PLACES["loop.json"]), json.dumps(dict(loop, export=True, **{"target-branch": "pr"})))
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "Steering")


def moved_and_committed(runner, repo):
    ran = run_seed(runner, repo)
    assert ran.status == 0, ran.err
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "Move the Steering")
    return ran


def test_with_the_export_an_old_path_the_default_branch_holds_gets_its_text_back(repo, runner):
    set_up_with_the_export(repo)

    moved_and_committed(runner, repo)

    assert git(repo.work, "show", "HEAD:" + old(ISSUE_TRACKER)) == TEAMS_TRACKER


def test_with_the_export_the_skillworks_text_lives_on_in_the_steering_folder(repo, runner):
    set_up_with_the_export(repo)

    moved_and_committed(runner, repo)

    held = git(repo.work, "show", "HEAD:" + ISSUE_TRACKER)
    assert held.startswith(TEAMS_TRACKER + "\n# Issue tracker")


def test_with_the_export_an_old_path_the_default_branch_does_not_hold_is_gone(repo, runner):
    set_up_with_the_export(repo)

    moved_and_committed(runner, repo)

    assert git(repo.work, "ls-tree", "-r", "--name-only", "HEAD", OLD_FOLDER).split() == [
        old(ISSUE_TRACKER), OTHER_TOOLS_FILE]


def test_with_the_export_each_old_path_given_back_is_listed(repo, runner):
    set_up_with_the_export(repo)

    ran = moved_and_committed(runner, repo)

    given = [line for line in ran.out.splitlines() if line.startswith("gave ")]
    assert given == ["gave {} back the text {} holds".format(old(ISSUE_TRACKER), repo.target)]


def test_without_the_export_nothing_is_given_back(repo, runner):
    write(repo.work, old(ISSUE_TRACKER), TEAMS_TRACKER)
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "The team's tracker")
    git(repo.work, "push", "--quiet", "origin", repo.target)
    set_up_in_the_old_layout(repo)

    ran = run_seed(runner, repo)

    assert (ran.status, files_under(repo.work, OLD_FOLDER)) == (0, [OTHER_TOOLS_FILE]), ran.err


def test_a_run_that_asks_a_question_gives_nothing_back_and_says_what_it_would_give_back(repo, runner):
    set_up_with_the_export(repo)
    with_a_question_to_ask(repo)
    before = (repo.work / old(ISSUE_TRACKER)).read_text(encoding="utf-8")

    ran = run_seed(runner, repo)

    said = "would give {} back the text {} holds\n".format(old(ISSUE_TRACKER), repo.target)
    held = (repo.work / old(ISSUE_TRACKER)).read_text(encoding="utf-8")
    assert (ran.status, said in ran.out, held == before) == (0, True, True), ran.err


def test_after_the_move_an_export_of_a_ticket_that_edits_a_team_file_applies_with_no_skillworks_text(
        repo, runner):
    set_up_with_the_export(repo)
    moved_and_committed(runner, repo)
    target = PREFIX + repo.target
    git(repo.work, "switch", "--quiet", "-c", target)
    write(repo.work, ".specs/0007-a-spec/spec.md", "---\nstatus: open\n---\n\n# SPEC: A spec\n")
    write(repo.work, ".specs/0007-a-spec/tickets/01-a-ticket.md",
          "---\nstatus: closed\nblocked-by: []\n---\n\n# TICKET: A ticket\n")
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "Tickets for spec 7")
    with (repo.work / old(ISSUE_TRACKER)).open("a", encoding="utf-8", newline="\n") as tracker:
        tracker.write("We triage on Mondays.\n")
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "Triage day\n\nTicket: 7/1")
    git(repo.work, "push", "--quiet", "origin", target)

    done = export(runner, repo.work.as_posix(), target, Files(runner, repo.work, target, "7"), "7", "SPEC: A spec")

    exported = git(repo.work, "show", "{}:{}".format(repo.target, old(ISSUE_TRACKER)))
    assert (done.not_applied, exported) == (None, TEAMS_TRACKER + "We triage on Mondays.\n")


def test_the_setup_page_says_setup_moves_only_the_skillworks_files_and_lists_each_move():
    page = " ".join((ROOT / "docs" / "usage" / "setup.md").read_text(encoding="utf-8").split())

    for said in ("setup moves a repo's Steering from `docs/agents/` to `docs/skillworks/`",
                 "Only the Skillworks files",
                 "Every other file in `docs/agents/` stays where it is",
                 "Setup lists each file it moved, by its old and its new path"):
        assert said in page, said


def test_the_setup_page_says_with_the_export_each_old_path_gets_the_default_branchs_text_back():
    page = " ".join((ROOT / "docs" / "usage" / "setup.md").read_text(encoding="utf-8").split())

    for said in ("With the Export, each old path that your default branch also holds gets the default branch's text back",
                 "Setup lists each old path it gave back"):
        assert said in page, said
