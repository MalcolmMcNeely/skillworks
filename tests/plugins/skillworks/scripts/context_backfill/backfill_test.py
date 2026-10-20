import io
import json
import os
import subprocess

import pytest
from conftest import Ran, git, no_wait, run
from context_backfill import backfill


def command(name, runner, where):
    out, err = io.StringIO(), io.StringIO()
    status = backfill.main([name], runner, out, err, no_wait, where.as_posix())
    return Ran(status, out.getvalue(), err.getvalue())


def check(runner, where):
    return command("check", runner, where)


def history_of(runner, where):
    return command("history", runner, where)


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
            if text is None:
                path.unlink()
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        git(self.work, "add", "-A")
        name, email = author
        env = dict(os.environ, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email, GIT_AUTHOR_DATE=when,
                   GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email, GIT_COMMITTER_DATE=when)
        done = subprocess.run(["git", "-C", self.work.as_posix(), "commit", "--quiet", "-m", message],
                              env=env, capture_output=True, encoding="utf-8", errors="replace")
        assert done.returncode == 0, done.stdout + done.stderr

    def head(self):
        return git(self.work, "rev-parse", "HEAD").strip()

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


def comment(login, body, when):
    return {"author": {"login": login}, "body": body, "createdAt": when}


def ticket(kind, number, title, body, *thread):
    return {"__typename": kind, "number": number, "title": title, "body": body, "state": "CLOSED",
            "url": "https://github.invalid/owner/repo/issues/{}".format(number),
            "createdAt": "2019-06-01T10:00:00Z", "comments": {"nodes": list(thread)}}


NAMED_TICKETS = json.dumps({"data": {"repository": {
    "t12": ticket("Issue", 12, "A crash on empty input", "It crashes on an empty file.",
                  comment("ann", "An empty file is a valid file, so the parser has to read it.",
                          "2019-06-02T10:00:00Z")),
    "t14": ticket("PullRequest", 14, "A web front end", "People asked to read dates in a browser.",
                  comment("bob", "TypeScript, because the team already writes it.", "2020-01-09T10:00:00Z")),
}}})


def merged_pull_requests(sha):
    return json.dumps([{
        "number": 20, "title": "Rename the parser to the reader", "body": "It reads more than dates now.",
        "url": "https://github.invalid/owner/repo/pull/20", "mergedAt": "2022-02-01T10:00:00Z",
        "mergeCommit": {"oid": sha},
        "comments": [comment("cy", "Reader is the word the docs use.", "2022-01-31T10:00:00Z")],
        "reviews": [{"author": {"login": "ann"}, "body": "Keep the old name out of the docs too.",
                     "state": "APPROVED", "submittedAt": "2022-01-31T11:00:00Z"}],
    }])


def scratch(where, name):
    return (where / ".context-backfill" / name).read_text(encoding="utf-8")


def test_history_writes_the_log_the_named_tickets_the_merged_pull_requests_and_the_renames(history, runner):
    history.commit("Rename the parser to the reader", BOB, "2022-02-01T10:00:00+00:00",
                   {"app/parse.py": None, "app/reader.py": "pass  # empty\n"})
    history.push()
    full = history.clone("full")
    runner.reply("auth status", "")
    runner.reply("pr list", merged_pull_requests(history.head()))
    runner.reply("issueOrPullRequest", NAMED_TICKETS)

    history_of(runner, full)

    assert ("The old one could not read a date with no year." in scratch(full, "log.txt"),
            "An empty file is a valid file, so the parser has to read it." in scratch(full, "tickets.md"),
            "TypeScript, because the team already writes it." in scratch(full, "tickets.md"),
            "Reader is the word the docs use." in scratch(full, "pull-requests.md"),
            "Keep the old name out of the docs too." in scratch(full, "pull-requests.md"),
            "app/parse.py -> app/reader.py" in scratch(full, "renames.md")) == (True,) * 6


def test_with_the_files_tracker_history_writes_the_specs_at_each_commit_and_calls_no_service(history, runner):
    history.commit("Add the parser spec", ANN, "2022-01-01T10:00:00+00:00", {
        ".specs/0001-parser/spec.md": "# Parser\n\nRead a date with no year.\n",
        ".specs/0001-parser/tickets/01-read-dates.md": "# Read dates\n",
    })
    history.commit("Narrow the parser spec", BOB, "2022-01-05T10:00:00+00:00", {
        ".specs/0001-parser/spec.md": "# Parser\n\nRead a date with no year, and never guess one.\n",
    })
    history.push()
    full = history.clone("full", tracker="files")

    history_of(runner, full)

    specs = scratch(full, "specs.md")
    assert ("Read a date with no year.\n" in specs,
            "Read a date with no year, and never guess one." in specs,
            "# Read dates" in specs,
            runner.started("gh")) == (True, True, True, [])


