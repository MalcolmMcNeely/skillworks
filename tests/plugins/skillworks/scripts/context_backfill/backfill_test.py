import io
import json
import os
import subprocess

import pytest
from conftest import Ran, git, no_wait, run
from context_backfill import backfill


def check(runner, where):
    out, err = io.StringIO(), io.StringIO()
    status = backfill.main(["check"], runner, out, err, no_wait, where.as_posix())
    return Ran(status, out.getvalue(), err.getvalue())


class History:
    def __init__(self, root):
        self.origin = root / "origin.git"
        self.work = root / "work"
        self.root = root
        run(["git", "init", "--quiet", "--bare", "--initial-branch=main", self.origin.as_posix()])
        # A local origin turns a filtered clone down unless it is told to serve one.
        git(self.origin, "config", "uploadpack.allowFilter", "true")
        run(["git", "init", "--quiet", "--initial-branch=main", self.work.as_posix()])
        for name, value in (("user.name", "Test"), ("user.email", "test@example.invalid"),
                            ("commit.gpgsign", "false"), ("core.autocrlf", "false")):
            git(self.work, "config", name, value)
        git(self.work, "remote", "add", "origin", self.origin.as_posix())

    def commit(self, message, author, when, files):
        for name, text in files.items():
            path = self.work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        git(self.work, "add", "-A")
        name, email = author
        env = dict(os.environ, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email, GIT_AUTHOR_DATE=when,
                   GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email, GIT_COMMITTER_DATE=when)
        done = subprocess.run(["git", "-C", self.work.as_posix(), "commit", "--quiet", "-m", message],
                              env=env, capture_output=True, encoding="utf-8", errors="replace")
        assert done.returncode == 0, done.stdout + done.stderr

    def push(self):
        git(self.work, "push", "--quiet", "origin", "main")

    def clone(self, name, *flags, tracker="github"):
        where = self.root / name
        run(["git", "clone", "--quiet", *flags, self.origin.as_uri(), where.as_posix()])
        loop = where / "docs" / "agents" / "loop.json"
        loop.parent.mkdir(parents=True)
        loop.write_text(json.dumps({"tracker": tracker, "target-branch": "main"}), encoding="utf-8")
        return where


ANN = ("Ann", "ann@example.invalid")
BOB = ("Bob", "bob@example.invalid")
CY = ("Cy", "cy@example.invalid")


@pytest.fixture
def history(tmp_path):
    made = History(tmp_path)
    made.commit("Add the parser\n\nThe old one could not read a date with no year.", ANN,
                "2019-03-01T10:00:00+00:00",
                {"app/pyproject.toml": "[project]\n", "app/parse.py": "pass\n"})
    made.commit("Fix #12, a crash on empty input", BOB, "2019-06-15T10:00:00+00:00",
                {"app/parse.py": "pass  # empty\n"})
    made.commit("Add the web front end\n\nTicket: #14", ANN, "2020-01-10T10:00:00+00:00",
                {"web/package.json": "{}\n", "web/src/index.ts": "", "web/src/view.ts": ""})
    made.commit("Tidy", CY, "2021-11-30T10:00:00+00:00", {"README.md": "# App\n"})
    made.push()
    return made


def test_a_clone_made_with_depth_one_is_refused_with_the_unshallow_fetch(history, runner):
    shallow = history.clone("shallow", "--depth", "1")

    ran = check(runner, shallow)

    assert (ran.status, "git fetch --unshallow" in ran.err) == (1, True)


def test_a_clone_made_with_a_blob_filter_is_refused_with_the_full_clone(history, runner):
    partial = history.clone("partial", "--filter=blob:none")

    ran = check(runner, partial)

    assert (ran.status, "git clone " + history.origin.as_uri() in ran.err) == (1, True)


def fit(said):
    return said.split("The fit of origin/main:\n", 1)[1].split("\n\n", 1)[0].splitlines()


def test_on_a_full_clone_the_fit_matches_the_history_written_commit_by_commit(history, runner):
    full = history.clone("full")
    runner.stub("gh", says="41\t12\n")

    ran = check(runner, full)

    assert fit(ran.out) == [
        "  Commits: 4",
        "  First: 2019-03-01",
        "  Last: 2021-11-30",
        "  Authors: 3",
        "  With a body: 25% (1 of 4)",
        "  Naming a ticket: 50% (2 of 4)",
        "  Tickets: 41, and 12 pull requests",
        "  Code roots: app, web",
        "  Languages: TypeScript (2 files), Python (1 file)",
    ]


def test_with_the_files_tracker_the_tickets_are_counted_from_the_specs(history, runner):
    history.commit("Add two specs", ANN, "2022-01-01T10:00:00+00:00", {
        ".specs/0001-parser/spec.md": "# Parser\n",
        ".specs/0001-parser/tickets/01-read-dates.md": "# Read dates\n",
        ".specs/0001-parser/tickets/02-read-years.md": "# Read years\n",
        ".specs/0002-web/spec.md": "# Web\n",
        ".specs/0002-web/tickets/01-show-dates.md": "# Show dates\n",
    })
    history.push()
    full = history.clone("full", tracker="files")

    ran = check(runner, full)

    assert "  Tickets: 3, in 2 specs" in fit(ran.out)


def test_a_gh_that_cannot_read_the_tickets_is_said_and_the_fit_still_printed(history, runner):
    full = history.clone("full")
    runner.stub("gh", says="", status=1)

    ran = check(runner, full)

    assert ("  Commits: 4" in fit(ran.out),
            any(line.startswith("  Tickets: none read") for line in fit(ran.out))) == (True, True)


def test_check_makes_the_scratch_folder_and_ignores_it(history, runner):
    full = history.clone("full")
    runner.stub("gh", says="0\t0\n")

    check(runner, full)

    assert ((full / ".context-backfill").is_dir(),
            (full / ".gitignore").read_text(encoding="utf-8")) == (True, ".context-backfill/\n")


def test_a_gitignore_that_names_the_scratch_folder_gets_no_second_line(history, runner):
    full = history.clone("full")
    (full / ".gitignore").write_text("bin/\n.context-backfill/\n", encoding="utf-8")
    runner.stub("gh", says="0\t0\n")

    check(runner, full)

    assert (full / ".gitignore").read_text(encoding="utf-8") == "bin/\n.context-backfill/\n"


def test_a_gitignore_with_no_last_newline_gets_the_line_on_a_line_of_its_own(history, runner):
    full = history.clone("full")
    (full / ".gitignore").write_text("bin/", encoding="utf-8")
    runner.stub("gh", says="0\t0\n")

    check(runner, full)

    assert (full / ".gitignore").read_text(encoding="utf-8") == "bin/\n.context-backfill/\n"
