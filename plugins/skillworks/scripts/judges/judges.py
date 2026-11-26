# All of a judge comes from its step name, so its skill, Sessions, kind and log files cannot drift apart.

from typing import Callable, NamedTuple

from position.position import DEEPENING_CHECK, DRIFT_CHECK, NAME_CHECK, SIMPLIFY_CHECK


class Judge(NamedTuple):
    name: str
    what: str
    report: str
    report_file: str
    read: Callable
    lost: str
    lost_again: str = ""

    @property
    def skill(self):
        return "spec-" + self.name

    @property
    def kind(self):
        return self.name

    @property
    def rechecks(self):
        return bool(self.lost_again)

    def session(self, again=False):
        return self.name.replace("-check", "-re-check") if again else self.name

    def said_as(self, again=False):
        return self.what.replace("check", "re-check") if again else self.what

    def log_file(self, again=False):
        return self.session(again) + ".md"


DEEPENING = Judge("deepening-check", DEEPENING_CHECK, "Deepening report", "deepening-report.md",
                  lambda tracker, spec: tracker.deepening_report(spec), "no deepening was read")
SIMPLIFY = Judge("simplify-check", SIMPLIFY_CHECK, "Simplify report", "simplify-report.md",
                 lambda tracker, spec: tracker.simplify_report(spec), "no cleanup was read")
DRIFT = Judge("drift-check", DRIFT_CHECK, "drift report", "drift-report.md",
              lambda tracker, spec: tracker.drift_report(spec), "nothing was counted",
              "the Gap items were not judged again")
NAMES = Judge("name-check", NAME_CHECK, "Name report", "name-report.md",
              lambda tracker, spec: tracker.name_report(spec), "no name was read",
              "no rename was checked")

# In the order the loop runs them.
JUDGES = (DEEPENING, SIMPLIFY, DRIFT, NAMES)


def told_to_judge():
    return [session for judge in JUDGES
            for session in ([judge.session(), judge.session(again=True)] if judge.rechecks
                            else [judge.session()])]