def test_a_gh_with_no_login_puts_the_warning_in_the_fit_and_still_writes_the_log_and_renames(history, runner):
    full = history.clone("full")
    runner.reply("totalCount", "41\t12\n")
    runner.reply("auth status", "", status=1)
    check(runner, full)

    history_of(runner, full)

    assert ("Warning: gh is not signed in" in scratch(full, "fit.md"),
            "Add the parser" in scratch(full, "log.txt"),
            scratch(full, "renames.md").startswith("# Renames")) == (True, True, True)


def apply(runner, where):
    return command("apply", runner, where)


SHEET_HEAD = "# Answer sheet\n\nMark each Answer: line with accept, reject or ?.\n\n"


def word(number, name, definition, answer, avoid=None):
    return ("### Draft W{}: {}\nAnswer: {}\n**{}**:\n{}\n{}Evidence:\n"
            "- commit 3f2a9c1 \"Rename the parser to the {}\"\n\n").format(
        number, name, answer, name, definition, "_Avoid_: " + avoid + "\n" if avoid else "", name.lower())


def decision(number, title, text, answer, *evidence):
    return "### Draft D{}: {}\nAnswer: {}\n{}\nEvidence:\n{}\n".format(
        number, title, answer, text, "".join("- " + item + "\n" for item in evidence))


def question(number, title, text, reason):
    return "### Question Q{}: {}\nReason: {}\n{}\nEvidence:\n- commit 77aa001 \"Move the store\"\n\n".format(
        number, title, reason, text)


def sheet(words="", decisions="", questions="", thin=""):
    return (SHEET_HEAD + "## Words\n\n" + words + "## Decisions\n\n" + decisions
            + "## Questions\n\n" + questions + "## Thin\n\n" + thin)


@pytest.fixture
def landing(history):
    where = history.clone("landing")
    for name, value in (("user.name", "Test"), ("user.email", "test@example.invalid"),
                        ("commit.gpgsign", "false"), ("core.autocrlf", "false")):
        git(where, "config", name, value)
    (where / ".context-backfill").mkdir()
    return where


def mark(where, text):
    (where / ".context-backfill" / "answer-sheet.md").write_text(text, encoding="utf-8", newline="\n")


def read(where, name):
    return (where / name).read_text(encoding="utf-8")


def test_an_accepted_word_lands_in_a_new_glossary_with_its_avoid_line_and_no_evidence(landing, runner):
    mark(landing, sheet(words=word(1, "Reader", "The part that turns a file into dates.", "accept", "Parser")))

    apply(runner, landing)

    assert read(landing, "CONTEXT.md").split("## Language\n\n", 1)[1] == (
        "**Reader**:\nThe part that turns a file into dates.\n_Avoid_: Parser\n")


GLOSSARY = ("# App\n\nThe date reader.\n\n## Language\n\n"
            "**Answer**:\nWhat the reader gives back.\n_Avoid_: Result\n\n"
            "**Verdict**:\nA call on one date.\n")

ADR_ONE = "# Read dates with no year\n\nThe parser reads them, because the files hold them.\n"


@pytest.fixture
def grown(history):
    history.commit("Glossary and two ADRs", ANN, "2022-03-01T10:00:00+00:00", {
        "CONTEXT.md": GLOSSARY,
        "docs/adr/0001-read-dates-with-no-year.md": ADR_ONE,
        "docs/adr/0002-a-web-front-end.md": "# A web front end\n\nIn TypeScript.\n",
    })
    history.push()
    return history


@pytest.fixture
def grown_landing(grown, landing):
    git(landing, "pull", "--quiet", "origin", "main")
    return landing


def test_an_accepted_word_lands_in_alphabetical_order_and_the_words_already_there_are_unchanged(
        grown_landing, runner):
    mark(grown_landing, sheet(words=word(1, "Batch", "Fifty tickets read in one call.", "accept", "Chunk")))

    apply(runner, grown_landing)

    assert read(grown_landing, "CONTEXT.md") == (
        "# App\n\nThe date reader.\n\n## Language\n\n"
        "**Answer**:\nWhat the reader gives back.\n_Avoid_: Result\n\n"
        "**Batch**:\nFifty tickets read in one call.\n_Avoid_: Chunk\n\n"
        "**Verdict**:\nA call on one date.\n")


def test_an_accepted_adr_takes_the_next_number_and_ends_with_where_it_was_recovered_from(grown_landing, runner):
    mark(grown_landing, sheet(decisions=decision(
        1, "Rename the parser to the reader", "The parser became the reader, because it reads more than dates.",
        "accept", 'commit 9c1d2e3 "Rename the parser to the reader"', 'pull request #20 "It reads more than dates now."',
        "app/reader.py:1 `pass`")))

    apply(runner, grown_landing)

    assert read(grown_landing, "docs/adr/0003-rename-the-parser-to-the-reader.md") == (
        "# Rename the parser to the reader\n\n"
        "The parser became the reader, because it reads more than dates.\n\n"
        "Recovered from history: commit 9c1d2e3, pull request #20\n")


