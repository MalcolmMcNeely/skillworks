# Under Sidecar Steering no commit on the team's branch names its ticket, so the loop keeps the pairing here.

from clock.clock import Clock
from sidecar.sidecar import Sidecar
from stop import refusal

LIST = "landed-commits.tsv"

# A branch name may hold a slash, and never a tab.
FIELD = "\t"


class Landed:
    def __init__(self, runner, where, clock=None):
        self.runner = runner
        self.sidecar = Sidecar.of(runner, where, clock or Clock())

    @property
    def path(self):
        return self.sidecar.folder / LIST

    def lines(self):
        if not self.path.is_file():
            return []
        return [line.split(FIELD) for line in self.path.read_text(encoding="utf-8").splitlines()
                if line.count(FIELD) == 2]

    def add(self, branch, ticket, commits):
        def append(folder):
            with (folder / LIST).open("a", encoding="utf-8", newline="\n") as held:
                held.writelines(FIELD.join((branch, commit, ticket)) + "\n" for commit in commits)
        self.sidecar.write("List the commits ticket {} Landed on {}".format(ticket, branch), append)

    # Checked before it is read, so a branch rewritten under the list stops the reader and nothing guesses.
    def on(self, branch, repo):
        held = {}
        for listed_on, commit, ticket in self.lines():
            if listed_on != branch:
                continue
            kept = self.runner.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", commit,
                                    "origin/" + branch])
            if kept.status != 0:
                raise refusal(
                    "{b} on origin no longer holds commit {c}, which the Sidecar lists as Landed for "
                    "ticket {t}. {b} was rewritten under the list, so the loop cannot tell which "
                    "commits are a ticket's, and it guesses none. Put the commit back on {b}, or take "
                    "its line out of {p}, and run again.".format(
                        b=branch, c=commit, t=ticket, p=self.path.as_posix()))
            held[commit] = ticket
        return held