def test_an_existing_adr_is_unchanged(grown_landing, runner):
    mark(grown_landing, sheet(decisions=decision(
        1, "Read dates with no year", "A second record of it.", "accept", 'commit 1a2b3c4 "Add the parser"')))

    apply(runner, grown_landing)

    assert read(grown_landing, "docs/adr/0001-read-dates-with-no-year.md") == ADR_ONE


def test_an_edited_draft_lands_with_the_text_on_the_sheet_and_not_the_text_the_pass_wrote(landing, runner):
    (landing / ".context-backfill" / "words.md").write_text(
        "### Reader\n**Reader**:\nThe parser.\n", encoding="utf-8")
    mark(landing, sheet(words=word(1, "Reader", "The part that reads a file of dates, with or without a year.",
                                   "accept")))

    apply(runner, landing)

    assert "**Reader**:\nThe part that reads a file of dates, with or without a year.\n" in read(landing, "CONTEXT.md")


def landed_text(where):
    paths = [where / "CONTEXT.md"] + sorted((where / "docs" / "adr").glob("*.md"))
    return "".join(path.read_text(encoding="utf-8") for path in paths if path.exists())


def test_a_rejected_draft_lands_nowhere(landing, runner):
    mark(landing, sheet(
        words=word(1, "Reader", "The part that reads dates.", "accept") + word(2, "Gadget", "A widget.", "reject"),
        decisions=decision(1, "Use a gadget store", "Gadgets are kept in a store.", "reject",
                           'commit 5e6f7a8 "Add the gadget store"')))

    apply(runner, landing)

    assert ("Gadget" in landed_text(landing), "gadget" in landed_text(landing)) == (False, False)


def headings(text):
    return [line for line in text.splitlines() if line.startswith("### ")]


def test_the_rewritten_sheet_holds_the_question_marks_and_the_unanswered_lines_and_nothing_else(landing, runner):
    mark(landing, sheet(
        words=word(1, "Reader", "The part that reads dates.", "accept") + word(2, "Batch", "Fifty tickets.", "?"),
        decisions=decision(1, "Use a gadget store", "Gadgets are kept in a store.", "reject",
                           'commit 5e6f7a8 "Add the gadget store"')
        + decision(2, "Read the log once", "The log is read once per run.", "", 'commit 6f7a8b9 "Cache the log"'),
        questions=question(1, "The store moved", "The store moved from app/ to store/ in 2021.", "?"),
        thin=word(3, "Tidy", "A commit that only tidies.", "")))

    apply(runner, landing)

    assert headings(read(landing, ".context-backfill/answer-sheet.md")) == [
        "### Draft W2: Batch",
        "### Draft D2: Read the log once",
        "### Question Q1: The store moved",
        "### Draft W3: Tidy",
    ]


def test_a_sheet_with_no_answer_stops_with_one_message_and_makes_no_commit(landing, runner):
    mark(landing, sheet(words=word(1, "Reader", "The part that reads dates.", ""),
                        questions=question(1, "The store moved", "The store moved in 2021.", "")))
    before = git(landing, "rev-parse", "HEAD")

    ran = apply(runner, landing)

    assert (ran.status, ran.err.startswith("FAIL  Mark the sheet"), ran.err.count("\n"),
            git(landing, "rev-parse", "HEAD")) == (1, True, 1, before)


def test_the_maps_accept_from_the_talk_is_not_an_answer(landing, runner):
    mark(landing, sheet(words="### Draft M1: The map\nAnswer: accept\n# Context Map\n\nEvidence:\n- code app/\n\n"
                        + word(1, "Reader", "The part that reads dates.", "")))

    ran = apply(runner, landing)

    assert (ran.status, ran.err.startswith("FAIL  Mark the sheet")) == (1, True)


def subjects(where, ref):
    return git(where, "log", "--format=%s", ref).splitlines()


def test_the_commits_carry_their_prefixes_leave_unstaged_work_out_and_reach_the_target_branch(
        history, landing, runner):
    (landing / "README.md").write_text("# App, half edited\n", encoding="utf-8")
    mark(landing, sheet(
        words=word(1, "Reader", "The part that reads dates.", "accept") + word(2, "Batch", "Fifty tickets.", "accept"),
        decisions=decision(1, "Read the log once", "The log is read once per run, because gh is slow.", "accept",
                           'commit 6f7a8b9 "Cache the log"')))

    apply(runner, landing)

    pushed = subjects(history.origin, "main")
    changed = git(history.origin, "log", "--format=", "--name-only", "-2", "main").split()
    assert (pushed[:2], sorted(changed), read(landing, "README.md")) == (
        ["ADR: Read the log once", "Glossary: 2 words in CONTEXT.md"],
        ["CONTEXT.md", "docs/adr/0001-read-the-log-once.md"],
        "# App, half edited\n")


def test_a_gitignore_with_no_last_newline_gets_the_line_on_a_line_of_its_own(history, runner):
    full = history.clone("full")
    (full / ".gitignore").write_text("bin/", encoding="utf-8")
    runner.stub("gh", says="0\t0\n")

    check(runner, full)

    assert (full / ".gitignore").read_text(encoding="utf-8") == "bin/\n.context-backfill/\n"
